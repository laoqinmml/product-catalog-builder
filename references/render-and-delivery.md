# 步骤 5：渲染出图与 PDF 合成

目标：把 `pages/` 渲染成单页 PNG（用于肉眼逐页核对），并合成一个**文字可选中、图片按版面尺寸重做**的打印版 PDF。产物是 `输出/*.png` 和最终 PDF。

## 输入是什么

步骤 4 的 `pages/` + `styles/catalog.css` + `assets/`。合并 HTML 由脚本生成，不用手写。

## 流水线顺序（不能换）

```powershell
# 1. 合并网页版 HTML（顺带确认页面引用都能解析）
python "$skill\scripts\build_catalog_html.py" --root $root

# 2. 量出每张图在版面里的真实绘制毫米尺寸
node "$skill\scripts\measure_assets.cjs" --html "$root\<名称>.html" --out "$root\tmp\asset-usage.json" --playwright "<playwright-core 目录>"

# 3. 清空并重建 assets-print/（派生目录，每次重做）
pwsh -NoProfile -File "$skill\scripts\reset_print_assets.ps1" -Root $root

# 4. 按测量结果重做打印图，生成 -print.html
python "$skill\scripts\build_print_sources.py" --root $root

# 5. 逐页截图，肉眼核对
pwsh -NoProfile -File "$skill\scripts\render_pages.ps1" -Root $root

# 6. 合成 PDF
pwsh -NoProfile -File "$skill\scripts\export_pdf.ps1" -Html "$root\<名称>-print.html" -Out "$root\输出\<名称>.pdf"
```

关键字：`measure_assets.cjs` 必须在 `build_print_sources.py` **之前**（后者读前者的 JSON）；`reset_print_assets.ps1` 也必须在 `build_print_sources.py` 之前（否则残留旧图）。

## 每步在做什么

| 脚本 | 输入 | 输出 | 关键点 |
| --- | --- | --- | --- |
| `build_catalog_html.py` | `pages/*.html`、`styles/catalog.css` | `<名称>.html` | 抠 `<body>` 拼装，`../assets/` → `assets/`，内联 CSS |
| `measure_assets.cjs` | `<名称>.html` | `tmp/asset-usage.json` | 无头浏览器量每张图的绘制宽高(mm)、底色、是否被滤镜影响 |
| `reset_print_assets.ps1` | — | 清空 `assets-print/` | 只删 `root/` 内路径，越界拒绝 |
| `build_print_sources.py` | 合并 HTML + JSON | `assets-print/` + `<名称>-print.html` | 按 300 DPI 重做图，抠图按底色合成 JPEG |
| `render_pages.ps1` | `pages/*.html` | `输出/*.png` | 逐页 2× 截图，重建 profile 防缓存 |
| `export_pdf.ps1` | `-print.html` | `输出/<名称>.pdf` | 浏览器打印成 PDF，保留矢量文字 |

## 图片重做的规则（`build_print_sources.py`）

- 目标像素 = 版面绘制毫米 × 300 DPI / 25.4，**只缩不放**。
- 抠图 + 白底/藏青底 → 合成 JPEG（`quality=92, subsampling=0, optimize=True`）。
- 被 `filter` / `opacity` < 1 / `mix-blend-mode` 影响的图 → 保留透明 PNG。
- **回拷原图有前提**：只有源文件本身是 `.jpg` / `.jpeg`，且产物不比源小，才允许用源。webp/png 套 `.jpg` 文件名的情况回拷会让 PDF 体积翻几倍。
- 单边超过 3400 px 的再压一次上限。

## 彩色 / 分页硬约束

- 成品 A4 210 × 297 mm；含出血 216 × 303 mm；安全边 10 mm。
- `@page { size: 210mm 297mm; margin: 0; }` 不可改。
- 印刷色彩空间 `CMYK US Web Coated (SWOP) v2`。
- **不做 PDF 事后压缩**（Ghostscript 之类会把黑色渐变压出条带）。要减体积只能从图片源头减。

## 环境依赖

- `measure_assets.cjs` 需要 `playwright-core`（可用 `tmp/pw/node_modules/playwright-core`）+ 一个 Chrome 内核浏览器。
- `render_pages.ps1` 用 Edge；`export_pdf.ps1` 用 Chrome/Edge。
- `build_print_sources.py` 需要 `Pillow`。
- `render_pages.ps1` 每次重建 `tmp/edge-profile-render`，避免浏览器缓存 `file://` 同名旧图。

## 检查点（进步骤 6 之前必须过）

- [ ] `render_pages.ps1` 末尾显示 `rendered k / n`，k = n，没有 `FAIL`。
- [ ] 逐页 PNG 肉眼过一遍：没有错位、没有糊图、没有半张图被裁。
- [ ] PDF 页数 = 页序表页数，没有多出空白页。
- [ ] PDF 文字可以选中、可以搜索。
- [ ] `assets-print/` 的大小远小于 `assets/`（重做生效）。

## 常见坑

- **顺序颠倒。** 先跑 `build_print_sources.py` 再量尺寸，打印图就按错误尺寸做，成品糊或爆大。
- **不清浏览器 profile。** 换了图但缓存没清，渲染出的是旧图。
- **用 Ghostscript 事后压 PDF。** 黑色渐变出条带，封面直接报废。
- **回拷了 webp 改名的 `.jpg`。** 浏览器打印时重新解码成未压缩位图，PDF 体积翻几倍。
