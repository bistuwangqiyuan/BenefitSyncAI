# -*- coding: utf-8 -*-
"""把若干 SVG 拼成一张 PNG，用于人工核对字形、配色与排版。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(names: list[str], out: str = "out/_preview.png"):
    from playwright.sync_api import sync_playwright

    svgs = []
    for n in names:
        p = ROOT / "charts" / n
        svgs.append(f'<figure><figcaption>{n}</figcaption>{p.read_text(encoding="utf-8")}</figure>')
    html = (
        "<html><head><meta charset='utf-8'><style>"
        "body{background:#fff;margin:0;padding:16px;font:12px 'Microsoft YaHei';}"
        "figure{margin:0 0 18px;} figcaption{color:#6E6E73;margin-bottom:4px;}"
        "svg{max-width:960px;height:auto;display:block;}"
        "</style></head><body>" + "".join(svgs) + "</body></html>"
    )
    tmp = ROOT / "out" / "_preview.html"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_text(html, encoding="utf-8")

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=2)
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(ROOT / out), full_page=True)
        b.close()
    print(ROOT / out)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args or ["trends_zero.svg", "jcurve.svg"])
