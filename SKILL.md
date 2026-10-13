---
name: product-catalog-builder
description: Build, update, render and QA a print-ready product catalogue (产品图册 / 产品画册 / 产品目录 / 产品手册) as A4 HTML pages plus a 300 DPI PDF. Use when the user wants to 做产品图册、做产品画册、生成产品目录、更新加页改版、重新导出 PDF, or fix PDF 体积暴涨、图片模糊、抠图白边、页码与文件名不一致、封面黑色渐变被压坏, and when they need a repeatable catalogue pipeline covering asset packing, page renders and a QA checklist.
---

# 产品图册生成（Product Catalog Builder）

把「做一本产品图册」这件事拆成七步，每步都有对应脚本，可以单独重跑。

## 何时用

- 从素材（产品图、规格表、PPT、旧画册 PDF）做一本新的产品图册/画册/目录
- 已有图册要加页、改文案、换图、重排版
- 重新导出 PDF，或者修 PDF 体积、清晰度、页码问题

## 工程目录约定

`root` = 图册工程根目录，固定结构如下：

```
root/
  pages/                     # 每页一个 HTML，文件名 01-xxx.html ... NN-yyy.html
  styles/catalog.css         # 全部版面样式
  assets/                    # 版面用图（网页版，源头就是高清大图）
  assets-print/              # 派生目录：按版面尺寸重做的打印图（自动生成，不要手改）
  tmp/                       # 中间产物、无头浏览器 profile（不入版本库）
  输出/                       # 单页渲染 PNG + 最终 PDF
  <名称>.html                 # 合并后的网页版（自动生成）
  <名称>-print.html           # 指向 assets-print/ 的打印版（自动生成）
```

两条硬规矩：

- `-print.html` 必须和 `assets-print/` **同级**。打印版 HTML 里的相对路径靠这一点才能解析。
- `pages/*.html` 里的图写 `../assets/...`（因为它在 `pages/` 下一层），合并脚本会把它改成 `assets/...`。

## 七步流程

| 步骤 | 做什么 | 产出 | 详细说明 |
| --- | --- | --- | --- |
| 1 | 输入与素材盘点 | 素材清单、缺口列表 | `references/input-and-assets.md` |
| 2 | 大纲与文案策划 | 页序表：文件名 + 标题 + 页脚页码 | `references/content-planning.md` |
| 3 | 视觉资产生成与清洗 | `assets/` 下的高清源图 | `references/visual-assets.md` |
| 4 | HTML/CSS 页面工程 | `pages/*.html` + `styles/catalog.css` | `references/page-engineering.md` |
| 5 | 渲染出图与 PDF 合成 | `输出/*.png` + 打印版 PDF | `references/render-and-delivery.md` |
| 6 | 质检 | 一致性报告 + PDF 图片体积表 | `references/qa-checklist.md` |
| 7 | 版本与交付 | 提交 / 打包 / 交付说明 | 见下方「版本管理」 |

第 1–3 步做完再进第 4 步。页序表先定死，后面改版的成本最低。

## 标准流水线

`$skill` 是本 skill 目录，`$root` 是图册工程根目录（用绝对路径），`<名称>` 是图册名，
**默认 = `$root` 的目录名**（`build_catalog_html.py` 不传 `--out` 时就是 `$root\<root 目录名>.html`）。
工程目录名和图册名不一致时（例如目录叫 `图册工程`、图册叫 `TaiWoo产品图册`），下面每处都必须显式传参。

```powershell
python "$skill\scripts\build_catalog_html.py" --root $root --out "$root\<名称>.html"
node   "$skill\scripts\measure_assets.cjs" --html "$root\<名称>.html" --out "$root\tmp\asset-usage.json" --playwright "<playwright-core 所在目录>"
pwsh -NoProfile -File "$skill\scripts\reset_print_assets.ps1" -Root $root
python "$skill\scripts\build_print_sources.py" --root $root
pwsh -NoProfile -File "$skill\scripts\render_pages.ps1" -Root $root
pwsh -NoProfile -File "$skill\scripts\export_pdf.ps1" -Html "$root\<名称>-print.html" -Out "$root\输出\<名称>.pdf"
python "$skill\scripts\check_pages.py" --root $root --html "$root\<名称>.html"
python "$skill\scripts\inspect_pdf_images.py" "$root\输出\<名称>.pdf"
```

顺序不能换：`reset_print_assets.ps1` 和 `measure_assets.cjs` 都要在 `build_print_sources.py` 之前，
`build_catalog_html.py` 要在 `measure_assets.cjs` 之前（量的是合并后的 HTML）。

各脚本参数：

- `build_catalog_html.py --root <dir> [--out <file>] [--title <title>]`
- `measure_assets.cjs --html <file> --out <json> --playwright <dir> [--chrome <exe>]`
- `reset_print_assets.ps1 -Root <dir>`
- `build_print_sources.py --root <dir> [--usage <json>] [--out-dir <dir>] [--html <file>] [--dpi 300] [--quality 92] [--max-side 3400]`
- `render_pages.ps1 -Root <dir> [-Only 01-cover.html,02-toc.html] [-Browser <exe>] [-OutDir <dir>]`
- `export_pdf.ps1 -Html <file> -Out <file> [-Chrome <exe>]`
- `check_pages.py [--root <dir>] [--html <file>]`
- `inspect_pdf_images.py <pdf>`

## 硬性技术约束

这些是踩过坑换来的，别绕过去：

1. **不做 PDF 事后压缩。** Ghostscript 之类会把封面、章节页的黑色渐变遮罩压出条带。要减体积就从图片源头减：按版面真实尺寸定像素、够 300 DPI 就行。
2. **图片必须是源头高清。** 生成或获取素材时就按大尺寸出图（版面毫米尺寸 × 300 DPI），不要靠事后放大。放大出来的图在成品 PDF 里一放大就糊。
3. **抠图按底色合成 JPEG。** 版面上只有白底和藏青 `#101A3D` 两种底，抠好的透明 PNG 就按所在底色合成成 JPEG，别让 PDF 里塞一堆带遮罩的 PNG（体积大，还容易出白边）。
4. **只有被滤镜影响的图才保留透明通道。** 图片自身或祖先元素带 `filter` / `opacity` < 1 / `mix-blend-mode`（例如封底 logo 用 `invert` 变白）时，合成到背景色会算错，这种情况存 PNG。
5. **回拷原图有前提。** 只有源文件本身就是 `.jpg`/`.jpeg` 才允许「产物不比源小就用源」。webp/png 的数据套着 `.jpg` 文件名，Chrome 打印时会重新解码成未压缩位图，PDF 体积翻几倍。
6. **渲染前清浏览器 profile。** Edge/Chrome 会缓存 `file://` 的同名图，素材换了内容不清缓存就会渲染出旧图。`render_pages.ps1` 每次重建 `tmp/edge-profile-render`。
7. **`.ps1` 里只用 ASCII。** Windows PowerShell 5.1 读无 BOM 的 `.ps1` 会按 ANSI 解，中文字面量会变成乱码路径。需要中文目录名时用 `[char]` 拼，例如 `[char]0x8F93 + [char]0x51FA` = 「输出」。
8. **打印分页靠 CSS。** `@page { size: 210mm 297mm; margin: 0; }` 加 `.sheet { break-after: page; }`，最后一页 `break-after: auto`，否则会多出一张空白页。
9. **页面唯一编号来源是文件名。** 文件名前两位是页码，页脚 `<span class="pn">N</span>` 必须跟它一致，`check_pages.py` 会核对。

## 规格与品牌

- 成品 210 × 297 mm A4 竖版；含出血 216 × 303 mm；安全边 10 mm；装订方式胶装。
- 品牌色：主色 `#101A3D`，辅助 `#2F3C68`、`#435082`，浅底 `#F4F6FB`、`#DCE3EF`。
- 字体：中文思源黑体 SC，英文 Inter / Helvetica Neue。正文 9.5 pt、行距 1.7。
- 印刷：图片 300 dpi，色彩 `CMYK US Web Coated (SWOP) v2`。
- 页脚：`taiwooeyewear.com | sales@taiwooeyewear.com | WhatsApp +86 13959244463`。
- 品牌事实（不要编）：2013-06-05 成立，眼镜 OEM/ODM，主打 RX 运动护目镜，年产能约 5,000,000 副；SGS ISO 9001:2015（证书 CN12/30945）、U.S. FDA 工厂注册（3012748937）、6 个月质保。
- 文字禁忌：不写 `FDA approved`、`cheapest`、`best in the world`；不把 ISO 9001 说成产品认证。
- 图片编辑边界：可去背、补光、超分、统一背景、轻微校色、去水印；**不可**改外形结构比例、改镀膜颜色、加不存在的零件、用 AI 图替代真实产品图。

## 参考页序（TaiWoo 62 页图册）

P1–P10 前置页；Ch01 P11–P29 镜框；Ch02 P30–P41 镜片功能；Ch03 P42–P50 车房定制；Ch04 P51–P56 光学与眼健康；Ch05 P57–P61 防护与环保；P62 封底。

做新图册时照这个骨架换内容即可：封面 → 目录 → 关于我们 → 合作方式 → 流程 → 工厂与品质 → 资质 → 商务条款 → 分章产品页 → 封底。

## 版本管理

Skill 随 `D:\AITools\codex-skills` 分发，只提交 `SKILL.md`、`agents/`、`references/`、`scripts/`。

图册工程本体是否入库要单独跟用户确认。建议：`assets/`、`assets-print/`、`tmp/`、`输出/` 走 `.gitignore`，或者图片素材用 Git LFS；只把 `pages/`、`styles/`、脚本和成品 PDF 纳入版本管理。

## 验收

交付前必须全过：

- `check_pages.py` 输出 `all consistent`（页数、页码、素材引用、合并 HTML 全部一致）
- PDF 文字可以选中、可以搜索（说明是矢量文字，不是截图）
- `inspect_pdf_images.py` 里没有异常大图（正常单图几百 KB 级，出现几 MB 的就是没走 `assets-print/`）
- 合并 HTML 的 `<section class="sheet">` 数量 = 页数 = 最后页码
- 全文没有禁忌词
