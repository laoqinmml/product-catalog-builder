# Cloudflare 令牌要哪些权限

做独立站基本离不开 Cloudflare：DNS、Pages 托管、D1 数据库、站点设置。让 Agent 帮你操作时，需要给一个 API 令牌——**给多了是风险，给少了每一步都会卡在 `Authentication error`**。

这一篇说明最小可用权限集，以及怎么验证到底缺哪一项。

## 一、按用途对照

| 要做的事 | 面板里的权限 | 给不给 |
| --- | --- | --- |
| 读域名信息（zone id、名称、状态） | Zone → **Zone → Read** | 必需 |
| 加/改 DNS 记录（CNAME、MX、TXT、DKIM、DMARC） | Zone → **DNS → Edit** | 必需 |
| 改站点设置（邮件地址混淆、SSL 模式、缓存、浏览器检查、Always Use HTTPS） | Zone → **Zone Settings → Edit** | 必需 |
| 部署静态站（`wrangler pages deploy`） | Account → **Cloudflare Pages → Edit** | 必需 |
| 建库、跑 SQL、读写线索 | Account → **D1 → Edit** | 必需 |
| 读账户/项目列表 | Account → **Account Settings → Read** | 建议 |
| 读流量数据（Analytics） | Zone → **Analytics → Read** | 可选 |
| 管证书 | Zone → **SSL and Certificates → Read/Edit** | 可选 |
| 配邮件转发（Email Routing） | Zone → **Email Routing Rules → Edit** | 可选 |
| 改 WAF / 速率限制规则 | Zone → **Zone WAF → Edit** | 可选 |

**范围（Zone Resources / Account Resources）一定要选具体域名和具体账户**，不要选 "All zones" —— 一个项目一个令牌，泄露了也只影响一个站。

## 二、创建步骤

1. 右上角头像 → **My Profile → API Tokens → Create Token**
2. 用 **Custom token**（不要用模板，模板通常给多了）
3. 按上表勾选 Permissions
4. **Zone Resources**：Include → Specific zone → `example.com`
5. **Account Resources**：Include → Specific account → 你的账户
6. 创建后**只显示一次**，立刻复制

存到代码库**外面**的文件里，例如 `../_secrets/cf-api-token.txt`，并在 `.gitignore` 里挡住 `_secrets/`。

> 改权限不用换令牌：在 API Tokens 列表里点 Edit，勾选新的权限保存，**同一个令牌字符串继续有效**，不必重新发给 Agent。

## 三、验证令牌到底能干什么

不要等跑到一半才发现缺权限。写一个探测脚本，把每一步要用的端点各打一次，缺哪项一目了然：

```js
const call = async (method, path, body) => {
  const res = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    method,
    headers: { Authorization: `Bearer ${TOKEN}`, "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json();
  return { ok: json.success, error: json.errors?.[0]?.message, result: json.result };
};

await call("GET", `/zones/${ZONE}`);                                  // Zone:Read
await call("GET", `/zones/${ZONE}/dns_records?per_page=5`);           // DNS:Read
await call("GET", `/zones/${ZONE}/settings/email_obfuscation`);       // Zone Settings:Read
await call("PATCH", `/zones/${ZONE}/settings/email_obfuscation`, { value: "off" }); // Zone Settings:Edit
await call("GET", `/accounts/${ACCOUNT}/pages/projects`);             // Pages:Read
await call("GET", `/accounts/${ACCOUNT}/d1/database`);                // D1:Read
```

返回 `success: true` 就是有权限，`Authentication error` 就是缺这一项。

实测一份只有 `Zone:Read + DNS:Edit + Pages:Edit` 的令牌的探测结果：

| 端点 | 结果 |
| --- | --- |
| `GET /zones/:id` | ✅ |
| `GET /zones/:id/dns_records` | ✅ |
| `GET /zones/:id/settings/email_obfuscation` | ❌ Authentication error ← 缺 Zone Settings |
| `PATCH /zones/:id/settings/:name` | ❌ Authentication error |
| `GET /accounts/:id/pages/projects` | ✅ |
| `GET /accounts/:id/d1/database` | ✅ |

所以「DNS 能改、站点能部署」不代表「设置能改」，这是两套权限。

## 四、没有对应权限时的替代做法

| 缺的权限 | 不改令牌也能解决的方案 |
| --- | --- |
| Zone Settings | 让账号本人在面板点一下（设置项都是一次性开关），或用 `<!--email_off-->` 这类页面级标记绕开邮件混淆 |
| Analytics | 用 Cloudflare 后台的图表，或接 GA4 |
| Email Routing | 用邮箱服务商（飞书 / Zoho / Google Workspace）自带的 MX |
| SSL/Certificates | Pages 托管默认自动签发，通常不需要手动管 |

拿到权限之后第一件事：先跑探测脚本，把所有 `❌` 一次列清楚，再问用户要，不要边做边卡。

## 五、安全提醒

- 令牌只放本地 `_secrets/`，**不进仓库、不进聊天记录、不写进日志**
- 一个站一个令牌，最小权限，用完可以随时 Revoke
- 探测脚本的失败信息（`Authentication error`）可以贴，令牌本身不行
- 如果令牌泄露：立刻 Revoke，重新生成，然后换掉本地文件
