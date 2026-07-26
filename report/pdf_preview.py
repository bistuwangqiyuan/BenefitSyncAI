# -*- coding: utf-8 -*-
"""把 out/BP.pdf 栅格化成联系表和单页大图，供人工核对分页与中文字形。"""

from __future__ import annotations

import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
PREV = OUT / "preview"


def render(dpi: int = 96) -> list[Path]:
    PREV.mkdir(parents=True, exist_ok=True)
    for old in PREV.glob("p*.png"):
        old.unlink()
    doc = fitz.open(OUT / "BP.pdf")
    paths = []
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi)
        p = PREV / f"p{i:02d}.png"
        pix.save(p)
        paths.append(p)
    doc.close()
    return paths


def contact_sheets(paths: list[Path], cols: int = 5, rows: int = 3) -> list[Path]:
    per = cols * rows
    sheets = []
    thumbs = [Image.open(p) for p in paths]
    tw, th = thumbs[0].size
    scale = 260 / tw
    tw, th = int(tw * scale), int(th * scale)
    pad = 10
    for s in range((len(thumbs) + per - 1) // per):
        chunk = thumbs[s * per:(s + 1) * per]
        sheet = Image.new("RGB",
                          (cols * (tw + pad) + pad, rows * (th + pad) + pad),
                          (200, 200, 205))
        for i, im in enumerate(chunk):
            im = im.resize((tw, th), Image.LANCZOS)
            r, c = divmod(i, cols)
            sheet.paste(im, (pad + c * (tw + pad), pad + r * (th + pad)))
        out = OUT / f"_sheet{s + 1}.png"
        sheet.save(out)
        sheets.append(out)
    return sheets


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    paths = render()
    sheets = contact_sheets(paths)
    print(f"渲染 {len(paths)} 页 -> {PREV}")
    for s in sheets:
        print(f"联系表 {s}")


if __name__ == "__main__":
    main()
