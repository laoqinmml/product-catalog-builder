# 上网用图：WebP

图册素材是按印刷标准准备的：300 DPI、大画幅、保留细节。同一套切图直接搬进网页，一张产品卡就可能背上几百 KB。上网前必须重新编码。

## 规则

1. **网页只发 WebP。** 产品图、场景图、首图统一导出 WebP（quality 82；带透明通道的用 RGBA，WebP 支持 alpha），HTML 里只引用 `.webp`。
2. **不要做 JPG/PNG 双份 fallback。** 现代浏览器都支持 WebP，多留一份只会让部署体积翻倍，而且那份永远没人下载。
3. **两个例外**：`og:image` 用 JPG（社交平台的兼容性更稳），iOS 的 `apple-touch-icon` 用 PNG（iOS 不认 WebP 图标）。
4. **按显示尺寸导出。** 版面上 400 px 宽的图就导出 800 px（2x），不要拿 3000 px 原图让浏览器缩，缩放省不了流量。
5. **验收线**：单张产品图 < 120 KB；首页全部图片合计 < 1 MB。超了就是没压。

## 实测（2026-11，A4 产品图册切图 → 站点）

| 文件 | 原格式 | WebP |
| --- | --- | --- |
| 中空扳手（透明底） | PNG 773 KB | 65 KB |
| 液压泵（透明底） | PNG 767 KB | 59 KB |
| 驱动扳手（白底） | JPG 103 KB | 38 KB |
| 拉力器（透明底） | PNG 179 KB | 15 KB |
| 图片目录合计 | 6.6 MB | 2.2 MB |

带透明通道的图不能转成 JPG —— 白底会变成硬边；WebP 的 alpha 才是正确落点。

## 转换（Pillow）

```python
from PIL import Image

# 白底图
Image.open("product.jpg").convert("RGB").save("product.webp", "WEBP", quality=82, method=6)

# 透明底图：保留 RGBA
Image.open("product.png").convert("RGBA").save("product.webp", "WEBP", quality=82, method=6)
```

Pillow 需要带 WebP 支持（`pip install Pillow` 的官方 wheel 默认就有）。

## 检查

```powershell
# 目录里还有没有漏网的位图
Get-ChildItem public\images -Recurse -Include *.png,*.jpg,*.jpeg

# 最大的十张，看有没有漏压
Get-ChildItem public\images -File | Sort-Object Length -Descending | Select-Object -First 10 Name,@{n='KB';e={[math]::Round($_.Length/1KB)}}
```

## 常见坑

- **只压了缩略图，产品大图还是 PNG。** 产品卡是最常被打开的地方，先压它。
- **用图片压缩网站逐张手工压。** 几十张以后一定会漏，写进构建脚本或一次性脚本里跑。
- **压完不检查渲染。** WebP 有损压缩在纯色背景和细螺丝纹理上会出块，quality 82 一般够，出现色带就提到 88 再压一次。
- **把 og:image 也换成 WebP。** 部分社交平台抓不到预览图，保持 JPG。
