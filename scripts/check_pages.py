#!/usr/bin/env python3
"""Consistency check for the catalogue pages.

Verifies that file numbering, the printed page number in the footer, the file
order in render.cjs and the LABELS order in build_catalog_html.py all agree, and
that every referenced asset exists.

Usage:
    python scripts/check_pages.py [--root <catalogue root>] [--html <combined.html>]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that the catalogue pages, page numbers, asset refs and the combined HTML agree."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="catalogue root: the folder that holds pages/ and assets/ (default: cwd)",
    )
    parser.add_argument(
        "--html",
        default=None,
        help="combined HTML to check (default: <root>/<root folder name>.html; skipped if absent)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    root = Path(args.root).resolve()
    pages = root / "pages"
    html_path = Path(args.html).resolve() if args.html else root / f"{root.name}.html"
    problems: list[str] = []

    files = sorted(p.name for p in pages.glob("*.html"))
    numbers = [int(name[:2]) for name in files]
    expected = list(range(1, len(files) + 1))
    if numbers != expected:
        problems.append(f"file numbering is not contiguous: {numbers}")

    for name in files:
        text = (pages / name).read_text(encoding="utf-8")
        number = int(name[:2])
        match = re.search(r'<span class="pn">(\d+)?</span>', text)
        if name in {"01-cover.html"} or name.endswith("back-cover.html"):
            continue
        if not match:
            problems.append(f"{name}: footer page number missing")
        elif int(match.group(1)) != number:
            problems.append(f"{name}: footer says {match.group(1)}, file name says {number}")
        for ref in re.findall(r'src="\.\./(assets/[^"]+)"', text):
            if not (root / ref).exists():
                problems.append(f"{name}: missing asset {ref}")

    render_path = root / "render.cjs"
    if render_path.exists():
        render = render_path.read_text(encoding="utf-8")
        listed = re.findall(r'^  "(\d{2}-[a-z0-9\-]+\.html)",$', render, re.M)
        if listed != files:
            problems.append("render.cjs list does not match the page directory")

    labels_source = Path(__file__).resolve().parent / "build_catalog_html.py"
    labels = re.findall(
        r'\("(\d{2}-[a-z0-9\-]+\.html)", "P\d+',
        labels_source.read_text(encoding="utf-8"),
    )
    if labels != files:
        problems.append("LABELS order does not match the page directory")

    sheets = 0
    if html_path.exists():
        combined = html_path.read_text(encoding="utf-8")
        sheets = len(re.findall(r'<section class="sheet"', combined))
        if sheets != len(files):
            problems.append(f"combined html has {sheets} sheets, expected {len(files)}")
        for ref in re.findall(r'src="assets/([^"]+)"', combined):
            if not (root / "assets" / ref).exists():
                problems.append(f"combined html: missing asset {ref}")

    print(f"pages: {len(files)}  sheets: {sheets}")
    if problems:
        print("\nPROBLEMS:")
        for item in problems:
            print(f"  - {item}")
        return 1
    print("all consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
