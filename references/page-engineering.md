# 步骤 4：HTML / CSS 页面工程

目标：把页序表和文案落成 `pages/*.html` + `styles/catalog.css`，并且能在浏览器里一页一屏地对着看。产物是页面源码。

## 输入是什么

步骤 2 的页序表（文件名、用途、页码）、步骤 3 的 `assets/` 图片，加上品牌 VI（色值、字体、logo）。

## 目录结构

```
root/
  pages/                # 一页一个 HTML，01-cover.html ... NN-back-cover.html
  styles/catalog.css    # 全部版面样式，所有页共用
  assets/               # 步骤 3 的图
  render.cjs            # 页面清单 + 批量截图工具（可选）
```

`build_catalog_html.py` 会把每个 `pages/*.html` 的 `<body>` 抠出来，拼成合并 HTML。所以：

- 每个 `pages/*.html` 是**完整可独立打开的 HTML**（有自己的 `<head>`、能直接双击看）。
- 合并版给每个页面套一层 `<section class="sheet">` 并内联 `styles/catalog.css`。
- 页面里的图写 `../assets/...`，合并脚本替换成 `assets/...`。

## 一页 = 一个 `.sheet`

页面根元素用 `.sheet`，尺寸和分页由 CSS 控制，不要写死在 HTML 里：

```css
.sheet { width: 210mm; height: 297mm; break-after: page; }
.sheet:last-child { break-after: auto; }   /* 最后一页不复位会多出空白页 */
@page { size: 210mm 297mm; margin: 0; }
```

- 版心：上 20 mm、左内 18 mm、右外 15 mm、下 ~22 mm。
- 正文 9.5 pt、行距 1.7；页脚 7.5 pt。
- 深色底页面（封面、章节页）用 `.sheet` 背景加渐变，不要用整图铺底。

## 页脚与页码

每页页脚结构固定，页码是**唯一编号来源**：

```html
<footer>taiwooeyewear.com | sales@taiwooeyewear.com | WhatsApp +86 13959244463</footer>
<span class="pn">11</span>
```

- `<span class="pn">N</span>` 里的数字必须等于文件名前两位。`check_pages.py` 会核对。
- 封面 `01-cover.html` 和封底 `*back-cover.html` 不带页码，校验时自动跳过。
- 页码不是手敲的——改完页面跑 `sync_page_numbers.py`，它按文件名回填。

## 图的写法

```html
<img src="../assets/tw-302-front.png" alt="TW-302 前视">
```

- 用 `<img>`，不要用 CSS 背景图放产品图——`measure_assets.cjs` 靠 `<img>` 的属性测真实绘制尺寸，背景图测不到。
- 需要裁剪/适配时用 `object-fit: contain | cover`，测量脚本会按它换算实际绘制宽高。
- 底色靠父容器 `background-color`（白或 `#101A3D`），不要给图片自己设底色。

## 页面清单三处同步

增删页必须同时改三处，否则 `check_pages.py` 报 `PROBLEMS`：

1. `pages/` 下的文件名
2. `render.cjs` 的页面清单（`"11-ch01-a.html",` 一行一个）
3. `build_catalog_html.py` 的 `LABELS`（`("11-ch01-a.html", "P11"),` 目录标签）

## 检查点（进步骤 5 之前必须过）

- [ ] 每个 `pages/*.html` 双击能独立打开，图片路径 `../assets/` 正确。
- [ ] 每页根元素是 `.sheet`，尺寸走 CSS，最后有 `break-after: auto` 复位。
- [ ] 每页页码 `<span class="pn">` 与文件名前两位一致（或已跑 `sync_page_numbers.py`）。
- [ ] `render.cjs` 清单、`LABELS` 与 `pages/` 目录三处一致。
- [ ] 产品图用 `<img>`，没有被写成 CSS 背景图。
- [ ] 没有绝对路径、没有指向工程外的图片。

## 常见坑

- **页码手敲。** 加页删页后手敲必然漏改。让 `sync_page_numbers.py` 回填。
- **最后一页忘了复位分页。** 会多出一张空白页，PDF 页数对不上。
- **产品图用背景图。** 测量脚本测不到，打印版会按错误尺寸重做，要么糊要么爆大。
- **页面里写死像素尺寸。** 换 A4 或改版心时全部返工，尺寸只写在 CSS 里。
