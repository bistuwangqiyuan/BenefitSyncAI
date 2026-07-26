# -*- coding: utf-8 -*-
"""
汇总入口：跑完全部模型，产出 out/results.json。

report/build_html.py 只允许从这个文件取数。正文里不得出现任何手写数字——
原计划书"以本表为准"那句话之所以要写，就是因为叙述和表格已经对不上了。
唯一的防御办法是让它们物理上出自同一个来源。
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

import kelly as kelly_mod
import opportunity_rank
import sensitivity as sens_mod
import unit_economics
from inputs import (ASSUMPTIONS, OUT, RETRIEVED, SOURCES, enable_utf8_stdout,
                    export_ledger, ledger_stats)
from monte_carlo import public, simulate


def _git_rev() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "未提交"


def _trends_summary() -> dict:
    p = Path(__file__).resolve().parent.parent / "data" / "trends_summary.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _roadmap() -> dict:
    """执行阶段的工时由每周可投入工时推出，而不是在正文里手写。

    四个阶段的工时之和应当等于蒙特卡洛里的五年总工时，否则说明执行计划和财务模型
    在讲两件不同的事。
    """
    wh = float(ASSUMPTIONS["weekly_hours"].value)
    weeks_per_month = 52.0 / 12.0
    phases = [
        {"id": "falsify", "when": "第 0–8 周", "months": 8 / weeks_per_month},
        {"id": "buildout", "when": "第 3–9 个月", "months": 7},
        {"id": "b2b", "when": "第 10–24 个月", "months": 15},
        {"id": "harden", "when": "第 25–60 个月", "months": 36},
    ]
    for p in phases:
        p["hours"] = int(round(p["months"] * weeks_per_month * wh))
        p["months"] = round(p["months"], 1)
    total = sum(p["hours"] for p in phases)
    return {
        "phases": phases,
        "weekly_hours": wh,
        "total_hours": total,
        "remaining_after_gate1": total - phases[0]["hours"],
    }


def _debunk() -> dict:
    """证伪章节里用到的派生量，同样不许在正文里手算。"""
    hi = float(SOURCES["orig_ltv_high"].value)
    lo = float(SOURCES["orig_ltv_low"].value)
    return {"orig_ltv_ratio": round(hi / lo, 0)}


def main() -> dict:
    enable_utf8_stdout()
    OUT.mkdir(parents=True, exist_ok=True)

    print("[1/6] 导出来源账本 ...")
    export_ledger()

    print("[2/6] 机会甄选 ...")
    opp = opportunity_rank.run()

    print("[3/6] 单位经济 ...")
    ue = unit_economics.run()

    print("[4/6] 蒙特卡洛 20,000 路径 ...")
    mc_full = simulate()
    mc = public(mc_full)

    print("[5/6] Kelly ...")
    kel = kelly_mod.run(mc_full)
    kel_public = {k: v for k, v in kel.items() if not k.startswith("_")}

    print("[6/6] 敏感性与情景 ...")
    sens = sens_mod.run()

    results = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_as_of": RETRIEVED,
            "git_rev": _git_rev(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "seed": int(ASSUMPTIONS["mc_seed"].value),
        },
        "ledger": ledger_stats(),
        "trends": _trends_summary(),
        "opportunity": opp,
        "unit_economics": ue,
        "monte_carlo": mc,
        "kelly": kel_public,
        "sensitivity": sens,
        "roadmap": _roadmap(),
        "debunk": _debunk(),
        "sources": [
            {"id": s.id, "claim": s.claim, "value": s.value, "unit": s.unit,
             "publisher": s.publisher, "url": s.url, "confidence": s.confidence,
             "retrieved": s.retrieved, "note": s.note}
            for s in SOURCES.values()
        ],
        "assumptions": [
            {"id": a.id, "claim": a.claim, "value": a.value, "unit": a.unit,
             "rationale": a.rationale, "low": a.low, "high": a.high, "note": a.note}
            for a in ASSUMPTIONS.values()
        ],
        "charts": {
            "kelly_curve_cash": kel["_growth_curve_cash"],
            "kelly_curve_full": kel["_growth_curve_full"],
            "sessions_median_path": mc_full["_sessions_median_path"],
            "net_median_path": mc_full["_net_median_path"],
            "net_p25_path": mc_full["_net_p25_path"],
            "net_p75_path": mc_full["_net_p75_path"],
            "moic_hist": _hist(mc_full["_moic"]),
        },
    }

    path = OUT / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {path}（{path.stat().st_size / 1024:.0f} KB）")
    return results


def _hist(moic: np.ndarray, clip: float = 20.0, bins: int = 40) -> dict:
    """MOIC 直方图。右尾极长（99 分位 583×），必须截断才能看清主体分布。"""
    m = np.asarray(moic, dtype=float)
    clipped = np.clip(m, 0, clip)
    counts, edges = np.histogram(clipped, bins=bins, range=(0, clip))
    return {
        "counts": counts.tolist(),
        "edges": [round(float(e), 3) for e in edges],
        "clip": clip,
        "share_above_clip_pct": round(float((m > clip).mean()) * 100, 2),
    }


if __name__ == "__main__":
    main()
