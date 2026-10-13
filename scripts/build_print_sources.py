"""为 PDF 导出准备一版体积可控的图片资源，并生成对应的合并 HTML。

不去压缩 PDF 本身（那会破坏封面与章节页的黑色渐变遮罩），
而是按 scripts/measure_assets.cjs 量出的真实版面尺寸重做图片：
  1. 每张图按其实际显示的毫米尺寸定分辨率，300 DPI 够印就行；
  2. 抠图（带透明通道）按它所在的底色合成成 JPEG —— 版面上只有白底和藏青底，
     这样既避免 PDF 里塞一堆带遮罩的 PNG，也不会出现白边。
文字仍是矢量，交给 Chrome 直接打印成 PDF。
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

DPI = 300
JPEG_QUALITY = 92
MAX_SIDE = 3400          # 上限，防止个别全幅图过大
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def has_alpha(im: Image.Image) -> bool:
    if im.mode in ("RGBA", "LA"):
        alpha = im.getchannel("A")
        return alpha.getextrema()[0] < 255
    if im.mode == "P":
        return "transparency" in im.info
    return False


def resize_factor(im: Image.Image, need_w: float, need_h: float) -> Image.Image:
    """按 300 DPI 需要的像素缩放，不放大。"""
    w, h = im.size
    factor = max(need_w / w, need_h / h, 1e-6)
    factor = min(1.0, factor)
    if factor >= 0.999:
        return im
    return im.resize((max(1, round(w * factor)), max(1, round(h * factor))), Image.LANCZOS)


def limit_max_side(im: Image.Image, max_side: int) -> Image.Image:
    w, h = im.size
    if max(w, h) <= max_side:
        return im
    factor = max_side / float(max(w, h))
    return im.resize((max(1, round(w * factor)), max(1, round(h * factor))), Image.LANCZOS)


def flatten(im: Image.Image, bg: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGB", im.size, bg)
    rgba = im.convert("RGBA")
    base.paste(rgba, mask=rgba.getchannel("A"))
    return base


def prepare(
    src: Path,
    dst: Path,
    need_w: float,
    need_h: float,
    bg: tuple[int, int, int],
    keep_alpha: bool = False,
) -> Path:
    """返回实际写出的目标路径（扩展名可能从 .png/.webp 变成 .jpg）。"""
    try:
        im = Image.open(src)
        im.load()
    except Exception:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst

    animated = getattr(im, "n_frames", 1) > 1
    if animated:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return dst

    out = resize_factor(im, need_w, need_h)

    if keep_alpha and has_alpha(out):
        # 版面给这张图加了滤镜/透明度，合成到背景上会算错，保留透明通道
        target = dst.with_suffix(".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        out.convert("RGBA").save(target, "PNG", optimize=True)
        if target.stat().st_size >= src.stat().st_size:
            shutil.copy2(src, target)
        return target

    if has_alpha(out):
        out = flatten(out, bg)
    else:
        out = out.convert("RGB")
    if max(out.size) > MAX_SIDE:
        out = limit_max_side(out, MAX_SIDE)

    target = dst.with_suffix(".jpg")
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target, "JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True)
    # 只有本来就是 JPEG 的源图才允许"原图更小就用原图"，
    # 否则会出现 webp/png 的数据套着 .jpg 文件名，Chrome 打印时会把它重新解码成
    # 未压缩位图塞进 PDF，体积翻好几倍。
    if src.suffix.lower() in {".jpg", ".jpeg"} and target.stat().st_size >= src.stat().st_size:
        shutil.copy2(src, target)
    return target


def load_usage(path: Path) -> dict:
    """从量的结果里得出每张图需要的像素尺寸和底色。"""
    if not path.exists():
        raise SystemExit(f"missing {path}; run scripts/measure_assets.cjs first")
    data = json.loads(path.read_text(encoding="utf-8"))
    mm_per_px = data.get("mmPerPx", 25.4 / 96)
    usage: dict[str, dict] = {}
    for row in data["rows"]:
        src = str(row["src"]).replace("\\", "/")
        if not src.startswith("assets/"):
            continue
        # 版面 CSS px -> 毫米 -> 300 DPI 需要的图片像素
        need_w = row["drawnW"] * mm_per_px / 25.4 * DPI
        need_h = row["drawnH"] * mm_per_px / 25.4 * DPI
        entry = usage.setdefault(src, {"w": 0.0, "h": 0.0, "bgs": set(), "filtered": False})
        entry["w"] = max(entry["w"], need_w)
        entry["h"] = max(entry["h"], need_h)
        entry["bgs"].add(row["bg"])
        entry["filtered"] = entry["filtered"] or bool(row.get("filtered"))
    return usage


def parse_rgb(value: str) -> tuple[int, int, int] | None:
    nums = re.findall(r"\d+(?:\.\d+)?", value or "")
    if len(nums) < 3:
        return None
    return tuple(int(round(float(n))) for n in nums[:3])  # type: ignore[return-value]


def main() -> int:
    global DPI, JPEG_QUALITY, MAX_SIDE
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Rebuild page images at print resolution and write a merged print HTML."
    )
    parser.add_argument("--root", default=".", help="catalog project root (default: cwd)")
    parser.add_argument("--html", default=None, help="merged catalog HTML (default: <root>/<root dir name>.html)")
    parser.add_argument("--usage", default=None, help="asset usage JSON from measure_assets.cjs (default: <skill>/tmp/asset-usage.json)")
    parser.add_argument("--out-dir", default=None, help="print image dir (default: <root>/assets-print)")
    parser.add_argument("--dpi", type=float, default=DPI, help="target print resolution (default: 300)")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help="JPEG quality (default: 92)")
    parser.add_argument("--max-side", type=int, default=MAX_SIDE, help="max pixels on the long side (default: 3400)")
    args = parser.parse_args()

    DPI = args.dpi
    JPEG_QUALITY = args.quality
    MAX_SIDE = args.max_side

    root = Path(args.root).resolve()
    html_path = Path(args.html).resolve() if args.html else root / (root.name + ".html")
    out_root = Path(args.out_dir).resolve() if args.out_dir else root / "assets-print"
    usage_path = (
        Path(args.usage).resolve()
        if args.usage
        else Path(__file__).resolve().parent.parent / "tmp" / "asset-usage.json"
    )

    if not html_path.exists():
        raise SystemExit(f"catalog HTML not found: {html_path}")
    if not out_root.is_relative_to(root):
        raise SystemExit(f"--out-dir must stay inside --root: {out_root}")
    if not (root / "assets").is_dir():
        raise SystemExit(f"no assets/ dir under {root}")

    html = html_path.read_text(encoding="utf-8")
    refs = sorted({m.group(0) for m in re.finditer(r"assets/[^\"')\s>]+", html)})
    usage = load_usage(usage_path)

    mapping: dict[str, str] = {}
    saved_before = saved_after = 0

    for ref in refs:
        src = root / ref
        if not src.exists() or src.is_dir():
            continue
        info = usage.get(ref)
        try:
            with Image.open(src) as probe:
                natural = probe.size
        except Exception:
            natural = (MAX_SIDE, MAX_SIDE)
        need_w = info["w"] if info else float(natural[0])
        need_h = info["h"] if info else float(natural[1])
        bgs = {parse_rgb(b) for b in (info["bgs"] if info else set())}
        bgs.discard(None)
        bg = bgs.pop() if len(bgs) == 1 else (255, 255, 255)

        rel = Path(ref).relative_to("assets")
        dst_base = out_root / rel
        if src.suffix.lower() in IMAGE_EXT:
            dst = prepare(src, dst_base, need_w, need_h, bg, keep_alpha=bool(info and info.get("filtered")))
        else:
            dst = dst_base
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        mapping[ref] = str(dst.relative_to(root)).replace("\\", "/")
        saved_before += src.stat().st_size
        saved_after += dst.stat().st_size

    def replace(match: re.Match) -> str:
        return mapping.get(match.group(0), match.group(0))

    new_html = re.sub(r"assets/[^\"')\s>]+", replace, html)

    # 必须和 assets-print/ 同级，HTML 里的相对路径才能解析
    out_html = html_path.with_name(html_path.stem + "-print.html")
    out_html.write_text(new_html, encoding="utf-8")

    print(f"OK {out_html}")
    print(f"assets: {len(mapping)}  {saved_before / 1048576:.1f} MB -> {saved_after / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
