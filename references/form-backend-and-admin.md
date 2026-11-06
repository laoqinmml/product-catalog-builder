# 表单收线索：Pages Function + D1 + Resend，再加一个 /admin/leads

静态站最容易被忽略的一环：表单看着能用，其实只是 `mailto:` 打开访客的邮件客户端。用 Gmail 网页版、手机没配邮箱的人点一下，线索就没了，你这边也没有任何记录。

这一篇是把表单做成真的：落库、发信、后台可查、能导出。

## 一、整体链路

```
访客提交 → POST /api/rfq
        → 蜜罐 + 限流 + 字段校验
        → 写入 D1（leads 表）
        → Resend 发通知到销售邮箱（reply_to 设成访客邮箱，直接回复即可）
        → 返回 { ok: true, id }
        → 跳转 /thank-you/?ref=<id>（转化页，事件在那里触发）
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
  status TEXT DEFAULT 'new',
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  click_id TEXT,
  referrer TEXT
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
- **每次提交发两封**：一封通知给销售（`reply_to` 设成访客邮箱，点回复直接回客户），一封回执给访客（`reply_to` 设成销售邮箱，客户点回复回到你收件箱）
- 两封的状态分开记（`mail_status` / `receipt_status`），一封失败不影响另一封
- 返回非 2xx 时不要吞掉，把状态写回数据库（`sent` / `error:422` / `skipped`），出问题一眼能看出来

**最容易被忽略的一步：收信。** 域名没有 MX 就没有人收得到 `sales@`，邮件会退。Resend 只管发，不管收。要么用飞书 / Google Workspace / Zoho 托管邮箱，要么用 Cloudflare Email Routing 转发（两者只能选一个，MX 会打架）。

域名侧的完整配置、双邮件模板、以及"DNS 全对但邮件还是退"的排查，见 [`mail-delivery.md`](mail-delivery.md)。

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
- 列表带：编号、时间、联系人（姓名 + 可点邮箱）、公司、数量、国家（单独一列）、来源页（有广告来源时下面多一行 `facebook / cpc / wind_2026q4`）、发信状态、需求（`<details>` 展开）、筛选框、分页、CSV 导出、退出

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

## 九、广告归因（投 Google / FB 之前先做）

投广告以后，"这个询盘从哪来"比"有没有询盘"更重要。落地页的参数要能一路带进数据库。

```sql
ALTER TABLE leads ADD COLUMN utm_source TEXT;
ALTER TABLE leads ADD COLUMN utm_medium TEXT;
ALTER TABLE leads ADD COLUMN utm_campaign TEXT;
ALTER TABLE leads ADD COLUMN click_id TEXT;   -- gclid 或 fbclid
ALTER TABLE leads ADD COLUMN referrer TEXT;
```

前端要做三件事：

1. 从 `location.search` 读 `utm_source / utm_medium / utm_campaign`，以及 `gclid` / `fbclid`（后者存进 `click_id`）
2. 存一份到 `sessionStorage`：访客从广告页跳到别的页再提交，来源也不会丢
3. 提交时随 JSON 一起 POST，并带上 `document.referrer`

后台与导出：列表的 Source 列显示页面路径，有来源时下面多一行 `facebook / cpc / wind_2026q4`；CSV 里五列都在；通知邮件加一行 Campaign。

UTM 命名别随手起，否则统计没法看：

| 平台 | utm_source | utm_medium | utm_campaign |
| --- | --- | --- | --- |
| Google Search | `google` | `cpc` | 系列名 |
| Google PMax | `google` | `pmax` | 系列名 |
| Facebook | `facebook` | `paid_social` | 系列名 |

两个注意：`document.referrer` 不能当唯一来源，HTTPS 站之间经常被裁成空；参数只作为附注，不要拼进正文，否则文案会被一长串参数搞乱。

## 十、WhatsApp 与邮件的来源标记

客户在 WhatsApp 里发来的第一句话，最好自带"我在哪一页看到你"。

**别在构建时把 URL 写进每个页面的链接。** 静态站常见做法是把页面路径塞进 `wa.me?text=`，能用，但每加一页都要保证模板传了路径，容易漏。更稳的是：HTML 只放基础地址，URL 由一条脚本在浏览器里拼。

```html
<body data-wa-template="Hello, I would like to know more about this page: {url}"
      data-mail-subject="Website enquiry: {url}">
...
<a href="https://wa.me/8613xxxxxxxxx" data-wa>WhatsApp</a>
<a href="mailto:sales@example.com" data-mail>sales@example.com</a>
```

```js
const pageUrl = location.origin + location.pathname; // 丢掉 utm 参数
document.querySelectorAll("a[data-wa]").forEach((a) => {
  const base = a.href.split("?")[0];
  const text = template.replace("{url}", pageUrl) + (campaign ? ` (via ${campaign})` : "");
  a.href = `${base}?text=${encodeURIComponent(text)}`;
});
```

- 加页面不用改任何模板，只要这页有页脚
- 文案改一处（`<body>` 上的模板）全站生效
- 结构化数据里仍然是干净地址，不带 `?text=`
- 代价：没有 JS 时链接能点开但没预填文案；介意的话在 `href` 里放一句通用文案兜底

邮件同理，`mailto:?subject=` 里带页面地址和来源，销售一眼看出客户在问哪个型号。

`tel:` 与 `wa.me` 用同一串数字；页面上显示可以带空格（`+86 137 3823 3256`），`href` 里必须是 `tel:+8613738233256` 这种无空格形式。

## 十一、提交成功后跳转转化页

接口返回 2xx 后不要停在原地显示"已收到"，**跳转到 `/thank-you/?ref=<id>`**：

```js
if (response.ok) {
  const { id } = await response.json();
  window.location.assign(`/thank-you/${id ? `?ref=${id}` : ""}`);
}
```

为什么要跳转而不是原地提示：

- 广告平台（Google Ads / Meta）认的是**落地 URL**，只有地址变了才能配成转化目标
- GA4 的 `generate_lead` 事件在转化页触发，天然排除"提交失败"和重复提交
- 页面刷新不会重复提交表单（POST 已经结束，现在停在 GET）

转化页本身的规则（不进导航、noindex、独立可访问、事件写法）见 [`web-page-plan.md`](web-page-plan.md)。

## 十二、清理

测试用的线索记得删掉，别让真实数据里混着 `@example.com`：

```powershell
npx wrangler d1 execute <库名> --remote --command "DELETE FROM leads WHERE email LIKE '%example.com%'"
```
