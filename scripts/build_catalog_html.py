import argparse
import re
import sys
from pathlib import Path

LABELS = [
    ("01-cover.html", "P1 封面"),
    ("02-toc.html", "P2 目录"),
    ("03-about.html", "P3 关于 TaiWoo"),
    ("04-cooperation.html", "P4 三种合作方式"),
    ("05-process.html", "P5 从需求到量产"),
    ("06-factory.html", "P6 工厂与品质体系"),
    ("07-rx-lab.html", "P7 数字化车房"),
    ("08-certificates.html", "P8 资质文件"),
    ("09-terms.html", "P9 商务条款与联系"),
    ("10-partners.html", "P10 合作品牌"),
    ("11-chapter-01.html", "P11 第一章 运动光学系统"),
    ("12-splicing.html", "P12 拼接式定制流程"),
    ("13-inlay.html", "P13 无框内嵌式定制流程"),
    ("14-scenes.html", "P14 六大运动场景"),
    ("15-warped-rx.html", "P15 高弯与高基弯处方运动镜"),
    ("16-frame-overview.html", "P16 镜框系列总览"),
    ("17-frames-sports.html", "P17 运动镜框 001-002"),
    ("18-frames-sports.html", "P18 运动镜框 003-004"),
    ("19-frames-sports.html", "P19 运动镜框 005-006"),
    ("20-frames-sports.html", "P20 运动镜框 007-008"),
    ("21-frames-sports.html", "P21 运动镜框 009-010"),
    ("22-frames-sports.html", "P22 运动镜框 011-019"),
    ("23-frames-sports.html", "P23 运动镜框 020-021"),
    ("24-frames-sports.html", "P24 运动镜框 022-023"),
    ("25-frames-sports.html", "P25 运动镜框 024"),
    ("26-frames-casual.html", "P26 休闲镜框 012-013"),
    ("27-frames-casual.html", "P27 休闲镜框 014-015"),
    ("28-frames-casual.html", "P28 休闲镜框 016-017"),
    ("29-frames-casual.html", "P29 休闲镜框 018"),
    ("30-chapter-02.html", "P30 第二章 功能镜片"),
    ("31-lens-logic.html", "P31 四种镜片，四种用法"),
    ("32-photochromic.html", "P32 变色镜片"),
    ("33-tinted.html", "P33 染色镜片"),
    ("34-polarized.html", "P34 偏光镜片"),
    ("35-high-contrast.html", "P35 高对比镜片"),
    ("36-blue-light.html", "P36 抗蓝光镜片"),
    ("37-coatings.html", "P37 表面处理与膜层"),
    ("38-structured.html", "P38 外观与结构工艺"),
    ("39-antifog.html", "P39 防雾镜片"),
    ("40-special-optics.html", "P40 多规格近视镜片与眼镜式放大镜"),
    ("41-ar-protection.html", "P41 AR 前后超薄保护镜片"),
    ("42-chapter-03.html", "P42 第三章 车房定制镜片"),
    ("43-thinner.html", "P43 镜片减薄系列"),
    ("44-large-diameter.html", "P44 大直径高基弯镜片"),
    ("45-casual-rx.html", "P45 休闲 RX 太阳镜片"),
    ("46-special-rx.html", "P46 特殊 RX 镜片"),
    ("47-color-rx.html", "P47 RX 彩色太阳镜片"),
    ("48-semi-finished.html", "P48 半成品 RX 基片"),
    ("49-blanks.html", "P49 单面颜色车房毛坯镜片"),
    ("50-casual-sun.html", "P50 一副镜子解决近视和遮光"),
    ("51-chapter-04.html", "P51 第四章 光学与眼健康镜片"),
    ("52-myopia.html", "P52 多点离焦镜片"),
    ("53-reading.html", "P53 老花、双光与渐进"),
    ("54-postop.html", "P54 术后与偏头痛滤光镜片"),
    ("55-sleep.html", "P55 睡眠镜片"),
    ("56-melanin.html", "P56 黑色素镜片"),
    ("57-chapter-05.html", "P57 第五章 防护与环保"),
    ("58-medical-goggle.html", "P58 医用隔离眼罩"),
    ("59-laser.html", "P59 激光防护镜片"),
    ("60-infrared.html", "P60 防红外镜片"),
    ("61-eco.html", "P61 回收材料镜片"),
    ("62-back-cover.html", "P62 封底"),
]

ORDER = [name for name, _ in LABELS]
TITLES = dict(LABELS)


def extract_body(html: str) -> str:
    match = re.search(r"(?is)<body[^>]*>(.*?)</body>", html)
    body = match.group(1).strip() if match else html
    # 单页文件放在 pages/ 下，图片写的是 ../assets/；
    # 合并后的文件放在工程根目录，路径要少一层。
    return body.replace("../assets/", "assets/")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge pages/*.html into a single catalogue HTML file."
    )
    parser.add_argument("--root", required=True, help="catalogue root holding pages/ and styles/")
    parser.add_argument(
        "--out",
        default=None,
        help="output html path (default: <root>/<root folder name>.html)",
    )
    parser.add_argument("--title", default="TaiWoo Eyewear Catalog", help="document title")
    return parser.parse_args(argv)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root / (root.name + ".html")
    css = (root / "styles" / "catalog.css").read_text(encoding="utf-8")

    blocks = []
    for index, name in enumerate(ORDER, start=1):
        source = root / "pages" / name
        body = extract_body(source.read_text(encoding="utf-8"))
        blocks.append(f'<section class="sheet" id="page-{index}">\n{body}\n</section>')

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{args.title}</title>
<style>
{css}

/* ---------- screen presentation ---------- */
body {{
  background: #E9EDF3;
  margin: 0;
  padding: 14mm 0 20mm;
}}

.sheet {{
  margin: 0 auto 12mm;
  box-shadow: 0 3mm 10mm rgba(16, 26, 61, 0.16);
  background: #FFFFFF;
  width: 210mm;
  height: 297mm;
}}

.sheet .page {{ box-shadow: none; }}

/* ---------- print ---------- */
@media print {{
  @page {{ size: 210mm 297mm; margin: 0; }}
  body {{ background: #FFFFFF; padding: 0; }}
  .sheet {{
    margin: 0;
    box-shadow: none;
    break-after: page;
    page-break-after: always;
  }}
  .sheet:last-child {{ break-after: auto; page-break-after: auto; }}
}}
</style>
</head>
<body>
{''.join(blocks)}
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    print(f"OK {out}")
    print(f"pages: {len(blocks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
