# 步骤 6：质检

目标：在交付之前，用脚本 + 肉眼双重确认「页数、页码、素材引用、PDF 图片体积」都对得上。产物是一份照得出的验收结论。

## 输入是什么

完整的 `root/`：`pages/`、`assets/`、`assets-print/`、合并 HTML、`输出/<名称>.pdf`。

## 脚本自检

```powershell
# 一致性：页数、页码、素材引用、合并 HTML
python "$skill\scripts\check_pages.py" --root $root

# PDF 内嵌图片体积表
python "$skill\scripts\inspect_pdf_images.py" "$root\输出\<名称>.pdf"
```

`check_pages.py` 查这些，任何一条不过就打印 `PROBLEMS:` 并以退出码 1 结束：

- `pages/` 文件名编号连续，无缺号无重号
- 每页 `<span class="pn">N</span>` 与文件名前两位一致（跳过 `01-cover.html` 与 `*back-cover.html`）
- 页面里 `src="../assets/..."` 的每个文件真实存在
- `render.cjs` 清单、`LABELS` 与 `pages/` 目录三处一致
- 合并 HTML 的 `<section class="sheet">` 数 = 页数
- 合并 HTML 里 `src="assets/..."` 的每个文件真实存在

期望输出：`pages: N  sheets: M` 然后 `all consistent`。

`inspect_pdf_images.py` 打印 `unique images: N   streams total: X MB` 和体积前 20 的图。正常单图几百 KB 级；出现几 MB 的说明那张图没走 `assets-print/`。

## 肉眼验收

脚本查不出「好不好看」，这部分必须人看：

- 逐页 PNG 或直接在 PDF 里翻，看错位、糊图、裁切、空白页。
- PDF 里搜一个正文词，能搜到 = 文字是矢量不是截图。
- 封面、章节页的黑色渐变没有条带。
- 产品图的底色统一（白 / 藏青），抠图边缘没有白边或灰边。

## 验收清单（交付前必须全过）

- [ ] `check_pages.py` 输出 `all consistent`。
- [ ] PDF 文字可以选中、可以搜索。
- [ ] `inspect_pdf_images.py` 里没有异常大图（没有几 MB 的单图）。
- [ ] 合并 HTML 的 `<section class="sheet">` 数量 = 页数 = 最后页码。
- [ ] 全文没有禁忌词：`FDA approved`、`cheapest`、`best in the world`；ISO 9001 没被写成产品认证。
- [ ] 逐页肉眼过一遍，无错位、糊图、裁切、多余空白页。
- [ ] 页脚联系方式、品牌名正确。
- [ ] 硬事实（成立日期、证书编号、产能、认证）与来源一致。

## 素材要上网页时，额外过这几条

- [ ] `public/images` 里没有 `.png` / `.jpg` 漏网（`og:image` 与 `apple-touch-icon` 除外）。
- [ ] 单张产品图 < 120 KB，首页图片合计 < 1 MB。
- [ ] 透明底的图仍然保留 alpha（转成了 WebP，没有硬压成白底 JPG）。
- [ ] 页面上引用的图片路径全部返回 200，没有 404 的旧文件名。
- [ ] 换图后链接带内容哈希或改过文件名，长缓存不会让访客看到旧图。

## 上线后（GA4 与收录）

- [ ] GA4 的 `gcs` 参数自查过：未同意 `G100`、同意后 `G101`，不是一开始就 granted。
- [ ] `grep -r "G-" dist | wc -l` 等于页面数，没有漏埋的页面。
- [ ] 同意条点了「接受」会写 `_ga`，点「拒绝」不上报，刷新后不再弹。
- [ ] sitemap 里的域名是正式域名，不是模板占位。
- [ ] Search Console 显示「已成功验证」，站点地图状态为「成功」。
- [ ] `site:域名` 24–48 小时后能搜到自己。

## 常见坑

- **只看脚本绿了就交付。** 脚本查一致性，查不出排版难看。肉眼看一遍是硬要求。
- **PDF 体积大就上 Ghostscript。** 会压坏黑色渐变，正确做法是回步骤 5 从图片源头减。
- **搜不到文字以为是字体问题。** 多半是整页被当成图片贴进去了，回步骤 5 检查渲染参数。
