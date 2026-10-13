"""列出 PDF 里图片对象的体积/编码，用于判断还能压缩多少。"""

import argparse
import sys
from pathlib import Path

import pikepdf


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List the image objects inside a PDF with their byte size and encoding."
    )
    parser.add_argument("pdf", help="path to the PDF to inspect")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        raise SystemExit(f"pdf not found: {pdf_path}")
    pdf = pikepdf.open(pdf_path)
    rows = []
    seen = set()
    for page_index, page in enumerate(pdf.pages, start=1):
        for name, image in page.get_images().items():
            try:
                obj = image.obj
            except AttributeError:
                obj = pdf.get_object(image.objgen)
            key = obj.objgen
            if key in seen:
                continue
            seen.add(key)
            raw = obj.read_raw_bytes()
            rows.append(
                (
                    len(raw),
                    int(obj.get("/Width", 0)),
                    int(obj.get("/Height", 0)),
                    str(obj.get("/Filter")),
                    str(obj.get("/ColorSpace"))[:22],
                    page_index,
                    name,
                    "/SMask" in obj,
                )
            )
    rows.sort(key=lambda r: r[0], reverse=True)
    total = sum(r[0] for r in rows)
    print(f"unique images: {len(rows)}   streams total: {total / 1048576:.1f} MB")
    for r in rows[:20]:
        print(f"{r[0] / 1024:8.0f} KB  {r[1]}x{r[2]}  {r[3]:12} {r[4]:22} p{r[5]} {r[6]} smask={r[7]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
