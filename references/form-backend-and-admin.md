# 表单收线索：Pages Function + D1 + Resend，再加一个 /admin/leads

静态站最容易被忽略的一环：表单看着能用，其实只是 `mailto:` 打开访客的邮件客户端。用 Gmail 网页版、手机没配邮箱的人点一下，线索就没了，你这边也没有任何记录。

这一篇是把表单做成真的：落库、发信、后台可查、能导出。

## 一、整体链路

```
访客提交 → POST /api/rfq
        → 蜜罐 + 限流 + 字段校验
        → 写入 D1（leads 表）
        → Resend 发通知到销售邮箱（reply_to 设成访客邮箱，直接回复即可）
        → 返回 { ok: true }
        → 页面原地显示"已收到"，表单清空
        → 接口挂了自动退回 mailto，线索不丢
```

## 二、Cloudflare Pages 的接法（直接上传部署）

用 **advanced mode**：输出目录里放一个 `_worker.js`，导出一个 `fetch`：

```js
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/rfq") { /* 处理接口 */ }
    return env.ASSETS.fetch(request); // 其余全部交给静态站点
  },
};
```

- 构建时把 `src/worker.js` 复制成 `dist/_worker.js`，跟着静态文件一起部署
- `wrangler pages deploy dist` 会打印 `Compiled Worker successfully`，说明函数被识别
- 不需要额外配置路由，`/api/rfq` 和 `/admin/*` 都在同一个 worker 里

## 三、D1 表结构

```sql
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  company TEXT,
  units TEXT,
  message TEXT NOT NULL,
  page TEXT,
  country TEXT,
  user_agent TEXT,
  ip_hash TEXT,
  mail_status TEXT DEFAULT 'pending',
  status TEXT DEFAULT 'new'
);
```

建库与建表：

```powershell
npx wrangler d1 create <库名>
npx wrangler d1 execute <库名> --remote --file db/schema.sql
```

## 四、绑定与变量（这一步最容易翻车）

Pages 项目的 D1 绑定和环境变量走同一次 PATCH：

```json
PATCH /accounts/{account}/pages/projects/{project}
{
  "deployment_configs": {
    "production": {
      "d1_databases": { "DB": { "id": "<database_id>" } },
      "env_vars": {
        "RESEND_API_KEY": { "type": "secret_text", "value": "re_..." },
        "NOTIFY_EMAIL":   { "type": "secret_text", "value": "sales@example.com" },
        "RESEND_FROM":    { "type": "secret_text", "value": "Brand Sales <sales@example.com>" },
        "IP_SALT":        { "type": "secret_text", "value": "<随机串>" },
        "ADMIN_PASSWORD": { "type": "secret_text", "value": "<后台密码>" }
      }
    }
  }
}
```

两个必须记住的坑：

1. **PATCH 是整体替换，不是合并。** 只发 `ADMIN_PASSWORD` 会把没发上去的 `RESEND_API_KEY` 清空，表现是线索照样落库、邮件状态变成 `skipped`。**每次改变量都要把全部 secret 一起重发。**
2. **plain_text 变量进不了 Functions**（面板里能看到、运行时 `env` 里没有）。要用就用 `secret_text`。

另外：**改了变量必须重新部署**才生效。

## 五、发信（Resend）

- 域名要先用 DNS 验证：TXT `resend._domainkey`（DKIM）、MX `send`、TXT `send`（SPF）、CNAME `rsend`，四条都在子域上，不动根域 MX
- 发信时把 `reply_to` 设成访客邮箱，销售点"回复"就直接回给客户
- 返回非 2xx 时不要吞掉，把状态写回 `leads.mail_status`（`sent` / `error:422` / `skipped`），出问题一眼能看出来

**最容易被忽略的一步：收信。** 域名没有 MX 就没有人收得到 `sales@`，邮件会退。Resend 只管发，不管收。要么用 Cloudflare Email Routing 转发到已有邮箱，要么上 Google Workspace / Zoho。

## 六、防垃圾（足够用，不用上验证码）

- **蜜罐**：表单里放一个屏幕外、`tabindex="-1"`、`aria-hidden` 的输入框；提交时该字段有值就返回 200 但静默丢弃
- **限流**：按 `ip_hash`（IP + salt 的 SHA-256 前 8 字节）统计一小时内的提交数，超过阈值返回 429
- 都不需要第三方服务，也不会给访客增加一步交互

## 七、/admin/leads

一个受密码保护的服务端渲染页面，同一个 worker 出：

| 路由 | 作用 |
| --- | --- |
| `GET /admin/leads` | 没登录显示密码框，登录后显示列表 |
| `POST /admin/login` | 校验密码 → 写 session → 303 |
| `POST /admin/logout` | 删 session → 清 cookie → 303 |
| `GET /admin/leads.csv` | 导出 CSV（受同样保护） |

要点：

- **session 表**：`token`（随机 32 位）、`created_at`、`expires_at`，8 小时过期，登录时顺手清理过期行
- **cookie**：`HttpOnly; Secure; SameSite=Strict; Max-Age=28800`
- **密码比较**用定长比较（逐字符 XOR 累加），别用 `===` 直接比
- **登录限流**：同 IP 每小时 8 次，写 `login_attempts` 表
- **页面** `noindex, nofollow`，robots.txt 加 `Disallow: /admin`
- 列表带：编号、时间、联系人（姓名 + 可点邮箱）、公司、数量、国家、发信状态、需求（`<details>` 展开）、筛选框、分页、CSV 导出、退出

**渲染必须包完整 HTML 外壳。** 只输出 `<table>` 会得到一张没有任何样式的裸页面（我们第一次就踩了）。

## 八、验收

```powershell
# 1 接口语义
curl -X GET  https://站点/api/rfq                       # 405
curl -X POST https://站点/api/rfq -d '{"name":"A"}'      # 422 + 逐字段错误
curl -X POST https://站点/api/rfq -d '<合法数据>'         # 200 {"ok":true,"id":N}
# 2 落库与发信
npx wrangler d1 execute <库名> --remote --command "SELECT id, mail_status FROM leads ORDER BY id DESC LIMIT 3"
# 3 后台
#   未登录 → 密码页；错密码 → Wrong password；对密码 → 列表；导出 CSV 行数 = 线索数 + 1
```

`mail_status` 必须是 `sent`，出现 `skipped` 说明 Resend 的 key 或收件人没读到；出现 `error:4xx` 看 Resend 的报错体。

## 九、清理

测试用的线索记得删掉，别让真实数据里混着 `@example.com`：

```powershell
npx wrangler d1 execute <库名> --remote --command "DELETE FROM leads WHERE email LIKE '%example.com%'"
```
