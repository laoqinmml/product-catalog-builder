# 邮件送达：域名配置与双邮件回执

表单能落库，不等于客户收到了回执、也不等于你收到了提醒。这一篇解决三件事：域名侧的记录怎么配、一次提交发两封邮件怎么写、以及"DNS 全对但邮件还是退"怎么查。

## 一、域名侧的四种记录，别混在一起

| 记录 | 谁需要 | 作用 |
| --- | --- | --- |
| **MX** | 收信方（飞书 / Google Workspace / Zoho） | 告诉全世界"这个域的邮件投给谁"，没有 MX 就收不到任何信 |
| **SPF**（TXT `@`） | 发信方 | 列出允许以本域发信的服务器；域名只能有一条 SPF |
| **DKIM**（TXT `<selector>._domainkey`） | 发信方 | 用私钥签名，收信方用这条公钥验签，可有多条 |
| **DMARC**（TXT `_dmarc`） | 域名整体 | 规定"没通过 SPF / DKIM 的信怎么处理"，并收汇总报告 |

要点：

- **收信和发信是两套系统，可以来自两家供应商。** 典型组合：飞书管收信（MX），Resend 管网站发信（子域 SPF + DKIM）。互不干扰。
- **发信的 ESP 都用子域隔离**：Resend 的记录全在 `send.` 和 `resend._domainkey` 上，根域的 SPF 留给邮箱服务商。这样以后换 ESP 不用动根域。
- **根域只能有一条 SPF。** 要接第二家，把它的 `include:` 合并进同一条，不要加第二条 TXT —— 两条 SPF 等于没有 SPF。
- **DMARC 用宽松对齐**（`adkim=r; aspf=r`），子域发信也能通过，不用为每个子域单独配。

## 二、DMARC 的三个阶段

```
v=DMARC1; p=none; sp=none; pct=100; adkim=r; aspf=r; rua=mailto:sales@example.com
```

| 阶段 | 值 | 含义 |
| --- | --- | --- |
| 观察 | `p=none` | 只记录，不拦截。**新域名从这里开始，先跑 2–4 周** |
| 收紧 | `p=quarantine` | 未通过认证的信进垃圾箱 |
| 最终 | `p=reject` | 直接拒收，最高防护 |

- `rua` 必须是一个**真实存在**的邮箱，否则报告全部退回，等于白配。邮箱还没建就先别加 `rua`，或者指向一个已在用的地址。
- 收紧前确认所有会用这个域发信的系统都在 SPF 或 DKIM 里：邮箱服务商、网站发信 API、以后可能接的 Mailchimp / SendGrid / 站内信。
- 到了 `p=reject` 之后再"临时用别家群发"会直接进垃圾箱，先加 include 或 DKIM 再发。

## 三、一次提交，发两封

| 邮件 | 收件人 | `reply_to` | 作用 |
| --- | --- | --- | --- |
| 通知 | 销售邮箱 | **访客邮箱** | 销售点"回复"直接回客户，不用复制地址 |
| 回执 | 访客邮箱 | **销售邮箱** | 客户点"回复"回到销售收件箱，形成闭环 |

两个 `reply_to` 方向相反，这才是关键。只发通知会让客户觉得没提交成功；只发回执会让销售漏掉线索。

回执里放什么：

- 称呼（取名字的第一个词，别用全名）
- **编号**（和后台、数据库里的 `id` 一致，客户来电时报这个号就能查到）
- 他填的关键字段原文（公司、数量、工况），证明"我们真的收到了"
- 接下来会发生什么（谁来看、会给你什么）
- 一句"有图纸或照片直接回复这封邮件"

工程上：

- 两封分别调用，**一封失败不影响另一封**，状态分开存（`mail_status` / `receipt_status`）
- 通知先发、回执后发：销售拿到线索比客户拿到回执更急
- 回执只在邮箱通过格式校验时发，别往明显错误的地址发

## 四、验证送达，不用登录邮箱

Resend 的接口可以直接看投递结果：

```
POST https://api.resend.com/emails            → 返回 id
GET  https://api.resend.com/emails/{id}       → last_event / bounce.diagnosticCode
```

`last_event` 的取值：`sent`、`delivered`、`delivery_delayed`、`bounced`、`complained`。

**`bounced` 一定要看 `diagnosticCode`**，它会直接告诉你是谁的问题：

| diagnosticCode | 含义 | 处理 |
| --- | --- | --- |
| `550 ... User not found a@b.com` | 收件箱不存在 | 去邮箱后台建账号，不是 DNS 问题 |
| `550 ... No such domain` | 收件域不存在 | 客户填错地址，正常现象 |
| `Transient General` + 没有细节 | 对方服务器临时拒绝 | 等，通常几小时后重试能过 |
| `error:401`（接口层） | Resend key 失效 | 换 key，见下面的坑 |

DNS 侧核对三个视角，缺一不可：

```powershell
# 权威 NS 直接问（排除缓存）
nslookup -type=mx example.com etienne.ns.cloudflare.com
# 公共解析器
Resolve-DnsName example.com -Type MX -Server 1.1.1.1
Resolve-DnsName example.com -Type MX -Server 8.8.8.8
# 记录本身
GET /zones/{zone}/dns_records
```

## 五、排错表

| 现象 | 真实原因 | 处理 |
| --- | --- | --- |
| 服务商面板显示 MX「验证失败」，但 `nslookup` 查得到 | 面板检测结果被缓存，或在加记录之前跑过一次 | 点「重新验证」，等 10 分钟；以 DNS 查询结果为准 |
| 邮件 `bounced`，诊断码 `550 User not found` | MX 已生效、服务器已经应答，但邮箱账号没建 | 去邮箱后台建账号。**加 MX ≠ 建邮箱** |
| `mail_status = skipped` | Resend key 或收件人变量在运行时是空的 | 检查 Pages 项目变量；`plain_text` 进不了 Functions，一律 `secret_text` |
| 改了变量但行为没变 | 没重新部署 | 变量改完必须重新 deploy |
| SPF 通过但进垃圾箱 | 缺 DKIM 或 DMARC | 补 DKIM 记录 + `_dmarc`（先 `p=none`） |
| 发信突然全部失败 | 有人把根域 SPF 改成了第二条 TXT | 合并成一条 |

## 六、上线检查

- [ ] 根域有 MX，且 `sales@` 真的能收信（发一封测试信看退信诊断码）
- [ ] 根域 SPF 只有一条，`-all` 结尾
- [ ] 发信服务商的 DKIM 记录已加，且解析出来是完整公钥（超过 255 字节会被分片，拼接后长度要等于原值）
- [ ] `_dmarc` 存在，`p=none` 起步，`rua` 指向一个真实存在的邮箱
- [ ] 通知邮件 `reply_to` = 访客邮箱；回执 `reply_to` = 销售邮箱
- [ ] 后台能看到两封各自的状态
- [ ] 用真实邮箱提交一次，两封都收到，且"回复"按钮指向正确的人
