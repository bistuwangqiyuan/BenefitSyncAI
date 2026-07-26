# -*- coding: utf-8 -*-
"""
单位经济：流量 → 收入的漏斗，以及成本栈。

三条与原计划书不同的硬约束：

1. 变现阶梯按 2026 年的真实门槛建模。Ezoic 已于 2026-02-19 把门槛提到 25 万月活，
   对新站实质关闭；"长到 5 万会话再进 Mediavine"的旧路径不复存在。
   真实路径是 AdSense → Journey（1,000 会话，70% 分成）→ Raptive（25,000 PV）
   或 Mediavine Official（5,000 美元年广告收入），二者先到先算。
2. RPM 按会话口径，并按年衰减。政府福利类属低商业意图的信息型流量，
   不享受信用卡/保险类金融内容的溢价。
3. 收入不来自向受益人收费。0.99 美元定价会被支付固定费吃掉 33.2%，
   且第 1140 条把"就免费的政府服务收费"列为按次计罚的行为。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from inputs import A, S, enable_utf8_stdout

# 变现阶梯：(阶段名, 进入门槛的月会话数, 分成后到手的会话 RPM 键)
TIER_ADSENSE = "AdSense"
TIER_JOURNEY = "Journey by Mediavine"
TIER_PREMIUM = "Raptive / Mediavine Official"


def sessions_to_pageviews(sessions: np.ndarray | float) -> np.ndarray | float:
    return sessions * A("pages_per_session")


def tier_for(sessions: np.ndarray, cum_ad_revenue_ttm: np.ndarray) -> np.ndarray:
    """
    返回每条路径当月所处的变现阶段编号：0=AdSense, 1=Journey, 2=Premium。

    进入 Premium 有两条并行路径，先到先算：
      - Raptive：月页面浏览 ≥ 25,000
      - Mediavine Official：过去 12 个月广告收入 ≥ 5,000 美元
    """
    pv = sessions * A("pages_per_session")
    tier = np.zeros_like(sessions, dtype=np.int8)
    tier[sessions >= S("journey_threshold")] = 1
    premium = (pv >= S("raptive_threshold")) | (cum_ad_revenue_ttm >= S("mediavine_official_threshold"))
    tier[premium] = 2
    return tier


def rpm_for_tier(tier: np.ndarray, year_index: np.ndarray,
                 rpm_adsense: float | np.ndarray = None,
                 rpm_journey: float | np.ndarray = None,
                 rpm_premium: float | np.ndarray = None,
                 decay: float = None) -> np.ndarray:
    """按阶段取会话 RPM，并按年衰减。允许外部注入抽样值以支持蒙特卡洛。"""
    ra = A("rpm_adsense") if rpm_adsense is None else rpm_adsense
    rj = A("rpm_journey") if rpm_journey is None else rpm_journey
    rp = A("rpm_premium") if rpm_premium is None else rpm_premium
    d = A("rpm_annual_decay") if decay is None else decay
    base = np.where(tier == 0, ra, np.where(tier == 1, rj, rp))
    return base * np.power(1.0 - d, year_index)


def ad_revenue(sessions: np.ndarray, tier: np.ndarray, year_index: np.ndarray,
               **rpm_kw) -> np.ndarray:
    """会话 RPM 已是分成后的到手口径（行业惯例即按发布商实收报价）。"""
    return sessions / 1000.0 * rpm_for_tier(tier, year_index, **rpm_kw)


@dataclass
class CostStack:
    """月度成本。固定项来自厂商官方定价页，变动项随页面规模与更新频率变化。"""
    infra: float
    tooling: float
    llm: float
    payment: float
    total: float


def monthly_costs(month: int, pages: float, b2b_revenue: float,
                  llm_cost_per_page_cycle: float = None,
                  refresh_per_year: float = None) -> CostStack:
    infra = S("infra_floor")

    # SEO 工具：第 1 个月起就需要，否则无法做关键词与索引监控
    tooling = S("ahrefs_starter") + S("screaming_frog") / 12.0

    # LLM：新页面生成 + 存量页面按频率刷新
    lc = A("llm_cost_per_page_cycle") if llm_cost_per_page_cycle is None else llm_cost_per_page_cycle
    rf = A("page_refresh_per_year") if refresh_per_year is None else refresh_per_year
    llm = pages * rf / 12.0 * lc

    # 支付手续费：只对 B 端订阅收取（消费者端不收费，故广告收入无此项）
    payment = b2b_revenue * 0.029 + (b2b_revenue / A("b2b_arpa") if A("b2b_arpa") else 0.0) * 0.30

    total = infra + tooling + llm + payment
    return CostStack(round(infra, 2), round(tooling, 2), round(llm, 2),
                     round(payment, 2), round(total, 2))


def one_time_costs() -> dict[str, float]:
    """开办期一次性支出。"""
    return {
        "域名（首年）": float(S("domain_cost")),
        "合规审查与条款起草": float(A("compliance_legal_reserve")),
        "建司与支付通道（Stripe Atlas，可选）": float(S("stripe_atlas")),
    }


def micropayment_comparison() -> list[dict]:
    """
    展示原方案 0.99 美元定价的结构性错误，并与本方案的 B 端客单价对比。
    这不是数字大小之争，而是固定手续费与客单价的量级关系问题。
    """
    rows = []
    for price, label in [(0.99, "原方案：单次代提交"), (2.99, "原方案：家庭同步"),
                         (float(A("b2b_arpa")), "本方案：B 端数据订阅（月）")]:
        stripe = price * 0.029 + 0.30
        mor = price * 0.05 + 0.50
        rows.append({
            "price": round(price, 2),
            "label": label,
            "stripe_fee": round(stripe, 3),
            "stripe_fee_pct": round(stripe / price * 100, 1),
            "mor_fee_pct": round(mor / price * 100, 1),
            "net": round(price - stripe, 3),
        })
    return rows


def revenue_ladder_table() -> list[dict]:
    """给定几个流量档位，展示所处阶段、RPM 与月收入，供 BP 正文引用。"""
    rows = []
    for sess in [500, 1_000, 5_000, 25_000, 50_000, 150_000, 300_000]:
        s = np.array([float(sess)])
        # 用一个与流量大致相称的 TTM 广告收入来判定 Mediavine 收入门槛
        approx_ttm = float(sess) / 1000.0 * A("rpm_premium") * 12
        t = tier_for(s, np.array([approx_ttm]))
        rpm = rpm_for_tier(t, np.array([0]))
        ad = ad_revenue(s, t, np.array([0]))
        b2b_accounts = sess / 10_000.0 * A("b2b_conv_per_10k_sessions")
        b2b = b2b_accounts * A("b2b_arpa")
        cost = monthly_costs(24, A("content_pages_total"), b2b)
        rows.append({
            "sessions": sess,
            "pageviews": int(round(sess * A("pages_per_session"))),
            "tier": [TIER_ADSENSE, TIER_JOURNEY, TIER_PREMIUM][int(t[0])],
            "rpm": round(float(rpm[0]), 2),
            "ad_revenue": round(float(ad[0]), 0),
            "b2b_accounts": round(b2b_accounts, 1),
            "b2b_revenue": round(b2b, 0),
            "total_revenue": round(float(ad[0]) + b2b, 0),
            "cost": cost.total,
            "net": round(float(ad[0]) + b2b - cost.total, 0),
        })
    return rows


def breakeven_sessions() -> float:
    """求净利转正所需的月会话数（含 B 端贡献）。"""
    lo, hi = 100.0, 500_000.0
    for _ in range(80):
        mid = (lo + hi) / 2
        s = np.array([mid])
        approx_ttm = mid / 1000.0 * A("rpm_premium") * 12
        t = tier_for(s, np.array([approx_ttm]))
        ad = float(ad_revenue(s, t, np.array([0]))[0])
        b2b = mid / 10_000.0 * A("b2b_conv_per_10k_sessions") * A("b2b_arpa")
        net = ad + b2b - monthly_costs(24, A("content_pages_total"), b2b).total
        if net < 0:
            lo = mid
        else:
            hi = mid
    return round(hi, 0)


def run() -> dict:
    ladder = revenue_ladder_table()
    fixed = monthly_costs(24, A("content_pages_total"), 0.0)
    return {
        "thresholds": {
            "journey_sessions": S("journey_threshold"),
            "journey_revshare_pct": S("journey_revshare"),
            "raptive_pageviews": S("raptive_threshold"),
            "raptive_revshare_pct": S("raptive_revshare"),
            "mediavine_annual_revenue": S("mediavine_official_threshold"),
            "ezoic_mau_closed": S("ezoic_threshold"),
        },
        "rpm": {
            "adsense": A("rpm_adsense"),
            "journey": A("rpm_journey"),
            "premium": A("rpm_premium"),
            "annual_decay_pct": round(A("rpm_annual_decay") * 100, 1),
        },
        "ladder": ladder,
        "fixed_monthly_cost": {
            "infra": fixed.infra, "tooling": fixed.tooling,
            "llm": fixed.llm, "total": fixed.total,
        },
        "one_time_costs": one_time_costs(),
        "one_time_total": round(sum(one_time_costs().values()), 2),
        "micropayment": micropayment_comparison(),
        "breakeven_sessions": breakeven_sessions(),
        "pages": A("content_pages_total"),
    }


if __name__ == "__main__":
    enable_utf8_stdout()
    r = run()
    print(f"固定月成本: ${r['fixed_monthly_cost']['total']:.2f}"
          f"（基础设施 {r['fixed_monthly_cost']['infra']:.2f} + 工具 {r['fixed_monthly_cost']['tooling']:.2f}"
          f" + LLM {r['fixed_monthly_cost']['llm']:.2f}）")
    print(f"开办一次性支出: ${r['one_time_total']:.2f}")
    print(f"盈亏平衡月会话数: {r['breakeven_sessions']:,.0f}\n")
    print(f"{'会话/月':>10} {'阶段':<28} {'RPM':>6} {'广告':>8} {'B端':>8} {'成本':>8} {'净利':>9}")
    for row in r["ladder"]:
        print(f"{row['sessions']:>10,} {row['tier']:<28} {row['rpm']:>6.2f} "
              f"{row['ad_revenue']:>8,.0f} {row['b2b_revenue']:>8,.0f} "
              f"{row['cost']:>8,.0f} {row['net']:>9,.0f}")
    print("\n定价结构对比（支付手续费占比）:")
    for m in r["micropayment"]:
        print(f"  ${m['price']:>6.2f}  {m['label']:<26} Stripe {m['stripe_fee_pct']:>5.1f}%"
              f"  第三方 MoR {m['mor_fee_pct']:>5.1f}%")
