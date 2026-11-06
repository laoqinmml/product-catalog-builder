# 上线后：GA4 与 Search Console

站点上线只是开始。这一步把「有没有人来、来了看什么、搜索引擎认不认」三件事接上。两个都不用改服务器，静态站一样做。

## 一、GA4（Google Analytics 4）

### 需要什么

一个衡量 ID（Measurement ID），形如 `G-XXXXXXXXXX`，在 GA4 → 管理 → 数据流 → 网站 里。

### 怎么埋（静态站）

把 ID 写进内容配置（例如 `content.mjs` 的 `ga4` 字段），构建时统一注入 `<head>`，**不要手改每个页面**——手改必然漏页，而且换 ID 时要改十几处。

```html
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  var storedConsent = 'denied';
  try { storedConsent = localStorage.getItem('vorlix-consent') || 'denied'; } catch (e) {}
  gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: storedConsent === 'granted' ? 'granted' : 'denied'
  });
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
```

一个站只有一个标签，不需要 GTM 或 Cloudflare Zaraz 再套一层。

### 同意管理（Consent Mode v2）

- `ad_storage` / `ad_user_data` / `ad_personalization` 永远 `denied`：这个站不投广告，就不给广告信号。
- `analytics_storage` 默认 `denied`，访客点「接受」才 `granted`。
- 同意条做成左下角一张小卡片，两个按钮，选择写 `localStorage`，别用弹窗遮全屏。
- **已同意的回访要直接把默认值设成 `granted`**，不要再走「先 denied 再 update」——否则首个 page_view 会以拒绝状态发出，数据里出现一段无 cookie 的空跑。

### 验收（不用等 GA 后台，看网络请求就够）

DevTools → Network → 过滤 `g/collect`，看 `gcs` 参数（第一位广告、第二位分析，0=拒绝 1=授权）：

| 场景 | 期望 |
| --- | --- |
| 新访客、未点同意 | `gcs=G100`，同意条出现 |
| 点「接受」 | 出现 `consent update → granted`，写入 `_ga` cookie |
| 已同意的回访 | `gcs=G101`，同意条不再出现 |

GA 后台的实时报告能看到自己，常规报告要等 24 小时。

### 建议标记的事件

`gtag('event', 'whatsapp_click')`、`email_click`、`quote_submit`——B2B 站真正的转化是这三个，页面浏览量只是过程指标。

## 二、Search Console（GSC）

### 先选资源类型

| 类型 | 覆盖范围 | 验证方式 |
| --- | --- | --- |
| **域名资源**（Domain） | http/https、www/非 www、全部子域 | **只能** DNS TXT |
| 网址前缀资源（URL prefix） | 只有该前缀 | HTML 文件、meta 标签、DNS 都可以 |

做独立站选**域名资源**，一次覆盖干净，以后加子域不用再验证。

### Cloudflare 托管的情况：一键授权最快

1. GSC → 添加资源 → 选「网域」→ 填 `example.com`（不带 www、不带 https）
2. 验证方式里，「以下说明适用于」选 **Cloudflare.com** → 点「开始验证」
3. 跳到 Google 授权页：列出它要添加的那条 TXT（`google-site-verification=...`），点「**授权**」。这是一次性授权，只允许加这一条，不给后续改 DNS 的权限。
4. Google 自动在 Cloudflare 加 TXT 记录，然后回到 GSC 自动完成验证
5. 验证通过后 → 左侧「站点地图」→ 提交 `https://example.com/sitemap.xml`

### 手动加 TXT（没有 OAuth，或 DNS 不在 Cloudflare）

- 类型 `TXT`，名称 `@`（根域），内容整串 `google-site-verification=xxxxxxxx`
- TTL 自动即可。TXT 记录不存在「代理开关」，面板上显示「仅 DNS」是正常状态，不是没生效。
- 加完回 GSC 点「验证」，通常 1 分钟内通过，DNS 慢的话等几分钟再点。

### 验收

- GSC 顶部显示「已成功验证」
- 站点地图状态从「无法获取」变成「成功」，发现网址数 = sitemap 条数
- 24–48 小时后搜 `site:example.com` 能看到自己的页面
- 「网址检查」里随便填一个产品页，能拿到「已编入索引」

### 顺手做：IndexNow（Bing / Yandex，不需要账号）

生成 32 位 key，放到站点根目录 `/{key}.txt`（内容就是这个 key），然后 POST：

```json
POST https://api.indexnow.org/indexnow
{"host":"example.com","key":"<key>","keyLocation":"https://example.com/<key>.txt","urlList":["https://example.com/", "..."]}
```

返回 `202` 就表示接收，Bing 会自己来抓。百度要在「百度搜索资源平台」单独提交，同样需要账号。

## 三、常见坑

- **sitemap 里还是 `example.com`**：模板占位没换，GSC 抓到的全是 404，收录 0。
- **canonical 没跟着换域名**：GSC 报「网页会重定向」或「已提交的网址不在所选资源中」。
- **只埋了首页**：手改模板会漏页，构建后 `grep -r "G-" dist | wc -l` 应该等于页面数。
- **同意默认 granted**：EU 访客直接落 cookie，合规上站不住；用 `gcs=G100/101` 自查。
- **刚上线就查 `site:`**：新域名 24–48 小时内查不到很正常，别急着改站。
- **TXT 加在子域上**：域名资源的 TXT 必须加在根域 `@`，加在 `www` 上验证不通过。
