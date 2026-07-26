# -*- coding: utf-8 -*-
"""
生成 BP 用的 SVG 图表。

两个技术决定：
- svg.fonttype = 'path'：把文字转成矢量路径。这样 PDF 里的中文字形不依赖渲染环境
  是否装了 Noto Sans SC，彻底消除"导出后变方块"的可能。
- 全部数据从 out/results.json 读取，不在本文件里写任何数值。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
HERE = ROOT / "charts"
sys.path.insert(0, str(ROOT / "model"))

# --- 苹果系统语义色 ---
BLUE = "#0071E3"
INK = "#1D1D1F"
GRAY = "#6E6E73"
SEP = "#D2D2D7"
FILL = "#F5F5F7"
GREEN = "#34C759"
RED = "#FF3B30"
ORANGE = "#FF9500"
PURPLE = "#AF52DE"
TEAL = "#5AC8FA"

# 字体选择说明：本机的 Noto Sans SC 是可变字体（NotoSansSC-VF.ttf），matplotlib 不支持
# 可变字重轴，只会按 Thin(100) 载入，9pt 正文在纸上几乎看不见。Microsoft YaHei 提供
# 真实的 400/700 两档字重，故图表统一用它。HTML 正文仍首选 Noto Sans SC——
# Chromium 能正确解析可变字重，两边的取舍条件不同。
plt.rcParams.update({
    "svg.fonttype": "path",
    "font.family": ["Microsoft YaHei", "Noto Sans SC", "DejaVu Sans"],
    "font.size": 10,
    "axes.edgecolor": SEP,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.titlesize": 12.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": SEP,
    "grid.linewidth": 0.6,
    "grid.alpha": 0.55,
    "xtick.color": GRAY,
    "ytick.color": GRAY,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "legend.frameon": False,
    "legend.fontsize": 9,
})


def _clean(ax, left=True, bottom=True, grid_axis="y"):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    ax.grid(axis=grid_axis)
    if grid_axis == "y":
        ax.grid(axis="x", visible=False)
    else:
        ax.grid(axis="y", visible=False)


def _save(fig, name: str):
    HERE.mkdir(parents=True, exist_ok=True)
    path = HERE / name
    fig.savefig(path, format="svg", bbox_inches="tight", transparent=False)
    plt.close(fig)
    print(f"  {name}")
    return path


def _usd(v, _=None):
    return f"${v:,.0f}"


# ---------------------------------------------------------------------------
def chart_trends():
    rows = list(csv.DictReader(open(ROOT / "data" / "trends_measured.csv", encoding="utf-8-sig")))
    wk = sorted([r for r in rows if r["granularity"] == "weekly"], key=lambda r: r["date"])
    x = np.arange(len(wk))
    y = np.array([float(r["value"]) for r in wk])

    fig, ax = plt.subplots(figsize=(9.6, 3.4))
    ax.fill_between(x, 0, y, color=BLUE, alpha=0.14, linewidth=0)
    ax.plot(x, y, color=BLUE, linewidth=1.9, solid_capstyle="round")

    peak = int(np.argmax(y))
    ax.scatter([peak], [y[peak]], s=34, color=BLUE, zorder=5)
    ax.annotate("2026-06-11 峰值\nUSA TODAY 报道当日",
                xy=(peak, y[peak]), xytext=(peak - 13, 74),
                color=INK, fontsize=9,
                arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.9))
    ax.annotate("此后至今持续为 0", xy=(len(x) - 1, 0), xytext=(peak + 3, 26),
                color=GRAY, fontsize=9,
                arrowprops=dict(arrowstyle="->", color=GRAY, linewidth=0.9))

    ticks = list(range(0, len(wk), 8))
    ax.set_xticks(ticks)
    ax.set_xticklabels([wk[i]["date"][:7] for i in ticks])
    ax.set_ylim(0, 108)
    ax.set_ylabel("Google Trends 相对热度")
    ax.set_title("锚点热词的 53 周实测：一次 9 天的新闻余波，不是一个市场", loc="left", pad=12)
    _clean(ax)
    return _save(fig, "trends_zero.svg")


def chart_opportunity(res):
    cands = res["opportunity"]["candidates"]
    crit = res["opportunity"]["criteria"]
    keys = list(crit)
    colors = [BLUE, TEAL, GREEN, ORANGE, PURPLE, GRAY]

    labels = [f"{c['code']}" for c in cands][::-1]
    fig, ax = plt.subplots(figsize=(9.6, 3.6))
    left = np.zeros(len(cands))
    vals = {k: np.array([c["weighted"][k] for c in cands][::-1]) for k in keys}
    for i, k in enumerate(keys):
        ax.barh(labels, vals[k], left=left, color=colors[i % len(colors)],
                height=0.56, label=crit[k]["name"], edgecolor="white", linewidth=0.8)
        left += vals[k]
    for i, c in enumerate(cands[::-1]):
        ax.text(c["total"] + 0.12, i, f"{c['total']:.2f}", va="center",
                fontsize=9.5, color=INK, fontweight="bold")

    ax.set_xlim(0, 9.2)
    ax.set_xlabel("加权总分（满分 10）")
    ax.set_title("五个候选方向的加权评分：分数由六个维度加总而成", loc="left", pad=12)
    ax.legend(loc="lower right", ncol=3, fontsize=8.2)
    _clean(ax, grid_axis="x")
    return _save(fig, "opportunity_rank.svg")


def chart_jcurve(res):
    med = np.array(res["charts"]["net_median_path"])
    p25 = np.array(res["charts"]["net_p25_path"])
    p75 = np.array(res["charts"]["net_p75_path"])
    x = np.arange(1, len(med) + 1)

    fig, ax = plt.subplots(figsize=(9.6, 3.6))
    ax.fill_between(x, p25, p75, color=BLUE, alpha=0.13, linewidth=0,
                    label="25–75 分位区间")
    ax.plot(x, med, color=BLUE, linewidth=2.0, label="中位路径")
    ax.axhline(0, color=GRAY, linewidth=0.9, linestyle=(0, (4, 3)))

    zero_cross = next((i for i, v in enumerate(med) if v > 0), None)
    if zero_cross is not None:
        ax.scatter([x[zero_cross]], [med[zero_cross]], s=30, color=GREEN, zorder=5)
        ax.annotate(f"中位路径第 {x[zero_cross]} 月转正",
                    xy=(x[zero_cross], med[zero_cross]),
                    xytext=(x[zero_cross] + 5, max(p75) * 0.45),
                    color=INK, fontsize=9,
                    arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.9))

    ax.set_xlabel("运营月份")
    ax.set_ylabel("月净利")
    ax.yaxis.set_major_formatter(FuncFormatter(_usd))
    ax.set_xlim(1, len(med))
    ax.set_title("月净利的 J 曲线：中位路径 5 年后仍只是一份微薄的副业收入", loc="left", pad=12)
    ax.legend(loc="upper left")
    _clean(ax)
    return _save(fig, "jcurve.svg")


def chart_moic(res):
    h = res["charts"]["moic_hist"]
    counts = np.array(h["counts"], dtype=float)
    edges = np.array(h["edges"])
    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    share = counts / counts.sum() * 100

    mc = res["monte_carlo"]
    fig, ax = plt.subplots(figsize=(9.6, 3.4))
    cols = [RED if c < 1.0 else BLUE for c in centers]
    ax.bar(centers, share, width=width * 0.92, color=cols, linewidth=0)

    ax.axvline(1.0, color=INK, linewidth=1.0, linestyle=(0, (4, 3)))
    ax.text(1.06, max(share) * 0.92, "回本线 1×", fontsize=9, color=INK)
    ax.axvline(mc["median_moic"], color=GREEN, linewidth=1.4)
    ax.text(mc["median_moic"] + 0.25, max(share) * 0.74,
            f"中位 {mc['median_moic']:.2f}×", fontsize=9, color=GREEN)

    ax.set_xlim(0, h["clip"])
    ax.set_xlabel("现金口径 MOIC（已投入现金的倍数）")
    ax.set_ylabel("路径占比 %")
    ax.set_title(f"MOIC 分布：右尾已在 {h['clip']:.0f}× 处截断，"
                 f"另有 {h['share_above_clip_pct']:.1f}% 的路径落在截断线之外",
                 loc="left", pad=12)
    _clean(ax)
    return _save(fig, "moic_hist.svg")


def chart_kelly(res):
    cash = res["charts"]["kelly_curve_cash"]
    full = res["charts"]["kelly_curve_full"]
    k = res["kelly"]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.3))

    for ax, curve, color, title, fstar in [
        (a1, cash, BLUE, "现金口径", k["cash_basis"]["f_star"]),
        (a2, full, ORANGE, "全成本口径（含 5,200 小时）", k["full_cost_basis"]["f_star"]),
    ]:
        x = np.array([p["f"] for p in curve])
        y = np.array([p["growth"] for p in curve])
        ax.plot(x, y, color=color, linewidth=2.0)
        ax.axhline(0, color=SEP, linewidth=0.9)
        ax.axvline(fstar, color=color, linewidth=1.1, linestyle=(0, (4, 3)))
        ax.text(0.03, 0.06, f"f* = {fstar:.2f}", transform=ax.transAxes,
                fontsize=10, color=color, fontweight="bold")
        ax.set_title(title, loc="left", pad=10, fontsize=11)
        ax.set_xlabel("下注比例 f")
        _clean(ax)
    a1.set_ylabel("E[log(1 + f·R)]")
    fig.suptitle("Kelly 增长率曲线：两个口径给出方向相反的答案", x=0.008, ha="left",
                 fontsize=12.5, color=INK, y=1.04)
    return _save(fig, "kelly_curve.svg")


# 龙卷风图的纵轴空间有限，用短标签；完整表述在正文与 sources.csv 中
TORNADO_SHORT = {
    "b2b_inbound_per_month": "B 端自然获客（不依赖流量）",
    "b2b_arpa": "B 端客单价",
    "algo_shock_median": "单次算法事件的可见度乘数",
    "mature_sessions_p22": "成熟期流量分布锚点",
    "penalty_hazard_annual": "人工处罚年风险率",
    "rpm_annual_decay": "RPM 年衰减率",
    "ramp_midpoint_months": "流量爬坡中点月份",
    "p_sale_given_threshold": "达标后实际成交概率",
    "content_pages_total": "维护的页面总量",
    "b2b_conv_per_10k_sessions": "每万会话的 B 端转化",
    "rpm_premium": "高级广告联盟 RPM",
    "exit_multiple_base": "退出倍数",
}


def chart_tornado(res):
    rows = res["sensitivity"]["tornado"]["rows"][:10][::-1]
    base = res["sensitivity"]["tornado"]["base"]
    labels = [TORNADO_SHORT.get(r["key"], r["label"][:20]) for r in rows]
    lows = np.array([r["low_metric"] for r in rows]) - base
    highs = np.array([r["high_metric"] for r in rows]) - base

    fig, ax = plt.subplots(figsize=(9.6, 4.2))
    y = np.arange(len(rows))
    ax.barh(y, lows, color=RED, alpha=0.80, height=0.6, label="取假设下界")
    ax.barh(y, highs, color=BLUE, alpha=0.85, height=0.6, label="取假设上界")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.6)
    ax.axvline(0, color=INK, linewidth=1.0)
    ax.set_xlabel(f"相对基准（${base:.2f}/小时）的变动")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.1f}"))
    ax.set_title("龙卷风图：中位折合时薪对各假设的敏感度", loc="left", pad=12)
    ax.legend(loc="lower right")
    _clean(ax, grid_axis="x")
    return _save(fig, "tornado.svg")


def chart_ladder(res):
    ladder = res["unit_economics"]["ladder"]
    sess = [r["sessions"] for r in ladder]
    ad = [r["ad_revenue"] for r in ladder]
    b2b = [r["b2b_revenue"] for r in ladder]
    cost = [r["cost"] for r in ladder]
    x = np.arange(len(sess))

    fig, ax = plt.subplots(figsize=(9.6, 3.5))
    ax.bar(x - 0.19, ad, width=0.36, color=BLUE, label="广告收入", linewidth=0)
    ax.bar(x - 0.19, b2b, width=0.36, bottom=ad, color=TEAL, label="B 端订阅", linewidth=0)
    ax.bar(x + 0.19, cost, width=0.36, color=SEP, label="总成本", linewidth=0)

    be = res["unit_economics"]["breakeven_sessions"]
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s:,}" for s in sess], fontsize=8.6)
    ax.set_xlabel(f"月会话数（盈亏平衡点约 {be:,.0f}）")
    ax.set_ylabel("美元/月")
    ax.set_yscale("symlog", linthresh=100)
    ax.yaxis.set_major_formatter(FuncFormatter(_usd))
    ax.set_title("变现阶梯：收入的台阶来自广告网络的准入门槛，而非流量的线性增长",
                 loc="left", pad=12)
    ax.legend(loc="upper left")
    _clean(ax)
    return _save(fig, "monetization_ladder.svg")


def chart_scenarios(res):
    sc = res["sensitivity"]["scenarios"]
    names = [s["name"] for s in sc]
    med = [s["breakeven_hourly_median"] for s in sc]
    mean = [s["breakeven_hourly_mean"] for s in sc]
    x = np.arange(len(sc))

    fig, ax = plt.subplots(figsize=(9.6, 3.2))
    ax.bar(x - 0.19, med, width=0.36, color=BLUE, label="中位路径", linewidth=0)
    ax.bar(x + 0.19, mean, width=0.36, color=TEAL, label="期望（被右尾拉高）", linewidth=0)

    hourly = res["kelly"]["assumed_hourly"]
    ax.axhline(hourly, color=RED, linewidth=1.2, linestyle=(0, (4, 3)))
    ax.text(len(sc) - 0.55, hourly + 0.8, f"设定机会成本 ${hourly:.0f}/小时",
            fontsize=9, color=RED, ha="right")

    for i, (m, a) in enumerate(zip(med, mean)):
        ax.text(i - 0.19, m + 0.5, f"${m:.2f}", ha="center", fontsize=9, color=INK)
        ax.text(i + 0.19, a + 0.5, f"${a:.2f}", ha="center", fontsize=9, color=INK)

    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("折合时薪")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("三情景下的折合时薪：只有乐观情景的期望值才超过设定的机会成本",
                 loc="left", pad=12)
    ax.legend(loc="upper left")
    _clean(ax)
    return _save(fig, "scenarios.svg")


def main():
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    print("生成图表:")
    chart_trends()
    chart_opportunity(res)
    chart_ladder(res)
    chart_jcurve(res)
    chart_moic(res)
    chart_kelly(res)
    chart_tornado(res)
    chart_scenarios(res)
    print("完成")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()
