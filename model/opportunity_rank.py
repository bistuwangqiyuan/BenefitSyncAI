# -*- coding: utf-8 -*-
"""
机会甄选：对 5 个候选方向按六维加权打分，输出排名与淘汰理由。

与原计划书的区别：原文只给出一个候选、一个 6.55 分，既无对照组也无评分依据。
本模型的每一个分值都必须挂一条来源编号（evidence），并做权重稳健性检验——
如果结论只在某一组特定权重下成立，那它就不是结论，只是偏好。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from inputs import SOURCES, enable_utf8_stdout

# 六个维度及其权重。权重之和为 1，取值理由写在 rationale 里。
CRITERIA: dict[str, dict] = {
    "demand": {
        "name": "需求可验证性",
        "weight": 0.20,
        "rationale": "原方案的致命伤就是把一个 9 天的新闻余波当成永久需求。需求能否被"
                     "独立观测（实测搜索序列、在营竞品规模）必须占最高权重之一。",
    },
    "winnability": {
        "name": "分发可赢性",
        "weight": 0.22,
        "rationale": "在 68% 零点击、第 1 位点击率再降 58% 的搜索环境下，"
                     "'能否真的拿到分发'比'市场有多大'更决定成败，故给最高权重。",
    },
    "compliance": {
        "name": "合规安全度（分越高越安全）",
        "weight": 0.20,
        "rationale": "第 1140 条按每次网页浏览计罚，罚金随流量线性放大而收入随转化率放大，"
                     "两者不同阶。合规不是扣分项而是生死项。",
    },
    "automation": {
        "name": "零人工可行度（20 小时/周约束下）",
        "weight": 0.14,
        "rationale": "唯一不可增加的投入是时间。任何需要持续人工销售或人工客服的模式，"
                     "在单人 20 小时/周下都会失速。",
    },
    "unit_economics": {
        "name": "单位经济与变现结构",
        "weight": 0.14,
        "rationale": "0.99 美元定价被支付固定费吃掉 33% 是结构性错误。"
                     "客单价与变现渠道的结构比毛利率数字本身更重要。",
    },
    "exit": {
        "name": "资产质量与退出倍数",
        "weight": 0.10,
        "rationale": "内容站 1.87× 年净利、含 AI 内容再折 39%，而 B 端订阅型资产为 3.9× 年净利。"
                     "资产形态直接决定 5 年末的兑现能力。",
    },
}


@dataclass
class Candidate:
    code: str
    name: str
    one_liner: str
    scores: dict[str, float]
    evidence: dict[str, list[str]]
    verdict: str = ""
    total: float = 0.0
    rank: int = 0
    detail: dict = field(default_factory=dict)


CANDIDATES: list[Candidate] = [
    Candidate(
        code="C1",
        name="州级到账日与资格自查工具站（消费者端）",
        one_liner="按州维护 EBT/SNAP 发放规则与联邦付款日历，做成免费查询工具，靠展示广告变现。",
        scores={"demand": 9, "winnability": 7, "compliance": 6,
                "automation": 7, "unit_economics": 5, "exit": 4},
        evidence={
            "demand": ["propel_scale", "serp_snap_tx_gov_share", "direct_express_migration"],
            "winnability": ["serp_snap_tx_gov_share", "serp_tool_beats_article",
                            "aio_ctr_drop_pos1", "zero_click_2026"],
            "compliance": ["sec1140_penalty", "free_to_user_pattern", "ftc_impersonation_rule"],
            "automation": ["serp_geo_personalized", "qrg_expert_paraphrase_ok"],
            "unit_economics": ["ezoic_threshold", "raptive_threshold", "mediavine_rpm_yoy"],
            "exit": ["ef_under300k_monthly", "ai_content_discount", "ef_display_share"],
        },
        verdict="需求与可赢性都被实测支持，但单腿站在 Google 上：一次算法事件同时打掉流量与"
                "AdSense 资格，且退出倍数处于经纪商最看空的两个类目的交集。",
    ),
    Candidate(
        code="C2",
        name="结构化福利数据集与 API（B 端）",
        one_liner="把同一份 50 州发放规则做成版本化、带引用的机器可读数据，向金融科技、AI 应用与地方媒体订阅收费。",
        scores={"demand": 5, "winnability": 6, "compliance": 8,
                "automation": 5, "unit_economics": 8, "exit": 8},
        evidence={
            "demand": ["direct_express_migration", "ssa_api_readonly"],
            "winnability": ["ai_chatbot_referral_share", "google_us_share"],
            "compliance": ["sec1140_penalty", "ssa_oig_free_warning"],
            "automation": ["ssa_api_readonly"],
            "unit_economics": ["stripe_fee_on_099", "stripe_fee"],
            "exit": ["acquire_saas_annual", "ef_under300k_monthly"],
        },
        verdict="合规暴露最低、客单价结构最健康、退出倍数最高，但需求缺乏可独立观测的证据，"
                "且 B 端获客高度依赖人工外呼——这正好撞上 20 小时/周的硬约束。单独走不通。",
    ),
    Candidate(
        code="C3",
        name="双通道：免费消费者工具 + 付费数据订阅（共用一套数据层）",
        one_liner="一次维护、两处变现：面向受益人的免费工具负责规模与可信度，面向机构的数据订阅负责利润与估值。",
        scores={"demand": 9, "winnability": 8, "compliance": 7,
                "automation": 6, "unit_economics": 8, "exit": 7},
        evidence={
            "demand": ["propel_scale", "serp_snap_tx_gov_share", "direct_express_migration"],
            "winnability": ["serp_tool_beats_article", "ai_chatbot_referral_share",
                            "chartbeat_small_pub_decline"],
            "compliance": ["free_to_user_pattern", "sec1140_penalty", "qrg_expert_paraphrase_ok"],
            "automation": ["serp_geo_personalized"],
            "unit_economics": ["b2b_arpa_ref", "stripe_fee_on_099"],
            "exit": ["acquire_saas_annual", "ai_content_discount"],
        },
        verdict="边际成本几乎为零的对冲：数据层只维护一次，搜索流量塌陷时 B 端收入仍在，"
                "而消费者站本身就是 B 端最有说服力的销售材料。",
    ),
    Candidate(
        code="C4",
        name="原赛道的合规降级版（免费预填表单，用户自行提交）",
        one_liner="不碰凭证、不收费，只生成用户可自行提交的预填材料与截止日提醒。",
        scores={"demand": 2, "winnability": 1, "compliance": 3,
                "automation": 6, "unit_economics": 2, "exit": 2},
        evidence={
            "demand": ["kw_zero_weeks", "paper_check_recipients", "ssa_no_annual_update"],
            "winnability": ["serp_ss_schedule_gov_share"],
            "compliance": ["sec1140_penalty", "ftc_impersonation_rule", "ssa_oig_free_warning"],
            "automation": ["ssa_1199_scope"],
            "unit_economics": ["paper_check_recipients"],
            "exit": ["ef_under300k_monthly"],
        },
        verdict="即使剥掉所有违法部分，剩下的需求也不存在：目标人群约 28 万且正被官方主动清零，"
                "'ssa direct deposit change' 实测 53 周全为 0，而联邦社保类查询首页 86% 是 ssa.gov。"
                "更糟的是，官方正持续教育这批用户把'非 ssa.gov 的收费/代办网站'一律视为诈骗——"
                "这个信任缺口无法靠执行质量弥补。",
    ),
    Candidate(
        code="C5",
        name="放弃本赛道，另择方向",
        one_liner="完全脱离福利主题，另找非 YMYL 的细分。",
        scores={"demand": 5, "winnability": 5, "compliance": 7,
                "automation": 6, "unit_economics": 5, "exit": 5},
        evidence={
            "demand": ["indie_reach_1k_mrr"],
            "winnability": ["ahrefs_top10_1yr_english", "zero_click_2026"],
            "compliance": ["scaled_content_policy"],
            "automation": ["indie_never_5k"],
            "unit_economics": ["indie_reach_1k_mrr"],
            "exit": ["flippa_content_annual"],
        },
        verdict="脱离 YMYL 确实能降低合规与质量评估风险，但也放弃了本项目唯一被实测证实的"
                "需求缺口与已建立的调研资产，各维度回落到无信息的先验水平。作为对照组保留。",
    ),
]

# C3 的 unit_economics 引用了一条假设而非来源，这里显式登记，避免审计脚本误判。
_ASSUMPTION_EVIDENCE = {"b2b_arpa_ref": "b2b_arpa"}


def score_all(weights: dict[str, float] | None = None) -> list[Candidate]:
    w = weights or {k: v["weight"] for k, v in CRITERIA.items()}
    for c in CANDIDATES:
        c.total = round(sum(c.scores[k] * w[k] for k in CRITERIA), 4)
        c.detail = {k: round(c.scores[k] * w[k], 4) for k in CRITERIA}
    ranked = sorted(CANDIDATES, key=lambda c: -c.total)
    for i, c in enumerate(ranked, 1):
        c.rank = i
    return ranked


def weight_robustness(n: int = 5000, seed: int = 20260726) -> dict:
    """
    权重稳健性：围绕基准权重做 Dirichlet 扰动，看冠军是否会易主。
    浓度参数越小扰动越大；取 alpha = 40 * 基准权重，相当于对权重本身有约 ±30% 的不确定。
    """
    rng = np.random.default_rng(seed)
    keys = list(CRITERIA)
    base = np.array([CRITERIA[k]["weight"] for k in keys])
    draws = rng.dirichlet(base * 40.0, size=n)
    mat = np.array([[c.scores[k] for k in keys] for c in CANDIDATES])  # (cand, crit)
    totals = draws @ mat.T                                            # (n, cand)
    winners = np.argmax(totals, axis=1)
    counts = np.bincount(winners, minlength=len(CANDIDATES))
    return {
        "draws": n,
        "win_share": {CANDIDATES[i].code: round(float(counts[i]) / n * 100, 1)
                      for i in range(len(CANDIDATES))},
        "champion_win_share_pct": round(float(counts.max()) / n * 100, 1),
        "champion": CANDIDATES[int(np.argmax(counts))].code,
    }


def run() -> dict:
    ranked = score_all()
    robust = weight_robustness()
    winner = ranked[0]

    # 校验：每个分值都必须挂上已登记的证据编号
    missing: list[str] = []
    for c in CANDIDATES:
        for k in CRITERIA:
            for e in c.evidence.get(k, []):
                if e not in SOURCES and e not in _ASSUMPTION_EVIDENCE:
                    missing.append(f"{c.code}.{k}:{e}")
    if missing:
        raise ValueError(f"存在未登记的证据编号: {missing}")

    caveat = (
        "稳健性结果需要一条自我批评：C3 是 C1 与 C2 的组合，因此在六个维度中的多数维度上"
        "结构性地不低于其组成部分，夺冠比例接近 100% 有相当一部分来自这种构造上的近似占优，"
        "而非模型发现了什么额外信息。组合方案真正的代价只体现在'零人工可行度'一个维度上"
        "（6 分 vs C1 的 7 分）——也就是创始人时间。因此本方案在后续财务模型中把时间成本"
        "单列为一个口径，并在执行计划中对两条通道做了明确的先后顺序，而不是同时铺开。"
    )
    return {
        "criteria": {k: {"name": v["name"], "weight": v["weight"], "rationale": v["rationale"]}
                     for k, v in CRITERIA.items()},
        "robustness_caveat": caveat,
        "candidates": [
            {
                "code": c.code, "name": c.name, "one_liner": c.one_liner,
                "scores": c.scores, "weighted": c.detail, "total": c.total,
                "rank": c.rank, "verdict": c.verdict,
                "evidence": c.evidence,
            } for c in ranked
        ],
        "winner": {"code": winner.code, "name": winner.name, "total": winner.total},
        "runner_up_gap": round(ranked[0].total - ranked[1].total, 3),
        "robustness": robust,
    }


if __name__ == "__main__":
    enable_utf8_stdout()
    r = run()
    print("机会甄选排名（满分 10）")
    for c in r["candidates"]:
        print(f"  {c['rank']}. {c['code']}  {c['total']:.2f}  {c['name']}")
    print(f"\n冠军: {r['winner']['code']}，领先第二名 {r['runner_up_gap']:.2f} 分")
    rb = r["robustness"]
    print(f"权重稳健性: {rb['draws']} 次 Dirichlet 扰动中，{rb['champion']} 夺冠比例 "
          f"{rb['champion_win_share_pct']}%")
    print(f"  各方案夺冠占比: {rb['win_share']}")
