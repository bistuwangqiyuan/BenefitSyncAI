# -*- coding: utf-8 -*-
"""
蒙特卡洛：60 个月、20,000 条路径的现金流模拟，产出胜率、盈亏比、MOIC 分布与年化。

口径声明（与原计划书一致的部分保留，错误的部分纠正）：

- 沿用"现金实现口径"：只有真正拿到手的分配与退出对价计入回报，账面存活不计。
  这一点原计划书是对的，予以保留。
- 纠正之处：本项目是纯自有资金的单人企业，不存在种子轮，故不再用"种子轮收益率"表述，
  改为"自有资金现金回报"。同时增列"含创始人时间机会成本"的全成本口径——
  5 年 5,200 小时是本项目最大的真实投入，只报现金 ROI 会系统性高估。

风险传导的关键建模决策：AdSense 资格与搜索反垃圾政策是强耦合的（Google 发布商政策
明文禁止在违反搜索反垃圾政策的页面投放广告）。因此一次处罚事件同时归零流量与广告收入，
两者不作为独立风险处理。B 端订阅收入不受该事件影响——这正是双通道方案的对冲价值所在。
"""

from __future__ import annotations

import numpy as np

from inputs import A, S, enable_utf8_stdout
from unit_economics import monthly_costs, one_time_costs, tier_for, rpm_for_tier

MONTHS = int(A("mc_horizon_months"))
PATHS = int(A("mc_paths"))


def _calibrate_lognormal() -> tuple[float, float]:
    """
    用两个分位锚点反解成熟期流量的对数正态参数：
      P(S_max >= 50,000) = 22%   （约对应 1,000 美元/月，取已上线独立项目达到 1k MRR 的经验区间）
      P(S_max >= 300,000) = 5%   （约对应 5,000 美元/月，调研结论为"多数站点永远达不到"）
    """
    from scipy.stats import norm
    x1, p1 = float(A("mature_sessions_p22")), 0.22
    x2, p2 = float(A("mature_sessions_p5")), 0.05
    z1, z2 = norm.ppf(1 - p1), norm.ppf(1 - p2)
    sigma = (np.log(x2) - np.log(x1)) / (z2 - z1)
    mu = np.log(x1) - z1 * sigma
    return float(mu), float(sigma)


def simulate(rng_seed: int | None = None, paths: int | None = None,
             overrides: dict | None = None) -> dict:
    """
    overrides 允许敏感性分析临时替换任意假设值，键为 inputs.ASSUMPTIONS 的 id。
    """
    ov = overrides or {}

    def a(key: str) -> float:
        return float(ov[key]) if key in ov else float(A(key))

    n = paths or PATHS
    rng = np.random.default_rng(rng_seed if rng_seed is not None else int(A("mc_seed")))

    mu, sigma = _calibrate_lognormal()
    if "mature_sessions_p22" in ov or "mature_sessions_p5" in ov:
        from scipy.stats import norm
        x1, x2 = a("mature_sessions_p22"), a("mature_sessions_p5")
        z1, z2 = norm.ppf(0.78), norm.ppf(0.95)
        sigma = (np.log(x2) - np.log(x1)) / (z2 - z1)
        mu = np.log(x1) - z1 * sigma

    # ---- 逐路径抽样 ----
    s_max = rng.lognormal(mu, sigma, n)
    t_mid = np.clip(rng.normal(a("ramp_midpoint_months"), 6.0, n), 6.0, 54.0)
    k = np.clip(rng.normal(a("ramp_steepness"), 1.5, n), 2.0, 10.0)

    def tri(lo: float, mode: float, hi: float) -> np.ndarray:
        """三角分布，并保证 lo <= mode <= hi（敏感性分析可能把 mode 推出原区间）。"""
        lo2, hi2 = min(lo, mode * 0.6), max(hi, mode * 1.6)
        return rng.triangular(lo2, mode, hi2, n)

    rpm_ads = tri(3.0, a("rpm_adsense"), 8.0)
    rpm_jrn = tri(5.0, a("rpm_journey"), 12.0)
    rpm_prm = tri(10.0, a("rpm_premium"), 30.0)
    rpm_dec = np.clip(rng.normal(a("rpm_annual_decay"), 0.04, n), 0.0, 0.30)

    b2b_conv = tri(0.10, a("b2b_conv_per_10k_sessions"), 1.00)
    b2b_arpa = a("b2b_arpa")
    churn = a("b2b_monthly_churn")
    inbound_rate = a("b2b_inbound_per_month")

    exit_mult = tri(11.0, a("exit_multiple_base"), 22.0)

    # 算法事件与处罚的月度风险率
    p_algo_event = 1.0 / a("algo_event_interval")
    shock_mu = np.log(a("algo_shock_median"))
    shock_sd = a("algo_shock_sigma")
    p_penalty_m = 1.0 - (1.0 - a("penalty_hazard_annual")) ** (1.0 / 12.0)

    # ---- 状态 ----
    # 现金口径的两个账户必须严格分开，否则会把"没花完的本金"当成利润分配掉。
    #   invested      = 真正掏出去的自有资金（开办费 + 每月亏损的补足额）
    #   distributions = 每月为正的经营现金流，即真正拿回来的钱
    # 自有资金上限 cash_budget 只作为约束：累计 invested 触顶即无力续投而关停。
    visibility = np.ones(n)
    subs = np.zeros(n)
    ttm_ad = np.zeros((n, 12))
    one_time = sum(one_time_costs().values())
    invested = np.full(n, one_time)
    distributions = np.zeros(n)
    alive = np.ones(n, dtype=bool)

    penalized_at = np.full(n, -1, dtype=np.int16)
    ad_blackout_until = np.full(n, -1, dtype=np.int16)

    sessions_hist = np.zeros((n, MONTHS))
    net_hist = np.zeros((n, MONTHS))
    rev_hist = np.zeros((n, MONTHS))
    b2b_hist = np.zeros((n, MONTHS))

    fixed_pages_total = a("content_pages_total")

    for m in range(MONTHS):
        year_idx = m // 12

        # 算法事件：泊松近似为每月以 1/间隔 的概率发生一次
        hit = rng.random(n) < p_algo_event
        shocks = np.exp(rng.normal(shock_mu, shock_sd, n))
        visibility = np.where(hit, visibility * shocks, visibility)

        # 人工处罚：流量塌到残值，同时 AdSense 资格中断 6 个月（政策强耦合）
        newly = (rng.random(n) < p_penalty_m) & (penalized_at < 0) & alive
        if newly.any():
            visibility[newly] *= a("penalty_traffic_residual")
            penalized_at[newly] = m
            ad_blackout_until[newly] = m + 6

        # 处罚满 12 个月后，少数路径部分恢复
        recov = (penalized_at >= 0) & (penalized_at == m - 12)
        if recov.any():
            lucky = recov & (rng.random(n) < a("penalty_recovery_prob"))
            visibility[lucky] *= 6.0

        ramp = 1.0 / (1.0 + np.exp(-(m - t_mid) / k))
        sessions = np.where(alive, s_max * ramp * visibility, 0.0)

        tier = tier_for(sessions, ttm_ad.sum(axis=1))
        rpm = rpm_for_tier(tier, np.full(n, year_idx),
                           rpm_adsense=rpm_ads, rpm_journey=rpm_jrn,
                           rpm_premium=rpm_prm, decay=rpm_dec)
        ad_rev = sessions / 1000.0 * rpm
        ad_rev = np.where(m <= ad_blackout_until, 0.0, ad_rev)

        # B 端：流量驱动的稳态目标 + 与流量无关的自然到达，二者都受流失侵蚀
        if m >= a("b2b_ramp_start_month"):
            target = sessions / 10_000.0 * b2b_conv
            adds = np.maximum(0.0, target - subs) * 0.20
            inbound = rng.poisson(inbound_rate, n).astype(float)
            subs = subs * (1.0 - churn) + adds + inbound
        subs = np.where(alive, subs, 0.0)
        b2b_rev = subs * b2b_arpa

        revenue = ad_rev + b2b_rev

        pages = min(fixed_pages_total, 30.0 * (m + 1))
        # 成本对 B 端收入的依赖只体现在支付手续费上，直接向量化，避免逐路径调用
        base_cost = monthly_costs(m, pages, 0.0).total
        cost = base_cost + b2b_rev * 0.029 + subs * 0.30

        net = np.where(alive, revenue - cost, 0.0)

        invested += np.where(net < 0, -net, 0.0)
        distributions += np.where(net > 0, net, 0.0)

        # 自有资金触顶即无力续投而关停
        broke = alive & (invested > a("cash_budget"))
        alive = alive & ~broke

        ttm_ad[:, m % 12] = ad_rev
        sessions_hist[:, m] = sessions
        net_hist[:, m] = net
        rev_hist[:, m] = revenue
        b2b_hist[:, m] = b2b_rev

    # ---- 退出 ----
    ttm_net = net_hist[:, -12:].mean(axis=1)
    ttm_rev = rev_hist[:, -12:].sum(axis=1)
    ttm_b2b = b2b_hist[:, -12:].sum(axis=1)
    b2b_share = np.divide(ttm_b2b, ttm_rev, out=np.zeros(n), where=ttm_rev > 0)

    eff_mult = exit_mult * (1.0 + b2b_share * (a("exit_b2b_multiple_premium") - 1.0))
    saleable = alive & (ttm_net >= a("exit_min_profit"))
    sold = saleable & (rng.random(n) < a("p_sale_given_threshold"))
    exit_value = np.where(sold, ttm_net * eff_mult, 0.0)

    realized = distributions + exit_value
    invested = np.maximum(invested, 1.0)

    moic = realized / invested
    r = moic - 1.0

    hours = a("weekly_hours") * 52.0 * (MONTHS / 12.0)
    time_cost = hours * a("founder_hourly_cost")
    moic_full = realized / (invested + time_cost)

    wins = r > 0
    losses = ~wins
    win_rate = float(wins.mean())
    avg_win = float(r[wins].mean()) if wins.any() else 0.0
    avg_loss = float(-r[losses].mean()) if losses.any() else 0.0
    payoff = float(avg_win / avg_loss) if avg_loss > 0 else float("inf")

    # 全成本口径的同一组指标。现金口径的分母只有两千多美元，任何微小收入都能"回本"，
    # 因此现金胜率天然虚高；把 5,200 小时计入分母后才是创始人真正面对的赔率。
    r_full = moic_full - 1.0
    wins_f = r_full > 0
    losses_f = ~wins_f
    avg_win_f = float(r_full[wins_f].mean()) if wins_f.any() else 0.0
    avg_loss_f = float(-r_full[losses_f].mean()) if losses_f.any() else 0.0
    payoff_f = float(avg_win_f / avg_loss_f) if avg_loss_f > 0 else float("inf")

    # 最具决策意义的单一指标：这个项目折合多少钱一小时
    eff_hourly = realized / hours
    surplus = realized - invested
    breakeven_hourly_mean = float(surplus.mean()) / hours
    breakeven_hourly_median = float(np.median(surplus)) / hours

    exp_moic = float(moic.mean())
    annualized = exp_moic ** (1.0 / 5.0) - 1.0
    med_moic = float(np.median(moic))
    med_annualized = med_moic ** (1.0 / 5.0) - 1.0

    # 里程碑
    reach_1k = (net_hist >= 1000.0).any(axis=1)
    reach_5k = (net_hist >= 5000.0).any(axis=1)
    first_1k = np.where(reach_1k, np.argmax(net_hist >= 1000.0, axis=1) + 1, 0)

    # 分年累计（用于 J 曲线）：截至第 y 年末的已实现现金 / 投入现金 − 1
    yearly_roi = []
    for y in range(1, 6):
        upto = y * 12
        seg = net_hist[:, :upto]
        dist_y = np.where(seg > 0, seg, 0.0).sum(axis=1)
        inv_y = one_time + np.where(seg < 0, -seg, 0.0).sum(axis=1)
        realized_y = dist_y + (exit_value if y == 5 else 0.0)
        # 全成本口径：现金投入 + 截至当年的创始人时间成本
        time_y = a("weekly_hours") * 52.0 * y * a("founder_hourly_cost")
        moic_y = float((realized_y / np.maximum(inv_y, 1.0)).mean())
        moic_y_full = float((realized_y / (inv_y + time_y)).mean())
        yearly_roi.append({
            "year": y,
            "roi": round((moic_y - 1.0) * 100, 2),
            "annualized": round((moic_y ** (1.0 / y) - 1.0) * 100, 2),
            "roi_full_cost": round((moic_y_full - 1.0) * 100, 2),
            "annualized_full_cost": round((moic_y_full ** (1.0 / y) - 1.0) * 100, 2),
            "median_net_month": round(float(np.median(net_hist[:, upto - 1])), 0),
        })

    return {
        "paths": n,
        "months": MONTHS,
        "calibration": {"lognormal_mu": round(mu, 4), "lognormal_sigma": round(sigma, 4),
                        "median_mature_sessions": int(round(float(np.exp(mu))))},
        "win_rate_pct": round(win_rate * 100, 2),
        "payoff_ratio": round(payoff, 2),
        "avg_win_r": round(avg_win, 3),
        "avg_loss_r": round(avg_loss, 3),
        "expected_moic": round(exp_moic, 3),
        "median_moic": round(med_moic, 3),
        "annualized_pct": round(annualized * 100, 2),
        "median_annualized_pct": round(med_annualized * 100, 2),
        "expected_moic_full_cost": round(float(moic_full.mean()), 3),
        "median_moic_full_cost": round(float(np.median(moic_full)), 3),
        "annualized_full_cost_pct": round((float(moic_full.mean()) ** 0.2 - 1.0) * 100, 2),
        "win_rate_full_cost_pct": round(float(wins_f.mean()) * 100, 2),
        "payoff_ratio_full_cost": round(payoff_f, 2),
        "founder_hours_5y": int(hours),
        "founder_hourly_cost": a("founder_hourly_cost"),
        "founder_time_cost": round(time_cost, 0),
        "invested_cash_mean": round(float(invested.mean()), 0),
        "one_time_cost": round(one_time, 2),
        "realized_mean": round(float(realized.mean()), 0),
        "realized_median": round(float(np.median(realized)), 0),
        "effective_hourly_mean": round(float(eff_hourly.mean()), 2),
        "effective_hourly_median": round(float(np.median(eff_hourly)), 2),
        "breakeven_hourly_mean": round(breakeven_hourly_mean, 2),
        "breakeven_hourly_median": round(breakeven_hourly_median, 2),
        "p_beat_hourly_cost_pct": round(float((eff_hourly >= a("founder_hourly_cost")).mean()) * 100, 2),
        "p_total_loss_pct": round(float((moic <= 0.001).mean()) * 100, 2),
        "p_reach_1k_pct": round(float(reach_1k.mean()) * 100, 2),
        "p_reach_5k_pct": round(float(reach_5k.mean()) * 100, 2),
        "median_month_to_1k": int(np.median(first_1k[reach_1k])) if reach_1k.any() else 0,
        "p_penalized_pct": round(float((penalized_at >= 0).mean()) * 100, 2),
        "p_sold_pct": round(float(sold.mean()) * 100, 2),
        "p_cash_exhausted_pct": round(float((~alive).mean()) * 100, 2),
        "moic_percentiles": {f"p{q}": round(float(np.percentile(moic, q)), 3)
                             for q in [5, 10, 25, 50, 75, 90, 95, 99]},
        "sessions_p50_final": int(np.median(sessions_hist[:, -1])),
        "sessions_p90_final": int(np.percentile(sessions_hist[:, -1], 90)),
        "net_p50_final": round(float(np.median(net_hist[:, -1])), 0),
        "yearly": yearly_roi,
        "_returns": r,
        "_returns_full_cost": moic_full - 1.0,
        "_moic": moic,
        "_sessions_median_path": np.median(sessions_hist, axis=0).tolist(),
        "_net_median_path": np.median(net_hist, axis=0).tolist(),
        "_net_p75_path": np.percentile(net_hist, 75, axis=0).tolist(),
        "_net_p25_path": np.percentile(net_hist, 25, axis=0).tolist(),
    }


def public(result: dict) -> dict:
    """剥掉下划线开头的大数组，供 JSON 序列化。"""
    return {k: v for k, v in result.items() if not k.startswith("_")}


def _write_console_report(r: dict, path: str = "out/mc_console.txt") -> None:
    from pathlib import Path
    lines = []
    lines.append(f"路径数 {r['paths']:,}  期限 {r['months']} 个月")
    lines.append(f"成熟期月会话中位数校准值: {r['calibration']['median_mature_sessions']:,}")
    lines.append("")
    lines.append("[现金口径]")
    lines.append(f"  胜率 {r['win_rate_pct']:.2f}%   盈亏比 {r['payoff_ratio']:.2f} : 1")
    lines.append(f"  期望 MOIC {r['expected_moic']:.3f}×  中位 {r['median_moic']:.3f}×")
    lines.append(f"  5 年年化 期望 {r['annualized_pct']:.2f}%  中位 {r['median_annualized_pct']:.2f}%")
    lines.append("[全成本口径：现金 + 5,200 小时创始人时间]")
    lines.append(f"  胜率 {r['win_rate_full_cost_pct']:.2f}%   盈亏比 {r['payoff_ratio_full_cost']:.2f} : 1")
    lines.append(f"  期望 MOIC {r['expected_moic_full_cost']:.3f}×  中位 {r['median_moic_full_cost']:.3f}×")
    lines.append(f"  年化 {r['annualized_full_cost_pct']:.2f}%")
    lines.append("[折合时薪 —— 本项目最具决策意义的单一指标]")
    lines.append(f"  期望 ${r['breakeven_hourly_mean']:.2f}/小时   中位 ${r['breakeven_hourly_median']:.2f}/小时")
    lines.append(f"  超过设定机会成本 ${r['founder_hourly_cost']:.0f}/小时 的概率 {r['p_beat_hourly_cost_pct']:.2f}%")
    lines.append("")
    lines.append(f"投入现金均值 ${r['invested_cash_mean']:,.0f}（其中开办 ${r['one_time_cost']:,.2f}）")
    lines.append(f"已实现现金 均值 ${r['realized_mean']:,.0f}  中位 ${r['realized_median']:,.0f}")
    lines.append(f"创始人 5 年工时 {r['founder_hours_5y']:,} 小时，机会成本 ${r['founder_time_cost']:,.0f}")
    lines.append(f"完全损失概率 {r['p_total_loss_pct']:.2f}%  被处罚 {r['p_penalized_pct']:.2f}%  "
                 f"成功售出 {r['p_sold_pct']:.2f}%  资金触顶关停 {r['p_cash_exhausted_pct']:.2f}%")
    lines.append(f"达到 1,000 美元/月 {r['p_reach_1k_pct']:.2f}%（中位第 {r['median_month_to_1k']} 月）  "
                 f"达到 5,000 美元/月 {r['p_reach_5k_pct']:.2f}%")
    lines.append(f"第 60 月会话 中位 {r['sessions_p50_final']:,}  P90 {r['sessions_p90_final']:,}")
    lines.append(f"MOIC 分位: {r['moic_percentiles']}")
    lines.append("")
    lines.append("分年（现金实现口径 / 全成本口径）:")
    for y in r["yearly"]:
        lines.append(f"  第{y['year']}年  ROI {y['roi']:>9.2f}% 年化 {y['annualized']:>8.2f}%  |  "
                     f"全成本 ROI {y['roi_full_cost']:>7.2f}% 年化 {y['annualized_full_cost']:>7.2f}%"
                     f"  |  当月净利中位 ${y['median_net_month']:,.0f}")
    text = "\n".join(lines)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    enable_utf8_stdout()
    r = simulate()
    _write_console_report(r)
