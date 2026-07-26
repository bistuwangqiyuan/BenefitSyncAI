# -*- coding: utf-8 -*-
"""
Kelly 最优比例：在完整结果分布上数值最大化 E[log(1 + f·R)]。

为什么不用 f* = p − q/b：
  该式只在"两点分布"下成立，即失败=全损、成功=单一赔率。本项目的结果是连续分布，
  5% 分位仍能收回 49% 的现金，90% 分位是 43×。用两点近似会同时高估亏损深度与
  压缩盈利结构，得到的比例不可用。原计划书正是用了这个式子。

两个口径分别求解，因为它们回答的是两个不同的问题：
  现金口径   —— "我该把多少可投资资产押在这个项目的现金支出上"
  全成本口径 —— "把 5,200 小时按机会成本计价后，这仍是一笔正期望的下注吗"
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

from inputs import A, enable_utf8_stdout
from monte_carlo import simulate


def kelly_fraction(returns: np.ndarray) -> dict:
    """
    数值求解 argmax_f E[log(1 + f·R)]，f ∈ [0, f_max)。
    f_max 由最差结果决定：f 不能大到让某条路径的财富归零或为负。
    """
    r = np.asarray(returns, dtype=float)
    worst = float(r.min())
    if worst >= 0:
        return {"f_star": 1.0, "growth_at_f_star": float(np.log1p(r).mean()),
                "note": "所有路径均非负，Kelly 无内点解，上限即最优", "f_max": 1.0}

    f_max = -1.0 / worst          # 使最差路径恰好归零的比例
    hi = f_max * (1 - 1e-9)

    def neg_growth(f: float) -> float:
        w = 1.0 + f * r
        if np.any(w <= 0):
            return 1e9
        return -float(np.log(w).mean())

    res = minimize_scalar(neg_growth, bounds=(0.0, hi), method="bounded",
                          options={"xatol": 1e-10})
    f_star = float(res.x)
    # 期望为负时最优解就是 0，数值解可能落在极小的正数上，做一次显式检查
    if -neg_growth(f_star) <= neg_growth(0.0) * -1.0 + 1e-12 and float(r.mean()) <= 0:
        f_star = 0.0
    return {
        "f_star": f_star,
        "growth_at_f_star": -neg_growth(f_star),
        "f_max": f_max,
        "note": "",
    }


def naive_kelly(returns: np.ndarray) -> dict:
    """两点近似 f* = p − q/b，仅用于展示它与完整分布解的差距。"""
    r = np.asarray(returns, dtype=float)
    wins = r > 0
    p = float(wins.mean())
    q = 1.0 - p
    avg_win = float(r[wins].mean()) if wins.any() else 0.0
    avg_loss = float(-r[~wins].mean()) if (~wins).any() else 1.0
    b = avg_win / avg_loss if avg_loss > 0 else float("inf")
    f = p - q / b if b not in (0, float("inf")) else p
    return {"p": round(p, 4), "b": round(b, 3), "f_naive": round(f, 4)}


def growth_curve(returns: np.ndarray, n: int = 120) -> list[dict]:
    """E[log(1+fR)] 随 f 的变化，供绘图。"""
    r = np.asarray(returns, dtype=float)
    worst = float(r.min())
    hi = (-1.0 / worst) * 0.999 if worst < 0 else 1.0
    hi = min(hi, 1.0)
    out = []
    for f in np.linspace(0.0, hi, n):
        w = 1.0 + f * r
        g = float(np.log(w).mean()) if np.all(w > 0) else float("nan")
        out.append({"f": round(float(f), 5), "growth": round(g, 6)})
    return out


def breakeven_hourly(mc: dict) -> dict:
    """
    求使全成本口径回报恰好为零的时薪：低于它，项目创造价值；高于它，直接去打那份工更划算。

    必须同时给出均值口径与中位口径。均值被右尾主导（99 分位 MOIC 高达 583×），
    对一个不可重复下注的单人创业者而言，中位数才是他大概率会经历的那个世界。
    """
    return {
        "mean": mc["breakeven_hourly_mean"],
        "median": mc["breakeven_hourly_median"],
    }


def run(mc: dict | None = None) -> dict:
    mc = mc or simulate()
    r_cash = mc["_returns"]
    r_full = mc["_returns_full_cost"]

    k_cash = kelly_fraction(r_cash)
    k_full = kelly_fraction(r_full)
    nv = naive_kelly(r_cash)

    cash_budget = float(A("cash_budget"))
    caveat = (
        "Kelly 公式的前提是同一场赌局可以按相同赔率重复无限次下注，且每次下注规模可以"
        "连续调整。单次创业一条都不满足：机会不可重复、投入不可分割（域名与合规支出是"
        "阶梯式的，不存在'投入 37% 的网站'）、结果分布会随自身行动改变。因此下面的比例"
        "只能作为风险资本上限的参照，不能当作出资指令。半 Kelly 是实务上的通行折中，"
        "它牺牲约 25% 的长期增长率换取大幅降低的回撤深度。"
    )

    interpretation = (
        f"两个口径给出方向完全相反的答案，这个反差本身就是本项目最重要的结论。"
        f"现金口径下 Kelly 逼近上限（{k_cash['f_star']:.2f}），因为真正掏出去的钱只有约 "
        f"{mc['invested_cash_mean']:,.0f} 美元，相对于潜在回报小到几乎不构成风险——"
        f"换句话说，'该不该投这笔钱'根本不是需要用 Kelly 来回答的问题。"
        f"全成本口径下最优比例为 {k_full['f_star']:.2f}，因为把 5,200 小时按 "
        f"{mc['founder_hourly_cost']:.0f} 美元/小时计价后，期望回报为负。"
        f"真正的下注标的不是现金，是时间。"
    )

    be = breakeven_hourly(mc)
    return {
        "cash_basis": {
            "f_star": round(k_cash["f_star"], 4),
            "half_kelly": round(k_cash["f_star"] / 2, 4),
            "growth_at_f_star": round(k_cash["growth_at_f_star"], 5),
            "f_star_amount": round(k_cash["f_star"] * cash_budget, 0),
            "half_kelly_amount": round(k_cash["f_star"] / 2 * cash_budget, 0),
        },
        "full_cost_basis": {
            "f_star": round(k_full["f_star"], 4),
            "half_kelly": round(k_full["f_star"] / 2, 4),
            "growth_at_f_star": round(k_full["growth_at_f_star"], 5),
        },
        "naive_two_point": nv,
        "naive_vs_full_gap": round(nv["f_naive"] - k_cash["f_star"], 4),
        "naive_note": (
            "本例中两点近似给出的比例反而更低（0.87 对 1.00），与教科书里"
            "'朴素式偏激进'的常见方向相反。原因是本项目的亏损侧远没有'全损'那么深："
            "5% 分位仍收回近一半现金。两点近似把所有失败都当成全损，于是过度惩罚了下注比例。"
            "无论方向如何，用两点式描述一个连续分布本身就是错的。"
        ),
        "breakeven_hourly": be,
        "assumed_hourly": mc["founder_hourly_cost"],
        "reference_budget": cash_budget,
        "caveat": caveat,
        "interpretation": interpretation,
        "_growth_curve_cash": growth_curve(r_cash),
        "_growth_curve_full": growth_curve(r_full),
    }


if __name__ == "__main__":
    enable_utf8_stdout()
    from pathlib import Path

    mc = simulate()
    k = run(mc)
    lines = []
    lines.append("Kelly 最优比例（完整分布数值解）")
    lines.append(f"  现金口径    f* = {k['cash_basis']['f_star']:.4f}  "
                 f"半 Kelly = {k['cash_basis']['half_kelly']:.4f}  "
                 f"对应金额 ${k['cash_basis']['f_star_amount']:,.0f} / "
                 f"${k['cash_basis']['half_kelly_amount']:,.0f}")
    lines.append(f"  全成本口径  f* = {k['full_cost_basis']['f_star']:.4f}  "
                 f"半 Kelly = {k['full_cost_basis']['half_kelly']:.4f}")
    lines.append(f"  两点近似    f  = {k['naive_two_point']['f_naive']:.4f}  "
                 f"(p={k['naive_two_point']['p']:.3f}, b={k['naive_two_point']['b']:.2f}) "
                 f"—— 与完整分布解相差 {k['naive_vs_full_gap']:+.4f}")
    lines.append("")
    lines.append(f"全成本盈亏平衡时薪: 期望口径 ${k['breakeven_hourly']['mean']:.2f}/小时，"
                 f"中位口径 ${k['breakeven_hourly']['median']:.2f}/小时"
                 f"（当前假设机会成本 ${k['assumed_hourly']:.0f}/小时）")
    lines.append("")
    lines.append("解读: " + k["interpretation"])
    lines.append("")
    lines.append("前提说明: " + k["caveat"])
    text = "\n".join(lines)
    Path("out").mkdir(exist_ok=True)
    Path("out/kelly_console.txt").write_text(text, encoding="utf-8")
    print(text)
