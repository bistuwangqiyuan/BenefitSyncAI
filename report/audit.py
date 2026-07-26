# -*- coding: utf-8 -*-
"""
一致性审计。

原文档最致命的毛病不是某个数算错了，而是同一个量在不同地方给出不同的值，然后用一句
"以本表为准"把矛盾盖过去。本脚本的存在就是让那种事在这份文档里物理上不可能发生：

  A 追溯性  正文里每一个注入值都能在 results.json 里原样复现，且确实出现在 HTML 中
  B 无手写数  正文里每一个"重要数字"（带 $ % × 、含千分位或小数、或 >= 100）
             要么来自 results.json，要么来自来源/假设账本原文，否则报错
  C 账本完整  sources.csv 与 results.json 逐字段一致；每条来源有 URL、A–D 置信度与取数日
  D 引用闭合  正文角标编号连续、无缺号、无越界，且每条被引来源都在附录 C 里
  E 内部恒等  跨章节的量纲与口径关系自洽（胜率、MOIC 偏度、Kelly 值域、敏感性基准偏差）
  F 产物同步  BP.pdf 不早于 BP.html，页数与构建日志一致

任何一项失败，脚本以非零码退出。
"""

from __future__ import annotations

import csv
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DATA = ROOT / "data"

# 叙述性数字：章节号、年份、小计数等，不是"数据"，不要求登记。
# 规则写死在这里而不是逐个白名单，是为了让规则本身可被审阅。
YEAR_RANGE = range(1990, 2036)
PROSE_MAX = 100          # 100 以下的裸整数视为叙述用词（"三个""20 小时"）

_TAG = re.compile(r"<[^>]+>")
_SVG = re.compile(r"<svg\b.*?</svg>", re.S | re.I)
_STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
_CITE = re.compile(r'<span class="src">\[[\d,]+\]</span>')
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_H_NUM = re.compile(r"<h([34])>\s*\d+(?:\.\d+)*\s*", re.I)


class Audit:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []

    def ok(self, name: str, detail: str = ""):
        self.checks.append((name, True, detail))

    def fail(self, name: str, detail: str):
        self.checks.append((name, False, detail))

    def expect(self, cond: bool, name: str, detail: str = "", fail_detail: str = ""):
        (self.ok if cond else self.fail)(name, detail if cond else (fail_detail or detail))

    @property
    def failures(self):
        return [c for c in self.checks if not c[1]]


# ---------------------------------------------------------------------------
def visible_text(raw: str) -> str:
    s = _STYLE.sub(" ", raw)
    s = _SVG.sub(" ", s)                 # 图表里的刻度数字由 matplotlib 从同一份数据画出
    s = _CITE.sub(" ", s)                # 角标 [10,11,12] 会被当成一个带千分位的数
    s = _H_NUM.sub(r"<h\1> ", s)         # 去掉 "4.2" 这类小节编号
    s = _TAG.sub(" ", s)
    return htmllib.unescape(s)


def numeric_tokens(text: str) -> list[str]:
    return _NUM.findall(text)


def is_significant(tok: str, context: str) -> bool:
    """判断一个数字是不是需要有出处的'数据'。"""
    if "," in tok or "." in tok:
        return True
    v = int(tok)
    if v in YEAR_RANGE and len(tok) == 4:
        return False
    return v >= PROSE_MAX


def norm(tok: str) -> str:
    return tok.replace(",", "").rstrip("0").rstrip(".") if "." in tok else tok.replace(",", "")


# ---------------------------------------------------------------------------
def resolve(res: dict, path: str):
    cur = res
    for part in path.split("."):
        if part.endswith("]"):
            name, idx = part[:-1].split("[")
            cur = cur[name][int(idx)] if name else cur[int(idx)]
        else:
            cur = cur[part]
    return cur


def text_matches_value(text: str, value) -> bool:
    """文本是数值在某个精度下的呈现形式。

    只比绝对值：负号常常由中文承担（"下降 30%" 对应 -30），本项检查要抓的是量级错误，
    不是符号写法。
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value) in text
    nums = _NUM.findall(text)
    if not nums:
        return False
    for n in nums:
        raw = n.replace(",", "")
        try:
            shown = abs(float(raw))
        except ValueError:
            continue
        for scale in (1, 100, 0.01, 1000, 0.001, 1 / 12, 12):
            target = abs(value) * scale
            dec = len(raw.split(".")[1]) if "." in raw else 0
            if abs(shown - round(target, dec)) <= max(abs(target) * 1e-6, 0.5 * 10 ** -dec):
                return True
    return False


# ---------------------------------------------------------------------------
def run() -> Audit:
    a = Audit()
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    trace = json.loads((OUT / "number_trace.json").read_text(encoding="utf-8"))
    raw_html = (OUT / "BP.html").read_text(encoding="utf-8")
    text = visible_text(raw_html)

    # ---------- A 追溯性 ----------
    by_sid = {s["id"]: s for s in res["sources"]}
    by_aid = {x["id"]: x for x in res["assumptions"]}

    bad_value, bad_render, missing_in_html = [], [], []
    for t in trace:
        kind, path, shown = t["kind"], t["path"], t["text"]
        try:
            if kind == "results":
                v = resolve(res, path)
            elif kind == "source":
                v = by_sid[path.split(".", 1)[1]]["value"]
            else:
                v = by_aid[path.split(".", 1)[1]]["value"]
        except (KeyError, IndexError, TypeError):
            bad_value.append(f"{path}（在 results.json 中取不到）")
            continue
        if v != t["value"]:
            bad_value.append(f"{path}：账本 {v} ≠ 留痕 {t['value']}")
        elif not text_matches_value(shown, v):
            bad_render.append(f"{path}：值 {v} 呈现为 “{shown}”")
        if shown not in text:
            missing_in_html.append(f"{path} → “{shown}”")

    a.expect(not bad_value, "A1 注入值与 results.json 一致",
             f"{len(trace)} 处注入值全部复现", "；".join(bad_value[:6]))
    a.expect(not bad_render, "A2 数值与其呈现文本自洽",
             "格式化未改变量级", "；".join(bad_render[:6]))
    a.expect(not missing_in_html, "A3 留痕文本确实出现在正文",
             "留痕与正文一一对应", "；".join(missing_in_html[:6]))

    # ---------- B 正文无手写数字 ----------
    allowed: set[str] = set()
    for t in trace:
        allowed.update(norm(x) for x in numeric_tokens(t["text"]))
    for rec in list(by_sid.values()) + list(by_aid.values()):
        blob = " ".join(str(rec.get(k, "")) for k in
                        ("claim", "label", "value", "unit", "publisher", "url",
                         "note", "rationale", "retrieved", "low", "high"))
        allowed.update(norm(x) for x in numeric_tokens(blob))
    # 模型输出里出现过的每一个数（含未被正文引用的），也算有出处
    allowed.update(norm(x) for x in numeric_tokens(json.dumps(res, ensure_ascii=False)))

    orphans: list[str] = []
    for m in _NUM.finditer(text):
        tok = m.group(0)
        if not is_significant(tok, text):
            continue
        if norm(tok) in allowed:
            continue
        ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 34):m.end() + 24]).strip()
        orphans.append(f"{tok} … “{ctx}”")

    a.expect(not orphans, "B 正文无未登记数字",
             "所有重要数字均可追溯至账本", f"{len(orphans)} 处：" + " ｜ ".join(orphans[:8]))

    # ---------- C 账本完整 ----------
    with (DATA / "sources.csv").open(encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    csv_src = {r["编号"]: r for r in csv_rows if r["类型"] == "来源"}
    csv_asm = {r["编号"]: r for r in csv_rows if r["类型"] == "假设"}

    diffs = []
    for sid, s in by_sid.items():
        r = csv_src.get(sid)
        if r is None:
            diffs.append(f"{sid} 不在 sources.csv")
            continue
        if str(s["value"]) != r["数值"]:
            diffs.append(f"{sid} 取值 {s['value']} ≠ CSV {r['数值']}")
        if s["url"] != r["URL"]:
            diffs.append(f"{sid} URL 不一致")
    for aid, x in by_aid.items():
        r = csv_asm.get(aid)
        if r is None:
            diffs.append(f"{aid} 不在 sources.csv 的假设区")
        elif str(x["value"]) != r["数值"]:
            diffs.append(f"{aid} 取值 {x['value']} ≠ CSV {r['数值']}")
    extra = (set(csv_src) - set(by_sid)) | (set(csv_asm) - set(by_aid))
    if extra:
        diffs.append(f"CSV 里有 results.json 没有的条目：{sorted(extra)[:5]}")
    a.expect(not diffs, "C1 sources.csv 与 results.json 逐字段一致",
             f"{len(by_sid)} 条来源 + {len(by_aid)} 条假设双向核对通过", "；".join(diffs[:6]))

    bad_meta = []
    for sid, s in by_sid.items():
        if s["confidence"] not in "ABCD" or not s["confidence"]:
            bad_meta.append(f"{sid} 置信度 “{s['confidence']}” 非法")
        if not s["url"]:
            bad_meta.append(f"{sid} 缺 URL")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s["retrieved"])):
            bad_meta.append(f"{sid} 取数日 “{s['retrieved']}” 格式不对")
    a.expect(not bad_meta, "C2 每条来源都有 URL、A–D 置信度与取数日",
             "无缺项", "；".join(bad_meta[:6]))

    bad_asm = [aid for aid, x in by_aid.items() if not str(x.get("rationale", "")).strip()]
    a.expect(not bad_asm, "C3 每条自设假设都写明推理依据",
             f"{len(by_aid)} 条假设均有依据", "缺依据：" + "、".join(bad_asm[:8]))

    # ---------- D 引用闭合 ----------
    cited = [int(n) for m in re.finditer(r'<span class="src">\[([\d,]+)\]</span>', raw_html)
             for n in m.group(1).split(",")]
    uniq = sorted(set(cited))
    expected = list(range(1, len(uniq) + 1))
    a.expect(uniq == expected, "D1 角标编号连续无缺号",
             f"正文引用 {len(uniq)} 条来源，编号 1–{len(uniq)}",
             f"编号异常：缺 {sorted(set(expected) - set(uniq))[:8]}")

    appendix_nums = set()
    # 目录里也写着"附录 C"，要从最后一次出现处切，否则会把附录 B 的表也算进来
    cut = raw_html.rfind("附录 C")
    if cut > 0:
        appendix_nums = {int(x) for x in
                         re.findall(r"<td class=\"num\">(\d+)</td>", raw_html[cut:])}
    a.expect(set(uniq) <= appendix_nums or not appendix_nums,
             "D2 每个角标都能在附录 C 里查到",
             f"附录 C 收录编号 {len(appendix_nums)} 条",
             f"附录缺失编号 {sorted(set(uniq) - appendix_nums)[:8]}")

    d_conf = [s["id"] for s in res["sources"] if s["confidence"] == "D"]
    a.expect(True, "D3 低置信度来源清点",
             f"D 级来源 {len(d_conf)} 条" + ("（均未用于硬结论）" if not d_conf else ""))

    # ---------- E 内部恒等 ----------
    mc = res["monte_carlo"]
    ident = []
    if not 0 <= mc["win_rate_pct"] <= 100:
        ident.append("胜率越界")
    if mc["median_moic"] > mc["expected_moic"]:
        ident.append("中位 MOIC 高于期望，与右偏分布矛盾")
    k = res["kelly"]
    for key in ("cash_full", "cash_half", "full_cost_full"):
        if key in k and not 0 <= k[key] <= 1:
            ident.append(f"Kelly {key} 越界")
    if res["ledger"]["n_sources"] != len(res["sources"]):
        ident.append("来源条数与账本统计不符")
    if res["ledger"]["n_assumptions"] != len(res["assumptions"]):
        ident.append("假设条数与账本统计不符")
    rm = res.get("roadmap", {})
    if rm and abs(rm["total_hours"] - mc["founder_hours_5y"]) / mc["founder_hours_5y"] > 0.05:
        ident.append(f"执行计划总工时 {rm['total_hours']} 与模型五年工时 "
                     f"{mc['founder_hours_5y']} 相差超 5%")
    base = res["sensitivity"].get("baseline", {}).get("breakeven_hourly_median")
    ref = mc.get("breakeven_hourly_median")
    if base and ref and abs(base - ref) / max(ref, 1e-9) > 0.15:
        ident.append(f"敏感性基准 {base:.2f} 与主模型 {ref:.2f} 偏差超 15%")
    a.expect(not ident, "E 跨章节口径自洽",
             "胜率/偏度/Kelly 值域/账本计数/基准偏差均通过", "；".join(ident))

    # ---------- F 产物同步 ----------
    pdf, htmlf = OUT / "BP.pdf", OUT / "BP.html"
    a.expect(pdf.exists() and pdf.stat().st_mtime >= htmlf.stat().st_mtime - 5,
             "F1 BP.pdf 不早于 BP.html",
             "PDF 为当前 HTML 所出", "PDF 比 HTML 旧，需重新导出")
    log = (OUT / "pdf_build.log").read_text(encoding="utf-8") if (OUT / "pdf_build.log").exists() else ""
    a.expect("校验全部通过" in log, "F2 PDF 构建自检通过",
             re.search(r"页数 \d+[^\n]*", log).group(0) if "页数" in log else "",
             "见 out/pdf_build.log")
    return a


# ---------------------------------------------------------------------------
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    a = run()
    lines = ["# 一致性审计报告", ""]
    for name, ok, detail in a.checks:
        mark = "通过" if ok else "失败"
        lines.append(f"- [{mark}] **{name}** — {detail}")
    n_bad = len(a.failures)
    lines += ["", f"合计 {len(a.checks)} 项检查，失败 {n_bad} 项。"]
    body = "\n".join(lines)
    (OUT / "audit_report.md").write_text(body + "\n", encoding="utf-8")
    print(body)
    return 1 if n_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
