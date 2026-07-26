# -*- coding: utf-8 -*-
"""
敏感性分析：龙卷风图 + 三情景。

目标不是给出更多数字，而是回答一个问题：结论到底靠哪几个假设撑着？
如果结论对某个我方假设极度敏感，那这个假设就必须被标为"投入真金白银之前必须先验证的事"。
"""

from __future__ import annotations

import numpy as np

from inputs import A, A_range, ASSUMPTIONS, enable_utf8_stdout
from monte_carlo import simulate

# 参与龙卷风分析的变量：只选真正可能显著影响结论、且本身存在不确定性的
TORNADO_VARS = [
    "mature_sessions_p22",
    "ramp_midpoint_months",
    "penalty_hazard_annual",
    "algo_shock_median",
    "rpm_premium",
    "rpm_annual_decay",
    "b2b_conv_per_10k_sessions",
    "b2b_inbound_per_month",
    "b2b_arpa",
    "exit_multiple_base",
    "content_pages_total",
    "p_sale_given_threshold",
]

# 刻意不放进龙卷风的变量：founder_hourly_cost。
# 主指标"中位折合时薪"按构造与它无关——它衡量的是项目每小时产出多少钱，
# 而机会成本是拿来跟这个产出做比较的标尺，不是产出本身。
# 把最主观的一个假设移出结论指标，是为了让结论不依赖于对自己时间的估价。
METRIC_INDEPENDENT_OF = ["founder_hourly_cost"]

# 龙卷风图与情景分析用较少路径以控制时间；分位数在 6,000 条路径上已足够稳定
FAST_PATHS = 6000
METRIC = "breakeven_hourly_median"     # 主指标：中位口径下项目折合多少钱一小时
METRIC_LABEL = "中位折合时薪（美元/小时）"


def _metric(overrides: dict, seed: int) -> float:
    r = simulate(rng_seed=seed, paths=FAST_PATHS, overrides=overrides)
    return float(r[METRIC])


def tornado(seed: int = 20260726) -> dict:
    base = _metric({}, seed)
    rows = []
    for key in TORNADO_VARS:
        lo, hi = A_range(key)
        v_lo = _metric({key: lo}, seed)
        v_hi = _metric({key: hi}, seed)
        rows.append({
            "key": key,
            "label": ASSUMPTIONS[key].claim,
            "low_input": lo, "high_input": hi,
            "low_metric": round(v_lo, 2), "high_metric": round(v_hi, 2),
            "swing": round(abs(v_hi - v_lo), 2),
            "direction": "正向" if v_hi >= v_lo else "反向",
        })
    rows.sort(key=lambda x: -x["swing"])
    return {
        "base": round(base, 2), "metric": METRIC, "metric_label": METRIC_LABEL,
        "paths": FAST_PATHS, "rows": rows,
        "note": (
            f"龙卷风分析用 {FAST_PATHS:,} 条路径以控制运行时间，故其基准值 {base:.2f} 与正文"
            f"引用的 20,000 条路径结果存在小数点后的抽样差异，属正常蒙特卡洛误差，"
            f"不影响变量之间的相对排序。"
        ),
    }


# 三情景：不是随手调参，而是把"同向的坏事一起发生"这件事显式建模。
# 现实中算法压力、RPM 下行与处罚风险是相关的（都由同一个平台政策周期驱动），
# 分开做单变量敏感性会系统性低估尾部。
SCENARIOS = {
    "pessimistic": {
        "name": "悲观",
        "story": "搜索侧持续恶化：AI 摘要进一步吞掉点击，小型发布商流量继续下行，"
                 "平台对 AI 辅助内容的判罚趋严，广告单价随之走低。",
        "overrides": {
            "mature_sessions_p22": 30000,
            "ramp_midpoint_months": 32,
            "penalty_hazard_annual": 0.15,
            "algo_shock_median": 0.96,
            "rpm_premium": 12.0,
            "rpm_annual_decay": 0.20,
            "b2b_conv_per_10k_sessions": 0.15,
            "b2b_inbound_per_month": 0.05,
            "exit_multiple_base": 11.0,
        },
    },
    "base": {"name": "基准", "story": "全部取 inputs.py 中的登记值。", "overrides": {}},
    "optimistic": {
        "name": "乐观",
        "story": "工具型页面在 AI 摘要环境下的抗性被验证，州级数据层形成事实标准，"
                 "B 端订阅超预期，退出时按含订阅收入的混合倍数成交。",
        "overrides": {
            "mature_sessions_p22": 70000,
            "ramp_midpoint_months": 18,
            "penalty_hazard_annual": 0.02,
            "algo_shock_median": 1.00,
            "rpm_premium": 26.0,
            "rpm_annual_decay": 0.03,
            "b2b_conv_per_10k_sessions": 0.80,
            "b2b_inbound_per_month": 0.35,
            "exit_multiple_base": 20.0,
        },
    },
}


def scenarios(seed: int = 20260726) -> list[dict]:
    out = []
    for key, cfg in SCENARIOS.items():
        r = simulate(rng_seed=seed, paths=FAST_PATHS, overrides=cfg["overrides"])
        out.append({
            "key": key,
            "name": cfg["name"],
            "story": cfg["story"],
            "win_rate_pct": r["win_rate_pct"],
            "win_rate_full_cost_pct": r["win_rate_full_cost_pct"],
            "expected_moic": r["expected_moic"],
            "median_moic": r["median_moic"],
            "annualized_pct": r["annualized_pct"],
            "expected_moic_full_cost": r["expected_moic_full_cost"],
            "breakeven_hourly_mean": r["breakeven_hourly_mean"],
            "breakeven_hourly_median": r["breakeven_hourly_median"],
            "p_reach_1k_pct": r["p_reach_1k_pct"],
            "p_reach_5k_pct": r["p_reach_5k_pct"],
            "realized_median": r["realized_median"],
            "net_p50_final": r["net_p50_final"],
        })
    return out


def run() -> dict:
    t = tornado()
    sc = scenarios()
    top3 = [r["key"] for r in t["rows"][:3]]
    verdict = (
        "结论对以下三个变量最敏感，它们共同的特点是——都还没有被真实数据验证过："
        + "、".join(ASSUMPTIONS[k].claim for k in top3)
        + "。因此本方案把'先花 8 周用最小成本验证这三件事'放在任何实质性投入之前，"
          "而不是先建站再祈祷。"
    )
    return {"tornado": t, "scenarios": sc, "top3": top3, "verdict": verdict}


if __name__ == "__main__":
    enable_utf8_stdout()
    from pathlib import Path

    r = run()
    lines = [f"龙卷风分析（指标：{r['tornado']['metric_label']}，基准 {r['tornado']['base']:.2f}）", ""]
    lines.append(f"{'变量':<44} {'低值':>10} {'高值':>10} {'摆幅':>8}")
    for row in r["tornado"]["rows"]:
        lines.append(f"{row['label'][:42]:<44} {row['low_metric']:>10.2f} "
                     f"{row['high_metric']:>10.2f} {row['swing']:>8.2f}")
    lines.append("")
    lines.append("三情景:")
    for s in r["scenarios"]:
        lines.append(f"  [{s['name']}] 全成本胜率 {s['win_rate_full_cost_pct']:>6.2f}%  "
                     f"中位 MOIC {s['median_moic']:>7.3f}×  "
                     f"中位时薪 ${s['breakeven_hourly_median']:>7.2f}  "
                     f"期望时薪 ${s['breakeven_hourly_mean']:>7.2f}  "
                     f"达 1k/月 {s['p_reach_1k_pct']:>5.2f}%")
    lines.append("")
    lines.append(r["verdict"])
    text = "\n".join(lines)
    Path("out").mkdir(exist_ok=True)
    Path("out/sensitivity_console.txt").write_text(text, encoding="utf-8")
    print(text)
