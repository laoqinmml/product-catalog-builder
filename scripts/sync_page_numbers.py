#!/usr/bin/env python3
"""Sync each page footer page number with its two-digit filename prefix.

Usage:
    python scripts/sync_page_numbers.py [--root <catalog-root>]

The cover and the back cover carry no page number and are skipped.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PN_RE = re.compile(r'<span class="pn">\d*</span>')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="catalog root (default: cwd)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    pages = root / "pages"
    changed = 0

    for path in sorted(pages.glob("*.html")):
        name = path.name
        if name == "01-cover.html" or name.endswith("back-cover.html"):
            continue
        try:
            number = int(name[:2])
        except ValueError:
            print(f"WARN {name}: filename does not start with a page number")
            continue
        text = path.read_text(encoding="utf-8")
        new_text, count = PN_RE.subn(f'<span class="pn">{number:02d}</span>', text)
        if count == 0:
            print(f"WARN {name}: page number span not found")
            continue
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
            print(f"{name} -> {number:02d}")

    print(f"updated {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
