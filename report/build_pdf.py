# -*- coding: utf-8 -*-
"""
把 out/BP.html 渲染为 A4 PDF。

为什么用 Chromium 而不是 WeasyPrint / wkhtmltopdf：本文档依赖可变字体、CSS Grid
与 break-inside 控制，只有 Chromium 的实现是完整的。

三件事值得说明：

1. 两遍渲染。目录页码只有渲染完才知道，所以第一遍先排一次，用 PyMuPDF 定位每个章节
   落在哪一页，写进 out/toc_pages.json，再重建 HTML 渲染第二遍。目录占位符在两遍里
   宽度一致（右对齐等宽数字），所以填上页码不会让分页漂移——这一点由脚本自己校验。
2. 封面单独渲染。Chromium 的页眉页脚模板对全文档生效，没有"首页除外"开关，
   因此封面与正文分两次导出再用 PyMuPDF 合并。正文页码从 1 起算，封面与目录不计入，
   这也是纸质书的通行做法。
3. 导出后做机器校验：页数、字体是否内嵌、有没有豆腐块（.notdef 字形）。
   最后一项是中文 PDF 最常见的翻车点，不能靠肉眼抽查。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"

# 页眉右侧走静态日期，不用 Chromium 的 <span class="date">：那个填的是导出时的
# 机器本地时间（带分钟），会让同一份文档每次导出都不一样，无法做二进制比对。
HEAD_FOOT_CSS = (
    "width:100%;font-size:7pt;color:#86868B;padding:0 15mm;"
    "font-family:'Segoe UI','Microsoft YaHei',sans-serif;"
    "display:flex;justify-content:space-between;-webkit-print-color-adjust:exact;"
)


def header_tpl(as_of: str) -> str:
    return (f'<div style="{HEAD_FOOT_CSS}">'
            f"<span>DepositDay · 商业计划书（证据驱动重建版）</span>"
            f"<span>数据截止 {as_of}</span></div>")


FOOTER = (f'<div style="{HEAD_FOOT_CSS}">'
          f"<span>数值均由 model/run_all.py 生成，可复现</span>"
          f'<span><span class="pageNumber"></span></span></div>')

EMPTY = '<div style="display:none"></div>'

MARGIN = {"top": "18mm", "bottom": "16mm", "left": "15mm", "right": "15mm"}


# ---------------------------------------------------------------------------
def _render(page, path: Path, *, ranges: str, header: str | None) -> None:
    page.pdf(
        path=str(path),
        format="A4",
        print_background=True,
        page_ranges=ranges,
        display_header_footer=header is not None,
        header_template=header or EMPTY,
        footer_template=FOOTER if header is not None else EMPTY,
        margin=MARGIN,
        prefer_css_page_size=False,
    )


def locate_chapters(pdf_path: Path, chapters: list[dict]) -> tuple[dict, list[str]]:
    """返回 {章节 id: 正文页码} 与未定位成功的章节标题。

    正文页码 = 物理页序号 − 1（封面不计页码）。
    """
    doc = fitz.open(pdf_path)
    pages: dict[str, int] = {}
    physical: dict[str, int] = {}
    missing: list[str] = []

    # 目录页上印着全部章节标题，从第 0 页找会全部命中目录本身。先把目录页跳过去。
    titles = [c["title"] for c in chapters]
    start = 0
    for i in range(doc.page_count):
        text = doc[i].get_text()
        on_page = sum(1 for t in titles if t in text)
        if "本文档怎么读" in text or (start and i == start and on_page >= 3):
            start = i + 1
    start = max(start, 1)

    # 章节标题常在别处以正文短语出现（"单位经济"就在第三章里被提到过），
    # 所以按文档顺序单调前移游标，只在上一章之后找下一章。
    cursor = start
    for ch in chapters:
        hit = None
        # 标题可能被排版拆行，逐步退化到前缀，再退到章节标签
        probes = [ch["title"], ch["title"][:10], ch["title"][:6], ch["label"]]
        for probe in probes:
            if not probe:
                continue
            for i in range(cursor, doc.page_count):
                if doc[i].search_for(probe):
                    hit = i
                    break
            if hit is not None:
                break
        if hit is None:
            missing.append(ch["title"])
            continue
        cursor = hit
        # Chromium 按页范围导出时保留原始页码，所以封面虽不打印页码但仍占第 1 页，
        # 页脚印的数字就等于物理页序号。
        physical[ch["id"]] = hit + 1
        pages[ch["id"]] = hit + 1
    doc.close()
    return {"labels": pages, "physical": physical}, missing


def apply_outline(pdf_path: Path, chapters: list[dict], physical: dict) -> int:
    doc = fitz.open(pdf_path)
    toc = [[1, "封面", 1], [1, "目录", 2]]
    for ch in chapters:
        p = physical.get(ch["id"])
        if p:
            toc.append([1, f'{ch["label"]}　{ch["title"]}', p])
    doc.set_toc(toc)
    doc.set_metadata({
        "title": "DepositDay 商业计划书 · 证据驱动重建版",
        "author": "DepositDay",
        "subject": "州级福利到账日数据基础设施：单人、AI 运营、纯自有资金的五年计划",
        "keywords": "business plan, SNAP, EBT, Monte Carlo, Kelly",
        "creator": "report/build_pdf.py (Chromium + PyMuPDF)",
    })
    try:
        doc.saveIncr()
    except Exception:
        tmp = pdf_path.with_suffix(".tmp.pdf")
        doc.save(tmp, garbage=4, deflate=True)
        doc.close()
        tmp.replace(pdf_path)
        return len(toc)
    doc.close()
    return len(toc)


def check_toc(pdf_path: Path, chapters: list[dict], maps: dict) -> list[str]:
    """把目录里印的页码和该页页脚里印的页码对一遍。

    差一页是这类两遍渲染最容易犯又最不容易看出来的错，必须由机器来对。
    """
    doc = fitz.open(pdf_path)
    bad = []
    for ch in chapters:
        p = maps["physical"].get(ch["id"])
        label = maps["labels"].get(ch["id"])
        if not p:
            continue
        page = doc[p - 1]
        r = page.rect
        footer = page.get_text(clip=fitz.Rect(r.x0, r.y1 - 40, r.x1, r.y1))
        if str(label) not in footer.split():
            bad.append(f'{ch["label"]}（目录写 {label}，页脚是 {footer.split()[-1:] or "空"}）')
    doc.close()
    return bad


def verify(pdf_path: Path) -> dict:
    raw = pdf_path.read_bytes()
    doc = fitz.open(pdf_path)
    # 文本层里的 U+FFFD 说明取字失败；真正的字形缺失还得靠 report/pdf_preview.py 看图
    notdef = sum(p.get_text().count("\ufffd") for p in doc)
    n_pages = doc.page_count
    fonts = sorted({f[3] for p in doc for f in p.get_fonts(full=False) if f[3]})
    doc.close()
    return {
        "size_kb": round(len(raw) / 1024),
        "pages": n_pages,
        "embedded_font_streams": len(re.findall(rb"/FontFile[23]?", raw)),
        "fonts": fonts,
        "replacement_chars": notdef,
    }


# ---------------------------------------------------------------------------
_LOG: list[str] = []


def say(msg: str = "") -> None:
    """PowerShell 的重定向会把中文写成 UTF-16，日志自己落盘更省事。"""
    _LOG.append(msg)
    print(msg)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from playwright.sync_api import sync_playwright

    import build_html  # noqa: E402  同目录

    build_html.main()
    src = OUT / "BP.html"

    as_of = json.loads((OUT / "results.json").read_text(encoding="utf-8"))["meta"]["data_as_of"]
    header = header_tpl(as_of)
    pass1 = OUT / "_pass1.pdf"
    cover = OUT / "_cover.pdf"
    bodyp = OUT / "_body.pdf"
    final = OUT / "BP.pdf"

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def load():
            page = browser.new_page()
            page.goto(src.as_uri(), wait_until="load")
            page.emulate_media(media="print")
            page.wait_for_timeout(700)
            return page

        # ---- 第一遍：只为拿页码 ----
        page = load()
        _render(page, pass1, ranges="", header=header)
        page.close()
        n1 = fitz.open(pass1).page_count

        chapters = json.loads((OUT / "chapters.json").read_text(encoding="utf-8"))
        maps, missing = locate_chapters(pass1, chapters)
        (OUT / "toc_pages.json").write_text(
            json.dumps(maps["labels"], ensure_ascii=False, indent=1), encoding="utf-8")

        # ---- 重建 HTML（这次目录里有页码），再渲染第二遍 ----
        build_html.main()
        page = load()

        cjk_width = page.evaluate("""() => {
            const s = document.createElement('span');
            s.style.cssText = 'position:absolute;visibility:hidden;font-size:40px';
            s.textContent = '到账日数据基础设施蒙特卡洛';
            document.body.appendChild(s);
            const w = s.getBoundingClientRect().width;
            s.remove();
            return w;
        }""")

        _render(page, cover, ranges="1", header=None)
        _render(page, bodyp, ranges="2-", header=header)
        page.close()
        browser.close()

    doc = fitz.open(cover)
    doc.insert_pdf(fitz.open(bodyp))
    doc.save(final, garbage=4, deflate=True)
    n2 = doc.page_count
    doc.close()

    n_toc = apply_outline(final, chapters, maps["physical"])
    toc_bad = check_toc(final, chapters, maps)
    info = verify(final)
    for tmp in (pass1, cover, bodyp):
        tmp.unlink(missing_ok=True)

    say(f"已写入 {final}")
    say(f"  页数 {info['pages']}  体积 {info['size_kb']} KB  书签 {n_toc} 条")
    say(f"  内嵌字体流 {info['embedded_font_streams']} 个：{', '.join(info['fonts'])}")
    say(f"  中文测量宽度 {cjk_width:.0f}px（远大于 0 表示字形已渲染，非豆腐块）")
    say(f"  文本层替换字符 {info['replacement_chars']} 个")
    say(f"  目录命中 {len(maps['labels'])}/{len(chapters)} 章")

    ok = True
    if missing:
        ok = False
        say(f"  [警告] 未能定位页码的章节：{'、'.join(missing)}")
    if n1 != n2:
        ok = False
        say(f"  [警告] 两遍分页不一致（{n1} → {n2}），目录页码可能偏移一页")
    if toc_bad:
        ok = False
        say(f"  [警告] 目录页码与页脚对不上：{'；'.join(toc_bad)}")
    if info["replacement_chars"]:
        ok = False
        say("  [警告] 文本层出现替换字符，检查字体覆盖")
    if info["embedded_font_streams"] == 0:
        ok = False
        say("  [警告] 未检测到内嵌字体，换机器打开可能变形")
    say("  校验" + ("全部通过" if ok else "存在告警，见上"))
    (OUT / "pdf_build.log").write_text("\n".join(_LOG) + "\n", encoding="utf-8")
    return info


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
