# 网站页面规划：先定清单，再动手

做企业站最容易漏的两类页面：**转化页**（客户提交后去哪）和**政策页**（律师要看的东西）。等站做完了再补，导航结构、表单、统计都得返工。所以在画首页之前先把清单钉死。

## 一、标准清单

| 路径 | 页面 | 进导航 | 进 sitemap | 索引 |
| --- | --- | --- | --- | --- |
| `/` | 首页（定位 + 主推产品 + 应用 + 信任状） | 是 | 是 | 是 |
| `/products/` | 产品总览 | 是 | 是 | 是 |
| `/products/<slug>/` | 产品详情（每个系列一页） | 下拉菜单 | 是 | 是 |
| `/applications/` | 应用 / 行业场景 | 是 | 是 | 是 |
| `/quality/` | 质量与认证 | 是 | 是 | 是 |
| `/about/` | 关于（公司、能力、交付） | 是 | 是 | 是 |
| `/contact/` | 联系 + 询价表单 | 是 | 是 | 是 |
| `/thank-you/` | **提交成功页（转化页）** | **否** | **否** | **noindex** |
| `/privacy/` | 隐私政策 | 页脚 | 是 | 是 |
| `/terms/` | 条款（报价、交期、质保） | 页脚 | 是 | 是 |
| `/404.html` | 错误页 | — | 否 | 否 |
| `/sitemap.xml`、`/robots.txt`、`/llms.txt` | 给爬虫的 | 页脚 | — | — |

产品页面数 = 产品线条数，不要一页塞五个系列；详情页是做长尾搜索的地方。

## 二、转化页（thank-you）的六条规矩

1. **不进导航、不进页脚、不进 sitemap**：它是给广告平台和自己看转化用的，不是给访客逛的。
2. **`noindex, follow`**：能被访问、能被广告平台加载，但不进搜索结果。
3. **只能由表单成功提交后跳转**：`POST` 返回 2xx → `location.assign('/thank-you/?ref=<id>')`。
4. **地址里带一个可读的标识**：`?ref=<线索id>`，页面上显示成 `#12`，客户打电话时报这个号就能查到。
5. **转化事件在它身上触发，不要在前一页触发**：前一页触发容易和"提交但失败"混在一起，也容易重复计数。
6. **页面本身要能独立打开**：直接访问 `/thank-you/` 时也要有内容（显示"reference 待确认"而不是空白或报错），广告平台审核会直接访问这个 URL。

页面上放什么：一句确认、参考号、接下来会发生什么（三步）、回执邮件的提醒、以及"看产品 / 回首页"两个出口。不要再放一个表单。

## 三、转化事件怎么写

```js
// 只在转化页执行
if (typeof window.gtag === "function") {
  window.gtag("event", "generate_lead", { lead_reference: ref, campaign: campaignLabel || "direct" });
}
```

- 事件名用 GA4 的推荐名 `generate_lead`，GA4 后台可以直接把它标为转化，再导入 Google Ads。
- 同时把参数挂到 `window.vorlixConversion`，以后要接 Google Ads / Meta 的转化代码，直接读这个对象，不用改页面。
- 同意模式下，`analytics_storage` 被拒绝时事件照发但不落 cookie，这是预期行为。

## 四、转化页要放联系方式

客户刚提交完，是最想再补一句"顺便问一下"的时候。但不要把联系方式直接怼在标题下面 —— 先让客户读完"我们的处理流程"，再在描述段落下方给一句引导 + 一行可点的链接：

```
If you would like to reach us faster, use either of these.

sales@example.com ↗    WhatsApp +86 137 3823 3256 ↗
```

- 引导语只写一句，说明"为什么点"（想更快联系），不要写成"联系我们"的按钮
- 邮箱走 `mailto:`，WhatsApp 走 `wa.me`，都用跟全站一致的预填文案（当前页地址自动带上，客户一开口你就知道他从哪来）
- 页面下方如果已经有一句"回执会发到你邮箱"，就别再重复"有问题写信给我们"，两句话都指向同一件事会显得啰嗦
- 社媒链接（Facebook / LinkedIn / Instagram）留着字段，有了就填，没有就不渲染 —— 空链接比没有更糟

## 五、政策页必须写真的

隐私政策里关于表单的那一段，**要跟实际实现一致**：

- 还是 `mailto:` 的站，写"邮件在你自己的客户端里发出"。
- 已经接了我们自己的服务端，就写"请求会存进我们的数据库，并发送通知到销售邮箱"，再补一句保留期限。
- 加了统计，就写清楚用哪家、同意模式、怎么撤回。

改完表单忘了改隐私政策，是这类站最常见的合规漏洞，也是客户投诉的起点。

## 六、每页都要有的东西

- **页脚联系方式做成图标列表**：邮箱、WhatsApp、电话（同号时说明区别）、Facebook 各一行，每行 `14px 内联 SVG + 文字`，全部左对齐、行距一致。邮箱用描边信封，WhatsApp 用品牌填充图标
- **Facebook 这类强识别平台用 40px 圆角徽章**，单独一行放在列表末尾，别用 14px 小图标跟文字混排；徽章上方不要再加分隔线，列表本身已经够清楚
- 不要在下面再单独放一行 "WhatsApp ↗ Facebook ↗" 文字链接，跟上面的图标列表重复
- **邮箱链接保持 `mailto:a@b.com`，不要加 `?subject=`**：地址后面挂一长串参数，鼠标悬停时状态栏显示一大段编码，访客会以为链接有问题
- 图标用 `currentColor`，跟随文字颜色变化，不要写死品牌色（深底站点里满色 logo 会抢视觉）

## 七、Cloudflare 会偷偷改你的邮箱链接

如果站托管在 Cloudflare（Pages、Workers 都算），代理开关打开时，**「邮件地址混淆（Email Address Obfuscation）」会默认把页面里所有 `mailto:` 和邮箱文本替换掉**：

```html
<!-- 你写的 -->
<a href="mailto:sales@example.com">sales@example.com</a>
<!-- 实际发给浏览器的 -->
<a href="/cdn-cgi/l/email-protection#4734262b2234...">[email protected]</a>
```

后果：鼠标悬停状态栏是一串乱码、关掉 JS 的访客看到 `[email protected]`、任何按 `mailto:` 做统计或装饰的脚本都失效。

处理：Cloudflare 面板 → 选中域名 → **Speed → Optimization → Email Address Obfuscation → 关**（老界面在 **Scrape Shield** 下）。关掉后 HTML 里就是干净的 `mailto:`。

排查时直接 `curl` 页面搜 `cdn-cgi/l/email-protection`：出现就说明被混淆了，别去改代码。

### 结论：默认关掉

这个功能保护的是"不让爬虫从 HTML 里抓到邮箱"，但实际收益接近于零，代价却很实在：

- **地址在别处已经是明文**：每页的 `Organization` JSON-LD 里有 `email`，`llms.txt` 里有，隐私政策正文里也有。混淆只盖住 `mailto:` 这一处，等于锁了门忘了窗。
- **现代爬虫都跑 JS**，无头浏览器一执行，混淆自动还原。
- **成本是每个访客都看得到的**：悬停状态栏是一串 `/cdn-cgi/l/email-protection#...`，无 JS 时正文显示 `[email protected]`，任何按 `mailto:` 做统计或预填的脚本全部失效。

防垃圾邮件靠这三层就够：表单蜜罐 + 按 IP 限流 + 邮箱服务商的垃圾过滤，都比混淆有效。

如果确实想保留这层保护，配套动作是**把 JSON-LD 里的 `email` 字段删掉**（不是必填项），否则混淆形同虚设。

注意：改这个设置需要 Cloudflare token 有 **Zone Settings: Edit** 权限，只给 DNS + Pages 的 token 会返回 `Authentication error`，只能由账号本人在面板操作。

## 八、每页都要有的标记
- **产品详情页的 `<h1>` 就是产品名**，不要写成广告语。`Hollow hydraulic torque wrenches` 比 `The workhorse for flange work.` 有用得多：客户是搜着产品词进来的，标题对不上，跳出率就上去了；广告语想留就放进下面的引言，别占 h1
- 系列名放在 h1 上方的 eyebrow（`XLCT SERIES`），不要塞进标题里重复
- `<title>` 用「产品名 | 品牌」，`<meta description>` 用一句有参数的话（尺寸范围、吨位、压力）
- `<link rel="canonical">`（指向自己的正式地址）
- OG / Twitter 卡片（分享出去要有图有标题）
- 唯一的 `<h1>`
- 面包屑（产品详情页）+ `BreadcrumbList` 结构化数据
- 首页放 `Organization`，产品页放 `Product`，FAQ 页放 `FAQPage`

## 九、链接关系自查

| 检查 | 期望 |
| --- | --- |
| 每个页面都能从首页 3 次点击内到达 | 是 |
| `/thank-you/` 是否有任何入口链接 | **没有**（只在提交成功后跳转） |
| 政策页是否在页脚可达 | 是 |
| 是否有孤儿页（没有任何入口） | 除 thank-you 外，没有 |
| sitemap 条目数 = 可索引页面数 | 相等 |

`grep -r 'href="/thank-you/"' dist --include=*.html` 应该只在转化页自己里命中（canonical / og:url），其他页面零命中。
