# 产品图册生成器 · Product Catalog Builder

一个 Codex Skill：把「做一本产品图册」拆成七步可重跑的流水线 —— 素材盘点 → 文案策划 → 视觉资产 → 页面工程 → 渲染出图 → 质检 → 交付，最终产出 210 × 297 mm A4 印刷级 PDF。

- **每步可单独重跑**：改一页文案不用从头走全流程。
- **出的是真印刷文件**：PDF 里文字是矢量的，可以选中、可以搜索。
- **图片按版面物理尺寸定点**：300 DPI 够用就不多给一个像素。
- **不做 PDF 事后压缩**：封面和章节页的黑色渐变不会被压出条带。
- **自带质检**：页码、素材引用、合并 HTML、PDF 图片体积，一条命令核完。

---

## 适用场景

用得上这个 skill 的时候：

- 从零做一本产品图册 / 产品画册 / 产品目录 / 产品手册。
- 已有图册要加页、换图、改文案、重排版。
- 重新导出 PDF，或者修「PDF 体积暴涨」「图片放大就糊」「抠图有白边」「页脚页码和文件名对不上」「封面黑色渐变被压坏」。

不管这本书是什么产品，流水线和脚本都通用；需要替换的是品牌、页序和文案（见[规格与品牌](#规格与品牌)）。

## 七步流程

| 步骤 | 做什么 | 产出 | 详细说明 |
| --- | --- | --- | --- |
| 1 | 输入与素材盘点 | 素材清单、缺口列表 | [`references/input-and-assets.md`](references/input-and-assets.md) |
| 2 | 大纲与文案策划 | 页序表：文件名 + 标题 + 页脚页码 | [`references/content-planning.md`](references/content-planning.md) |
| 3 | 视觉资产生成与清洗 | `assets/` 下的高清源图 | [`references/visual-assets.md`](references/visual-assets.md) |
| 4 | HTML/CSS 页面工程 | `pages/*.html` + `styles/catalog.css` | [`references/page-engineering.md`](references/page-engineering.md) |
| 5 | 渲染出图与 PDF 合成 | `输出/*.png` + 打印版 PDF | [`references/render-and-delivery.md`](references/render-and-delivery.md) |
| 6 | 质检 | 一致性报告 + PDF 图片体积表 | [`references/qa-checklist.md`](references/qa-checklist.md) |
| 7 | 版本与交付 | 提交 / 打包 / 交付说明 | 见[版本管理建议](#版本管理建议) |

第 1–3 步做完再进第 4 步。**页序表先定死**，后面改版成本最低。

## 安装

### 依赖

| 组件 | 用在哪 | 说明 |
| --- | --- | --- |
| Python 3.9+ | 4 个 `.py` 脚本 | 需要 `Pillow`（`build_print_sources.py`）和 `pikepdf`（`inspect_pdf_images.py`） |
| Node.js | `measure_assets.cjs` | 需要 `playwright-core`，用 `--playwright <所在目录>` 指过去 |
| Microsoft Edge 或 Google Chrome | 页面渲染、打印 PDF | 无头模式调用 |
| PowerShell 5.1+ / PowerShell 7 | 3 个 `.ps1` 脚本 | 内容全部是 ASCII，中英文环境都能跑 |

```powershell
python -m pip install Pillow pikepdf
```

### 放进 skills 目录

Codex 从 skills 根目录读取 skill，目录名必须保持 `product-catalog-builder`：

```powershell
# 方式一：直接复制进去
Copy-Item -Recurse -Force "D:\AITools\codex-skills\product-catalog-builder" "$env:USERPROFILE\.codex\skills\"

# 方式二：skill 放在别的盘，用 junction 挂进来（Windows 不需要管理员权限）
New-Item -ItemType Junction -Path "$env:USERPROFILE\.codex\skills\product-catalog-builder" -Target "D:\AITools\codex-skills\product-catalog-builder"
```

装完自检：

```powershell
$env:PYTHONUTF8 = 1
python "$env:USERPROFILE\.codex\skills\product-catalog-builder\scripts\check_pages.py" --help
```

> 中文环境下跑 Python 脚本前先设 `$env:PYTHONUTF8 = 1`。否则 Windows 上用 GBK 读 UTF-8 源码会报 `UnicodeDecodeError`。

## 工程目录约定

`root` 指图册工程根目录，结构固定：

```text
root/
  pages/                     # 每页一个 HTML：01-xxx.html ... NN-yyy.html
  styles/catalog.css         # 全部版面样式
  assets/                    # 版面用图（源头就是高清大图）
  assets-print/              # 派生目录：按版面真实尺寸重做的打印图（自动生成，不要手改）
  tmp/                       # 中间产物、无头浏览器 profile（不入版本库）
  输出/                      # 单页渲染 PNG + 最终 PDF
  <名称>.html                # 合并后的网页版（自动生成）
  <名称>-print.html          # 指向 assets-print/ 的打印版（自动生成）
```

两条硬规矩：

1. `-print.html` 必须和 `assets-print/` **同级**，打印版 HTML 里的相对路径靠这一点才能解析。
2. `pages/*.html` 里的图写 `../assets/...`（它在 `pages/` 下一层），合并脚本会统一改写成 `assets/...`。

## 标准流水线

`$skill` 是 skill 目录，`$root` 是图册工程根目录（**用绝对路径**），`<名称>` 是图册名。

图册名默认等于 `$root` 的目录名；工程目录名和图册名不一致时（例如目录叫「图册工程」、图册叫「TaiWoo产品图册」），下面每一处都必须显式传参 —— 合并 HTML 的实际文件名以 `--out` 为准。

```powershell
$skill = "$env:USERPROFILE\.codex\skills\product-catalog-builder"
$root  = "C:\path\to\<图册工程>"
$名称  = "我的产品图册"

# 1) 合并单页 HTML -> 整本网页版
python "$skill\scripts\build_catalog_html.py" --root $root --out "$root\$名称.html"

# 2) 浏览器实测每张图的真实显示尺寸 -> 素材用量表
node "$skill\scripts\measure_assets.cjs" --html "$root\$名称.html" --out "$root\tmp\asset-usage.json" --playwright "<playwright-core 所在目录>"

# 3) 清空派生目录（避免残留旧图被渲染命中）
pwsh -NoProfile -File "$skill\scripts\reset_print_assets.ps1" -Root $root

# 4) 按用量表重做打印图 -> assets-print/
python "$skill\scripts\build_print_sources.py" --root $root

# 5) 逐页渲染 PNG -> 输出/
pwsh -NoProfile -File "$skill\scripts\render_pages.ps1" -Root $root

# 6) 打印 PDF
pwsh -NoProfile -File "$skill\scripts\export_pdf.ps1" -Html "$root\$名称-print.html" -Out "$root\输出\$名称.pdf"

# 7) 质检
python "$skill\scripts\check_pages.py" --root $root --html "$root\$名称.html"
python "$skill\scripts\inspect_pdf_images.py" "$root\输出\$名称.pdf"
```

顺序不能换：

- `build_catalog_html.py` 必须在 `measure_assets.cjs` 之前 —— 量的是合并后的 HTML。
- `reset_print_assets.ps1` 和 `measure_assets.cjs` 都必须在 `build_print_sources.py` 之前。

## 脚本速查

| 脚本 | 作用 | 关键参数 |
| --- | --- | --- |
| `build_catalog_html.py` | 把 `pages/*.html` 按文件名顺序合并成整本 HTML，并把 `../assets/` 改写成 `assets/` | `--root` `[--out]` `[--title]` |
| `measure_assets.cjs` | 无头浏览器打开合并 HTML，量出每张图的实际显示尺寸 | `--html` `--out` `--playwright` `[--chrome]` |
| `reset_print_assets.ps1` | 清空 `assets-print/`，防止旧图残留被命中 | `-Root` |
| `build_print_sources.py` | 按用量表 + 目标 DPI 重做打印图，抠图按底色合成 JPEG | `--root` `[--usage]` `[--out-dir]` `[--html]` `[--dpi 300]` `[--quality 92]` `[--max-side 3400]` |
| `render_pages.ps1` | 逐页渲染 PNG，每次重建浏览器 profile | `-Root` `[-Only 01-cover.html,02-toc.html]` `[-Browser]` `[-OutDir]` |
| `export_pdf.ps1` | 用打印版 HTML 导出 PDF | `-Html` `-Out` `[-Chrome]` |
| `check_pages.py` | 核对页数、文件名页码、页脚页码、素材引用、合并 HTML 是否一致 | `[--root]` `[--html]` |
| `inspect_pdf_images.py` | 列出 PDF 内每张图的像素与压缩后体积，揪异常大图 | `<pdf>` |
| `sync_page_numbers.py` | 按文件名把页脚页码批量改齐 | `[--root]` |

每个脚本都支持 `--help` / `-?`（`.ps1` 直接打开看头部 `param`）。

## 硬性技术约束

这几条是踩过坑换来的，别绕过去：

1. **不做 PDF 事后压缩。** Ghostscript 之类会把封面、章节页的黑色渐变遮罩压出条带。要减体积就从图片源头减：按版面真实尺寸定像素，够 300 DPI 就行。
2. **图片必须是源头高清。** 生成或获取素材时就按大尺寸出图（版面毫米尺寸 × 300 DPI），不要靠事后放大 —— 放大出来的图在成品 PDF 里一放大就糊。
3. **抠图按底色合成 JPEG。** 版面上通常只有白底和藏青 `#101A3D` 两种底，抠好的透明 PNG 就按所在底色合成成 JPEG。别让 PDF 里塞一堆带遮罩的 PNG：体积大，还容易出白边。
4. **只有被滤镜影响的图才保留透明通道。** 图片自身或祖先元素带 `filter`、`opacity` < 1、`mix-blend-mode`（例如封底 logo 用 `invert` 变白）时，合成到背景色会算错，这种情况存 PNG。
5. **回拷原图有前提。** 只有源文件本身就是 `.jpg` / `.jpeg` 才允许「产物不比源小就用源」。webp/png 的数据套着 `.jpg` 文件名时，Chrome 打印会把它们重新解码成未压缩位图，PDF 体积翻几倍。
6. **渲染前清浏览器 profile。** Edge/Chrome 会缓存 `file://` 的同名图，素材换了内容不清缓存就会渲染出旧图。`render_pages.ps1` 每次重建 `tmp/edge-profile-render`。
7. **`.ps1` 里只用 ASCII。** Windows PowerShell 5.1 读无 BOM 的 `.ps1` 会按 ANSI 解，中文字面量会变成乱码路径。需要中文目录名时用 `[char]` 拼，例如 `[char]0x8F93 + [char]0x51FA` =「输出」。
8. **打印分页靠 CSS。** `@page { size: 210mm 297mm; margin: 0; }` 加 `.sheet { break-after: page; }`，最后一页 `break-after: auto`，否则会多出一张空白页。
9. **页面编号唯一来源是文件名。** 文件名前两位是页码，页脚 `<span class="pn">N</span>` 必须跟它一致，`check_pages.py` 会核对。

## 规格与品牌

出厂默认值（换成自己的品牌即可）：

| 项 | 默认 |
| --- | --- |
| 开本 | 210 × 297 mm A4 竖版；含出血 216 × 303 mm；安全边 10 mm；胶装 |
| 品牌色 | 主色 `#101A3D`，辅助 `#2F3C68`、`#435082`，浅底 `#F4F6FB`、`#DCE3EF` |
| 字体 | 中文思源黑体 SC，英文 Inter / Helvetica Neue；正文 9.5 pt，行距 1.7 |
| 印刷 | 图片 300 dpi，色彩 `CMYK US Web Coated (SWOP) v2` |

仓库里 `SKILL.md` 和 `references/` 保留了一本真实图册（TaiWoo，62 页）作为示范，含页脚联系方式和品牌事实。**做自己的项目时这些都要替换**：

- **品牌事实不要编。** 成立时间、资质证书编号、产能、质保期，一律照实填。
- **文字禁忌。** 不写 `FDA approved`、`cheapest`、`best in the world`；不把 ISO 9001 说成产品认证。
- **图片编辑边界。** 可去背、补光、超分、统一背景、轻微校色、去水印；**不可**改外形结构比例、改镀膜颜色、加不存在的零件、用 AI 图替代真实产品图。

页序骨架可以直接照搬：封面 → 目录 → 关于我们 → 合作方式 → 流程 → 工厂与品质 → 资质 → 商务条款 → 分章产品页 → 封底。

## 质检清单

交付前必须全过：

- [ ] `check_pages.py` 输出 `all consistent`（页数、页码、素材引用、合并 HTML 全部一致）
- [ ] PDF 文字可以选中、可以搜索（说明是矢量文字，不是整页截图）
- [ ] `inspect_pdf_images.py` 里没有异常大图（正常单图几百 KB 级；出现几 MB 的就是没走 `assets-print/`）
- [ ] 合并 HTML 的 `<section class="sheet">` 数量 = 页数 = 最后页码
- [ ] 全文没有禁忌词

## 故障排查

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 成品 PDF 几十上百 MB | 图没走 `assets-print/`，或 webp/png 套着 `.jpg` 文件名 | 重跑 `build_print_sources.py`，别用 Ghostscript 压 |
| 放大后图片糊 | 素材按小图出、事后放大 | 回第 3 步，按「版面毫米 × 300 DPI」重新出图 |
| 抠图边缘有白边 | 透明 PNG 直接进了 PDF | 按底色（白 / `#101A3D`）合成 JPEG |
| 封面、章节页渐变出现条带 | 事后压缩 PDF | 删掉压缩步骤，从图片源头减体积 |
| 渲染出来还是旧图 | 浏览器缓存了 `file://` 同名图 | 重跑 `render_pages.ps1`（每次重建 profile） |
| 最后一页后面多一张空白页 | 末页 `break-after` 还是 `page` | 末页改 `break-after: auto` |
| 页脚页码和文件名对不上 | 手改过页脚或改过文件名 | 跑 `sync_page_numbers.py`，再跑 `check_pages.py` |
| `.ps1` 报找不到中文目录 | PS 5.1 按 ANSI 读脚本 | 脚本里只用 ASCII，中文用 `[char]0xXXXX` 拼 |
| 合并 HTML 找不到、页数是 0 | 工程目录名和图册名不一致，脚本按默认名找 | 显式传 `--html` / `--out` |

## 版本管理建议

Skill 本体只提交 `README.md`、`SKILL.md`、`agents/`、`references/`、`scripts/`。

**图册工程本体是否入库要单独决定。** 建议 `assets/`、`assets-print/`、`tmp/`、`输出/` 走 `.gitignore`，或者图片素材用 Git LFS；只把 `pages/`、`styles/`、脚本和成品 PDF 纳入版本管理。素材目录动辄几 GB，直接 `git add .` 会把仓库撑爆。

```gitignore
tmp/
**/__pycache__/
**/assets-print/
**/输出/
```

---

本 skill 由 [Codex](https://openai.com/codex) 使用。仓库暂未指定开源许可，如需明确授权请补一个 `LICENSE`。
