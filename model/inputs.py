# -*- coding: utf-8 -*-
"""
来源账本与模型输入的唯一真相源 (single source of truth)。

设计原则（针对原商业计划书暴露的问题）：

1. 任何进入财务模型的数字，必须登记为 Source（有外部出处）或 Assumption（我方假设，
   附推理与合理区间）。二者之外的"裸数字"在 audit.py 中会被判为违规。
2. 每条 Source 带 A–D 置信度。A=一手（厂商定价页/政府统计/法条原文），
   B=二手但多源互证，C=单一来源或来源互相矛盾，D=自选择样本，仅作方向性参考。
3. 已识别为 AI 内容农场的站点（earnifyhub / roipad / adsrpm / arbitragetimes /
   organicarbitrage 等）提供的"分行业 RPM 表""0→5K 案例"一律不予采信，不入账本。
"""

from __future__ import annotations

import csv
import io
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
CHARTS = ROOT / "charts"

RETRIEVED = "2026-07-26"


def enable_utf8_stdout() -> None:
    """Windows 控制台默认 cp936，直接 print 中文/特殊符号会抛异常。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass(frozen=True)
class Source:
    id: str
    claim: str          # 中文论断
    value: Any          # 数值或字符串
    unit: str
    publisher: str
    url: str
    confidence: str     # A / B / C / D
    retrieved: str = RETRIEVED
    note: str = ""


@dataclass(frozen=True)
class Assumption:
    id: str
    claim: str
    value: Any
    unit: str
    rationale: str      # 为什么取这个值
    low: Any = None     # 敏感性下界
    high: Any = None    # 敏感性上界
    note: str = ""


def _s(*args, **kwargs) -> Source:
    return Source(*args, **kwargs)


# ---------------------------------------------------------------------------
# 一、锚点热词实测（本项目自测，可复现）
# ---------------------------------------------------------------------------
_SOURCES: list[Source] = [
    _s("kw_zero_weeks", "锚点热词近 53 周中取值为 0 的周数", 50, "周",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update",
       "A", note="美国区 2025-07-20 至 2026-07-19 周粒度，实时抓取可复现（model/fetch_trends.py）；"
                 "非零周仅 3 个：06-07=100、06-14=4、06-21=1。前置调研口头汇报的'46 周'与其自列的"
                 "非零周清单相矛盾，以本次实抓数据为准"),
    _s("kw_total_weeks", "锚点热词观测总周数", 53, "周",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A"),
    _s("kw_12mo_avg", "锚点热词近 12 个月平均热度（满分 100）", 1.98, "指数",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A"),
    _s("kw_alive_days", "锚点热词从起量到归零的存活天数", 9, "天",
       "本项目 Google Trends 实测（日粒度）", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A",
       note="2026-06-10 起量，06-11 峰值，06-19 起归零"),
    _s("kw_peak_date", "锚点热词峰值日", "2026-06-11", "日期",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A",
       note="与 USA TODAY 报道 SSA 全面电子化同日"),
    _s("kw_zero_since", "锚点热词归零起始日", "2026-06-19", "日期",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A"),
    _s("kw_capture_day_decay", "原计划书采集日（06-12）相对峰值的衰减", 67, "%",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security%20electronic%20benefits%20update", "A",
       note="峰值 100 → 采集日 33"),
    _s("kw_peak_vs_head", "锚点热词历史峰值 vs 头部词 social security 的相对量级", 9, "指数(对方=100)",
       "本项目 Google Trends 实测", "https://trends.google.com/trends/explore?geo=US&q=social%20security", "A"),
    _s("trends_bucket_nature", "Trending Now 的搜索量为短窗口分桶标签而非月均搜索量", "bucketed", "定性",
       "Google Trends 官方说明 / Trending Now",
       "https://support.google.com/trends/answer/4365533", "A",
       note="原计划书把 24 小时分桶标签 200K+ 当作月均量并乘季节系数"),
    _s("usatoday_trigger", "触发热词的新闻源：USA TODAY 报道 SSA 年内完成全面电子化", "2026-06-11", "日期",
       "USA TODAY", "https://www.usatoday.com/story/money/2026/06/11/social-security-benefits-electronic-payment/90506560007/", "A"),
]

# ---------------------------------------------------------------------------
# 二、原方案证伪：法规与事实核验
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("ssa_account_no_proxy", "SSA 规定：任何人不得代他人创建或使用 my Social Security 账户，即使有书面或口头授权",
       "No one can create or use an account on your behalf, even with your written or verbal permission", "条文",
       "美国社会保障署 SSA", "https://www.ssa.gov/myaccount/create.html", "A"),
    _s("logingov_no_automation", "Login.gov 规则：严禁自动化访问（含自动认证、表单提交）",
       "Automated access to Login.gov is strictly prohibited", "条文",
       "Login.gov", "https://www.login.gov/policy/rules-of-use/", "A"),
    _s("ssa_tos_federal_crime", "SSA 服务条款：就个人身份欺骗社会保障署属联邦犯罪",
       "federal crime to deceive the SSA about an individual's identity", "条文",
       "美国社会保障署 SSA", "https://www.ssa.gov/help/di/TOS.html", "A"),
    _s("sec1140_penalty", "《社会保障法》第 1140 条：违规通信罚金，网站按每次浏览单独计罚", 13132, "美元/次浏览",
       "SSA 监察长办公室 OIG", "https://oig.ssa.gov/fraud-reporting/consumer-protection-section-1140/", "A",
       note="each viewing of the website is subject to a separate penalty；广播按每次播出 65,653 美元"),
    _s("sec1140_statute", "第 1140 条法条本身（42 U.S.C. §1320b-10），涵盖任何互联网或电子通信",
       "42 U.S.C. 1320b-10", "法条", "Cornell LII", "https://www.law.cornell.edu/uscode/text/42/1320b-10", "A"),
    _s("sec1140_case_usafiling", "第 1140 条实际和解案例：对社保卡收费网站", 50000, "美元",
       "SSA OIG", "https://oig.ssa.gov/news-releases/2019-09-19-newsroom-news-releases-company-pays-50000-penalty-settle-claim-misleading-consumers-social-security/", "A"),
    _s("sec1140_case_lexisnexis", "第 1140 条实际和解案例：LexisNexis 因产品命名暗示与 SSA 直连", 54000, "美元",
       "SSA OIG", "https://oig.ssa.gov/news-releases/2018-10-23-newsroom-news-releases-oct23-1140-settlement/", "A",
       note="并下架该产品；该公司本身拥有合法 CBSV 权限，仍因'如何描述'被罚"),
    _s("sec1140_case_trak1", "第 1140 条实际和解案例：背景调查公司使用 SSA 徽标", 103950, "美元",
       "SSA OIG", "https://oig.ssa.gov/news-releases/2019-08-27-newsroom-news-releases-background-screening-companies-agree-pay-103950-penalty-settle-claim-they/", "A"),
    _s("ssa_fee_authorization", "42 U.S.C. §406(a)(5)：未经授权收取超额代理费为轻罪",
       "misdemeanor, fine up to $500 or imprisonment up to 1 year", "法条",
       "美国法典", "https://uscode.house.gov/view.xhtml?req=%28title%3A42+section%3A406+edition%3Aprelim%29", "A"),
    _s("ftc_impersonation_rule", "FTC 政府冒充规则（16 CFR Part 461，2024-04-01 生效）民事罚金上限", 53088, "美元/次违规",
       "美国联邦贸易委员会 FTC", "https://www.ecfr.gov/current/title-16/chapter-I/subchapter-D/part-461", "A",
       note="含'by implication'暗示性冒充；首年即关停 13 个网站"),
    _s("ftc_citizens_disability", "FTC/DOJ 诉 Citizens Disability（2025-09-30 和解）：SSDI 外呼营销", 1000000, "美元(实付)",
       "美国联邦贸易委员会 FTC", "https://www.ftc.gov/news-events/news/press-releases/2025/09/citizens-disability-pay-1-million-over-ftc-charges-it-made-tens-millions-illegal-misleading-calls", "A",
       note="判罚 200 万、实付 100 万；1.09 亿次外呼含 2570 万次拨往 DNC 名单"),
    _s("ssa_beneficiaries_total", "SSA 受益人总数（2026 年 6 月）", 75656000, "人",
       "SSA Quick Facts", "https://www.ssa.gov/policy/docs/quickfacts/stat_snapshot/", "A",
       note="原计划书称 5200 万，低估约 2360 万"),
    _s("paper_check_recipients", "仍领纸质支票的受益人（2026 年）", 280000, "人",
       "The Hill / Nexstar", "https://thehill.com/business/personal-finance/5906488-social-security-is-fully-doing-away-with-paper-checks-how-to-prepare/", "B",
       note="占全部受益人不足 1%，且随电子化推进主动归零"),
    _s("eo_14247", "第 14247 号行政令：2025-09-30 起联邦支付停止签发纸质支票", "2025-03-25", "日期",
       "白宫", "https://www.whitehouse.gov/presidential-actions/2025/03/modernizing-payments-to-and-from-americas-bank-account/", "A"),
    _s("ssa_no_annual_update", "SSA 明确：受益人无需为继续领取按期联系 SSA（不存在'年度电子更新'义务）",
       "No. You do not need to contact Social Security to continue your monthly benefits", "条文",
       "SSA", "https://www.ssa.gov/news/en/identity-proofing.html", "A"),
    _s("ssa_eft_mandate_1998", "电子支付强制要求的真实起点（非 2024 年 1 月）", "1998-12", "日期",
       "SSA Handbook §122.2", "https://www.ssa.gov/OP_Home/handbook/handbook.01/handbook-0122.html", "A"),
    _s("ssa_1199_scope", "SSA-1199 系列为境外居住受益人的国际直存表，无 -BK 变体", "International Direct Deposit", "定性",
       "SSA", "https://www.ssa.gov/forms/ssa-1199.html", "A"),
    _s("ssa_api_readonly", "SSA 公开 API 仅 5 个只读 ArcGIS 统计/地址接口，无交易类接口", 5, "个",
       "SSA Open Data", "https://www.ssa.gov/data/OASDIBenefitPaymentsByState.htm", "A",
       note="不存在 /v1/receipt 端点"),
    _s("ecbsv_cost", "eCBSV（唯一的认证类数据交换）最低年费，且仅限 GLBA 金融机构用于授信场景", 5100, "美元/年",
       "SSA", "https://www.ssa.gov/dataexchange/eCBSV/", "A"),
    _s("propel_blocked", "先例：Conduent 单方切断 Propel 对州级 EBT 系统的抓取访问", "约 80% 用户受影响", "定性",
       "纽约时报", "https://www.nytimes.com/2018/04/23/technology/start-up-fight-poverty-food-stamp-giant-blocking-it.html", "A",
       note="Propel 有 8000 万美元融资仍被切断；本方案据此不做任何抓取式代登录"),
    _s("ssa_oig_free_warning", "SSA OIG 公开警告：社保卡相关服务免费，无需使用收费的第三方网站",
       "You ARE NOT required to use one of these services", "条文",
       "SSA OIG", "https://oig.ssa.gov/scam-alerts/2026-03-10-ssa-provides-new-and-replacement-social-security-cards-for-free/", "A"),
]

# ---------------------------------------------------------------------------
# 二之二、原方案的自述数字
#
# 证伪一份文档，引用它自己说过的话也需要出处，否则批评本身就是无据的。
# 这几条的"发布方"就是被证伪的原文档，URL 指向本仓库里的存档，置信度 A：
# 不是因为数字对，而是因为"原文确实这么写"这件事可以逐字复核。
# ---------------------------------------------------------------------------
_ORIG = "原方案文档（本仓库存档）"
_ORIG_URL = "file:googletrendhot.txt"
_SOURCES += [
    _s("orig_claimed_volume", "原方案宣称的锚点热词搜索量（实为 Trending Now 的 24 小时分桶标签）",
       200000, "次", _ORIG, _ORIG_URL, "A",
       note="原文写作 200,000+ 并据此乘季节系数外推为月均量；分桶性质见 trends_bucket_nature"),
    _s("orig_ltv_low", "原方案表格中的 LTV 之一", 1.12, "美元", _ORIG, _ORIG_URL, "A",
       note="与 orig_ltv_high 出自同一份文档，两者相差约 738 倍"),
    _s("orig_ltv_high", "原方案表格中的 LTV 之二", 827, "美元", _ORIG, _ORIG_URL, "A",
       note="原文以此值支撑营收预测，同时又在另一处使用 1.12 美元"),
    _s("orig_payment_cost_share", "原方案假设的支付与云成本合计占收入比", 11, "%",
       _ORIG, _ORIG_URL, "A",
       note="仅 Stripe 对 0.99 美元客单价的固定费就已达 33.2%"),
]

# ---------------------------------------------------------------------------
# 三、搜索生态：可获取流量的真实上限
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("ahrefs_top10_1yr_all", "新发布页面一年内进入前 10 的比例（全样本 100 万 URL）", 1.74, "%",
       "Ahrefs", "https://ahrefs.com/blog/how-long-does-it-take-to-rank-in-google-and-how-old-are-top-ranking-pages/", "A"),
    _s("ahrefs_top10_1yr_english", "同上，过滤为非空英文内容后的比例（200 万 URL）", 6.11, "%",
       "Ahrefs", "https://ahrefs.com/blog/how-long-does-it-take-to-rank-in-google-and-how-old-are-top-ranking-pages/", "A"),
    _s("ahrefs_top10_highvol", "新页面一年内为高搜索量词进入前 10 的比例", 0.3, "%",
       "Ahrefs", "https://ahrefs.com/blog/how-long-does-it-take-to-rank-in-google-and-how-old-are-top-ranking-pages/", "A"),
    _s("ahrefs_winner_within_1mo", "在进入前 10 的少数页面中，首月即达成的占比", 40.82, "%",
       "Ahrefs", "https://ahrefs.com/blog/how-long-does-it-take-to-rank-in-google-and-how-old-are-top-ranking-pages/", "A",
       note="排名突破是双峰分布：早期不破则大概率永不破"),
    _s("ahrefs_top1_age", "排名第 1 的页面平均年龄", 5, "年",
       "Ahrefs", "https://ahrefs.com/blog/how-long-does-it-take-to-rank-in-google-and-how-old-are-top-ranking-pages/", "A"),
    _s("aio_ctr_drop_pos1", "AI Overview 使第 1 位自然点击率下降幅度（2026-12 复测）", 58.0, "%",
       "Ahrefs", "https://ahrefs.com/blog/ai-overviews-reduce-clicks-update/", "A",
       note="2025-03 首测为 34.5%，一年内恶化"),
    _s("aio_prevalence_edu_finance", "教育型金融查询触发 AI Overview 的比例", 91, "%",
       "BrightEdge", "https://www.brightedge.com/resources/weekly-ai-search-insights/google-ymyl-finance-ai-overviews", "B"),
    _s("pew_click_with_aio", "出现 AI 摘要时用户点击自然结果的访问占比", 8, "%",
       "Pew Research Center", "https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/", "A",
       note="n=900 名美国成年人真实浏览行为，68,879 次查询"),
    _s("pew_click_without_aio", "无 AI 摘要时用户点击自然结果的访问占比", 15, "%",
       "Pew Research Center", "https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/", "A"),
    _s("pew_click_inside_aio", "点击 AI 摘要内部引用链接的访问占比", 1, "%",
       "Pew Research Center", "https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/", "A",
       note="被 AI 引用 ≠ 拿到流量；'成为 AI 引用源'不是可行的流量战略"),
    _s("zero_click_2026", "美国 Google 搜索中未产生任何点击的比例（2026 年 1–4 月）", 68.01, "%",
       "SparkToro / Similarweb", "https://sparktoro.com/blog/in-2026-less-than-one-third-of-google-searches-still-send-a-click/", "A",
       note="2024 年为 60.45%"),
    _s("chartbeat_small_pub_decline", "日均 1 万 PV 以下小型出版商 2025 年搜索流量变化", -60, "%",
       "Chartbeat（经 Press Gazette 报道）", "https://pressgazette.co.uk/media-audience-and-business-data/us-publishers-see-traffic-boost-for-breaking-news-from-google-discover/", "A",
       note="10 万 PV 以上为 -22%；越小跌得越狠，新站起步即在最差分档"),
    _s("define_evergreen_decline", "大型出版商常青型内容（指南/解释/测评）自 2024-11 以来的搜索流量变化", -40, "%",
       "Define Media Group（64 家出版商面板，经 Press Gazette 报道）", "https://pressgazette.co.uk/media-audience-and-business-data/us-publishers-see-traffic-boost-for-breaking-news-from-google-discover/", "A"),
    _s("core_updates_28mo", "2024-03 至 2026-06 期间 Google 确认的排名系统更新次数", 16, "次",
       "Google Search Status Dashboard", "https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history", "A",
       note="平均每 7–8 周一次，属不可对冲的经常性风险"),
    _s("march2026_fell_out_top100", "2026-03 核心更新后原前 10 页面跌出前 100 的比例", 24.1, "%",
       "SE Ranking（经 Search Engine Land 报道）", "https://searchengineland.com/march-2026-google-core-update-what-changed-474397", "A"),
    _s("sistrix_winners", "2026-03 核心更新的赢家画像：官方与机构、专业垂直、成熟品牌；输家：聚合站与比价站",
       "official/institutional, specialist, established brands", "定性",
       "Aleyda Solis / Sistrix（经 Search Engine Land 报道）", "https://searchengineland.com/march-2026-google-core-update-what-changed-474397", "B",
       note="Census.gov、BLS.gov 在事实型查询上显著获益"),
    _s("scaled_content_policy", "Google 反垃圾政策：大规模内容滥用与生成方式无关，仅看意图与价值",
       "no matter whether content is produced through automation, human efforts, or some combination", "条文",
       "Google Search Central", "https://developers.google.com/search/blog/2024/03/core-update-spam-policies", "A"),
    _s("spam_policy_covers_ai_answers", "2026-05-15 起 Google 反垃圾政策明确覆盖生成式 AI 回答",
       "or attempting to manipulate generative AI responses in Google Search", "条文",
       "Google（经 Search Engine Land 报道）", "https://searchengineland.com/google-updates-search-spam-policies-to-clarify-it-applies-to-generative-ai-responses-477657", "A",
       note="GEO/AI 引用优化同样在处罚范围内，不存在政策真空区"),
    _s("qrg_ymyl_anonymous_lowest", "质量评估指南：YMYL 页面若完全没有网站或内容创作者信息，应判 Lowest",
       "YMYL pages or websites ... with absolutely no information about the website or content creator should be rated Lowest", "条文",
       "Google 搜索质量评估指南（2025-09-11 版）", "https://static.googleusercontent.com/media/guidelines.raterhub.com/uk//searchqualityevaluatorguidelines.pdf", "A"),
    _s("qrg_suspect_scaled_lowest", "质量评估指南：即便无法确认生成方式，只要强烈怀疑大规模内容滥用即判 Lowest",
       "Even if you are unsure of the method of creation ... you should still use the Lowest rating when you strongly suspect scaled content abuse", "条文",
       "Google 搜索质量评估指南（2025-09-11 版）", "https://static.googleusercontent.com/media/guidelines.raterhub.com/uk//searchqualityevaluatorguidelines.pdf", "A"),
    _s("qrg_expert_paraphrase_ok", "质量评估指南留出的合规窗口：由专家把政府政策改写为易懂语言是有价值的",
       "when an expert paraphrases the contents of a government policy in easy-to-understand language", "条文",
       "Google 搜索质量评估指南（2025-09-11 版）", "https://static.googleusercontent.com/media/guidelines.raterhub.com/uk//searchqualityevaluatorguidelines.pdf", "A",
       note="关键词是 expert：必须有具名且可核验的责任人"),
    _s("adsense_couples_search_spam", "Google 发布商政策：不得在违反搜索反垃圾政策的页面投放广告",
       "must not place Google-served ads on screens that violate the Spam policies for Google web search", "条文",
       "Google Publisher Policies", "https://support.google.com/adsense/answer/10502938", "A",
       note="同一次违规会同时消灭流量与收入，两大风险高度相关"),
    _s("manual_action_base_rate", "2024-03 核心更新中被完全移除索引的广告网络站点占比", 1.9, "%",
       "Originality.ai（约 7.9 万站样本）", "https://originality.ai/can-google-detect-penalize-ai-content", "B",
       note="独立复核为 1.7%（Ian Nuttall，49,345 站）；这是全样本基准率，纯 AI 站条件概率显著更高"),
    _s("deindexed_ai_share", "被移除索引站点中可判定发布过 AI 内容的比例", 86, "%",
       "Originality.ai（175 站、30,614 URL 抽样）", "https://originality.ai/can-google-detect-penalize-ai-content", "B",
       note="151/175；其中 51/175 约 30% 为 95% 以上纯 AI 生成"),
    _s("google_us_share", "Google 在美国搜索市场的份额（2026-06）", 86.67, "%",
       "StatCounter", "https://gs.statcounter.com/search-engine-market-share/all/united-states-of-america/", "A"),
    _s("ai_chatbot_referral_share", "四大 AI 聊天机器人合计带来的搜索引荐流量份额（2026-05）", 0.29, "%",
       "Cloudflare Radar 数据（二手转引）", "https://technologychecker.io/blog/search-engine-market-share", "C",
       note="精确小数不可靠，但'AI 渠道几乎不导流'的方向被 Ahrefs 与 SparkToro 独立佐证"),
]

# ---------------------------------------------------------------------------
# 四、SERP 实测：赛道可赢性的直接证据
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("serp_ss_schedule_gov_share", "查询 social security payment schedule 2026 首页 7 条结果中 ssa.gov 占比", 86, "%",
       "本项目 SERP 实测（美国区，2026-07-26）", "https://www.google.com/search?q=social+security+payment+schedule+2026&gl=us", "A",
       note="6/7 为 ssa.gov，唯一非政府结果是 AARP；独立站无机会"),
    _s("serp_snap_tx_gov_share", "查询 SNAP EBT deposit dates Texas 首页 9 条结果中 .gov 占比", 11, "%",
       "本项目 SERP 实测（美国区，2026-07-26）", "https://www.google.com/search?q=SNAP+EBT+deposit+dates+Texas&gl=us", "A",
       note="1/9；独立站 snapscreener.com 排名第 1 且被 AI Overview 引用，foodstampsneed.com 第 5"),
    _s("serp_tool_beats_article", "在 YMYL 福利类查询中胜出的独立站形态为工具（资格自查/到账日计算），而非文章",
       "calculator/screener outranks .gov", "定性",
       "本项目 SERP 实测（美国区，2026-07-26）", "https://www.google.com/search?q=what+is+the+income+limit+for+medicaid&gl=us", "A",
       note="snapscreener.com 位列 3 个 .gov 域名之上"),
    _s("serp_geo_personalized", "美国福利类查询高度按 IP 地理个性化，全国性内容站需与 50 套州级机构竞争", "state-localized", "定性",
       "本项目 SERP 实测（美国区，2026-07-26）", "https://www.google.com/search?q=how+to+apply+for+snap+benefits&gl=us", "A"),
    _s("propel_scale", "Propel（EBT 余额与到账查询）月活用户规模，验证该需求真实存在", 5000000, "人",
       "Propel", "https://www.propel.app/blog/is-propel-a-scam/", "B",
       note="约每 4 个美国 SNAP 家庭有 1 个在用；对用户免费，靠广告与 interchange"),
    _s("free_to_user_pattern", "该赛道所有已成规模的运营者无一例外对受益人免费",
       "Propel / SNAP Screener / BenefitsUSA / WhenIsMyCheck / FoodStampsNeed", "定性",
       "本项目竞品核验", "https://www.snapscreener.com/about", "A",
       note="变现来自广告、赞助、interchange 或 B2B 转介；无一向受益人收费"),
    _s("direct_express_migration", "Direct Express 发卡行由 Comerica 迁移至 Fifth Third，过渡沟通计划于 2026 年中",
       "~3.4M cardholders", "定性",
       "SSA PolicyNet EM-26005 REV", "https://secure.ssa.gov/apps10/reference.nsf/links/05182026111816AM", "A",
       note="真实、有明确日期、影响约 340 万人的信息缺口"),
    _s("benefitscalculus_nonexistent", "原计划书所列竞品 BenefitsCalculus.com 域名未注册", "NXDOMAIN", "定性",
       "本项目权威 DNS 查询（8.8.8.8）", "https://dns.google/query?name=benefitscalculus.com", "A"),
]

# ---------------------------------------------------------------------------
# 五、变现阶梯与 RPM（2026 年真实门槛）
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("ezoic_threshold", "Ezoic 自 2026-02-19 起的准入门槛（对新站实质关闭）", 250000, "月活用户",
       "Ezoic", "https://osticket.ezoic.com/kb/article/getting-started-ezoics-requirements?lang=en_US", "A",
       note="Incubator 每月全球仅收 20 家且不放宽流量要求；'先长到 5 万会话再进 Mediavine'的旧路径已失效"),
    _s("journey_threshold", "Journey by Mediavine 准入门槛", 1000, "会话/月",
       "Mediavine", "https://help.mediavine.com/what-does-it-take-to-get-approved-by-mediavine", "A"),
    _s("journey_revshare", "Journey by Mediavine 发布商分成", 70, "%",
       "Mediavine", "https://journeymv.zendesk.com/hc/en-us/articles/23783857493787-Revenue-Share", "A"),
    _s("raptive_threshold", "Raptive 准入门槛", 25000, "页面浏览/月",
       "Raptive", "https://raptive.com/blog/opening-the-door-to-more-creators-who-meet-raptive-quality-standards/", "A",
       note="并要求 50% 以上流量来自美加英澳新"),
    _s("raptive_revshare", "Raptive 发布商分成", 75, "%", "Raptive",
       "https://raptive.com/reach-your-full-potential-with-raptive/", "A"),
    _s("mediavine_official_threshold", "Mediavine Official 准入门槛（改为收入门槛，非流量门槛）", 5000, "美元/年广告收入",
       "Mediavine", "https://help.mediavine.com/revenue-share", "A"),
    _s("adsense_revshare", "Google AdSense 展示广告发布商分成", 68, "%",
       "Google AdSense", "https://support.google.com/adsense/answer/9724?hl=en", "A"),
    _s("mediavine_rpm_yoy", "Mediavine 发布商 2025 年末至 2026 年初报告的 RPM 同比变化", -30, "%",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "B",
       note="RPM 应按下行建模，不能按持平"),
    _s("seniors_smartphone", "65 岁以上美国人智能手机拥有率（低于 50 岁以下的 97%）", 78, "%",
       "Pew Research Center NPORS 2025 (n=5,022)", "https://www.pewresearch.org/internet/fact-sheet/mobile/?menuItem=13d95e33-8fb8-45ef-938e-d22b96c7206e", "A",
       note="目标人群桌面占比偏高，对 RPM 略为有利"),
]

# ---------------------------------------------------------------------------
# 六、成本栈（厂商官方定价）
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("domain_cost", "Cloudflare Registrar .com 年费（按成本价）", 10.44, "美元/年",
       "Cloudflare Registrar", "https://www.cloudflare.com/products/registrar/", "C",
       note="按 Verisign 批发价 10.26 + ICANN 0.18 重构；2026-11-01 起批发价升至 10.97"),
    _s("cloudflare_workers_paid", "Cloudflare Workers 付费计划起步价（RAG 需要，Free 档 10ms CPU 不够）", 5.00, "美元/月",
       "Cloudflare", "https://developers.cloudflare.com/workers/platform/pricing/", "A"),
    _s("cloudflare_pages_bandwidth", "Cloudflare Pages 静态带宽与请求计费方式", "unmetered", "定性",
       "Cloudflare", "https://pages.cloudflare.com/", "A",
       note="1 万 / 10 万 / 100 万 PV 三档成本均为 5 美元/月，带宽不计费"),
    _s("infra_floor", "Cloudflare 技术栈固定月成本下限（域名摊销+Pages+D1+R2+Resend+Sentry+BetterStack+Workers）", 5.87, "美元/月",
       "本项目按各厂商官方定价页汇总", "https://developers.cloudflare.com/workers/platform/pricing/", "A"),
    _s("ahrefs_starter", "Ahrefs Starter 档月费（2026-01 新增，Semrush 无对标档位）", 29.00, "美元/月",
       "Ahrefs", "https://ahrefs.com/pricing", "A"),
    _s("screaming_frog", "Screaming Frog SEO Spider 年费", 279.00, "美元/年",
       "Screaming Frog", "https://www.screamingfrog.co.uk/seo-spider/pricing/", "A"),
    _s("llm_1000_articles_cheap", "生成并核验 1000 篇 1500 词内容的 LLM 成本（DeepSeek V4-Flash + 缓存）", 2.38, "美元",
       "本项目按厂商官方费率测算，见 research/cost_model.py", "https://api-docs.deepseek.com/quick_start/pricing", "A",
       note="四段式流水线：提纲/初稿/修订/事实核查，共 1 万输入+5600 输出 token 每篇"),
    _s("llm_1000_articles_frontier", "同上，改用前沿模型（Claude Opus 4.8 + 缓存 + 批处理）", 85.28, "美元",
       "本项目按厂商官方费率测算，见 research/cost_model.py", "https://platform.claude.com/docs/en/about-claude/pricing", "A",
       note="LLM 成本在本量级不构成约束；真正的约束是每周 20 小时的人工核验时间"),
    _s("stripe_fee", "Stripe 美国本土卡费率", "2.9% + $0.30", "费率",
       "Stripe", "https://stripe.com/pricing", "A"),
    _s("stripe_fee_on_099", "0.99 美元定价被 Stripe 手续费吃掉的收入比例", 33.2, "%",
       "本项目按 Stripe 官方费率测算", "https://stripe.com/pricing", "A",
       note="Paddle/Lemon Squeezy 为 55.6%；原计划书假设的合计成本仅 11%"),
    _s("stripe_atlas", "Stripe Atlas 一次性建司费用（含无需 SSN 获取 EIN）", 500, "美元",
       "Stripe Atlas", "https://docs.stripe.com/atlas/signup", "A",
       note="次年起注册代理 100 美元/年"),
    _s("w8ben_default_withholding", "未提交 W-8BEN 时美国来源 FDAP 所得的预扣税率", 30, "%",
       "美国国税局 IRS", "https://www.irs.gov/instructions/iw8ben", "A"),
    _s("services_income_sourcing", "劳务所得按'劳务发生地'定源：完全在美国境外提供的服务为外国来源",
       "IRC 862(a)(3)", "法条", "美国国税局 IRS",
       "https://www.irs.gov/individuals/international-taxpayers/nonresident-aliens-sourcing-of-income", "A",
       note="广告与联盟收入通常按劳务定性；若被定性为特许权使用费则改按'使用地'定源并预扣"),
]

# ---------------------------------------------------------------------------
# 七、退出倍数与基准存活率
# ---------------------------------------------------------------------------
_SOURCES += [
    _s("ef_under300k_monthly", "Empire Flippers 2025 实际成交：30 万美元以下资产倍数", 22.42, "×月净利",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "A",
       note="n=129，占全部成交 77.7%，平均成交价 91,098 美元；折合 1.87× 年净利"),
    _s("ef_avg_2025", "Empire Flippers 2025 全部成交平均倍数（较 2024 年下降 10.1%）", 23.93, "×月净利",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "A"),
    _s("ef_distressed", "Empire Flippers 困境资产挂牌倍数", 13.7, "×月净利",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "A"),
    _s("ef_typical", "Empire Flippers 典型质量档挂牌倍数", 27.8, "×月净利",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "A"),
    _s("ef_display_share", "展示广告类资产在 Empire Flippers 2025 成交中的占比", 13.3, "%",
       "Empire Flippers 2026 State of the Industry Report", "https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf", "A",
       note="报告原话：许多知名联盟 SEO 玩家已完全退出"),
    _s("ai_content_discount", "含 AI 内容的站点相对纯人工内容站点的成交价折让", 39, "%",
       "Originality.AI 分析 Motion Invest 12 个月实际成交数据", "https://originality.ai/blog/ai-website-sales-study", "A",
       note="AI 内容站 1.5× 年营收 vs 人工 2.1×；且多花 19 天（+54%）才售出"),
    _s("flippa_content_annual", "Flippa H1 2026：内容站平均倍数（前四分位 4.68×）", 2.32, "×年净利",
       "Flippa", "https://flippa.com/blog/digital-ma-insights-h1-2026/", "A"),
    _s("acquire_saas_annual", "Acquire.com 已确认成交的 SaaS 中位数倍数（2024 与 2025 均为此值）", 3.9, "×年净利",
       "Acquire.com Biannual Acquisition Multiples Report (2026-01)", "https://blog.acquire.com/acquire-com-biannual-acquisition-multiples-report-jan-2026/", "A",
       note="B 端订阅型资产较内容型资产有约 45% 溢价，是本方案设置 B 端通道的估值理由之一"),
    _s("bls_survival_5yr", "美国新建企业 5 年存活率（BLS 完整队列均值）", 51.5, "%",
       "美国劳工统计局 BLS Business Employment Dynamics Table 7", "https://www.bls.gov/bdm/us_age_naics_00_table7.txt", "A",
       note="BLS 仅统计有雇员的经营单位，单人无雇员企业基本不在此口径内，51.5% 应视为上界"),
    _s("bls_survival_1yr", "美国新建企业 1 年存活率", 80.1, "%",
       "BLS Table 7", "https://www.bls.gov/bdm/us_age_naics_00_table7.txt", "A"),
    _s("bls_survival_2yr", "美国新建企业 2 年存活率", 71.2, "%",
       "BLS Table 7", "https://www.bls.gov/bdm/us_age_naics_00_table7.txt", "A"),
    _s("bls_survival_3yr", "美国新建企业 3 年存活率", 63.8, "%",
       "BLS Table 7", "https://www.bls.gov/bdm/us_age_naics_00_table7.txt", "A"),
    _s("bls_survival_4yr", "美国新建企业 4 年存活率", 57.0, "%",
       "BLS Table 7", "https://www.bls.gov/bdm/us_age_naics_00_table7.txt", "A"),
    _s("correlation_below_1x", "风险投资基准：未能返还 1 倍本金的融资占比", 65.0, "%",
       "Correlation Ventures（21,640 笔美国风险融资，2004–2013）", "https://sethlevine.com/archives/2014/08/venture-outcomes-are-even-more-skewed-than-you-think.html", "C",
       note="原始研究从未直接公开，所有引用均可追溯至同一转述；仅作对照基准"),
    _s("microconf_under_1k_mrr", "独立 SaaS 中月经常性收入低于 1000 美元的占比（最大单一群体）", 28, "%",
       "MicroConf State of Independent SaaS 2024 (n=469)", "https://microconf.com/state-of-independent-saas", "D",
       note="自选择样本；分母不含从未上线即放弃的项目，真实无条件比例更差"),
    _s("indie_reach_1k_mrr", "已上线的独立项目达到 1000 美元/月的概率区间", "20–30", "%",
       "MicroConf 2024 与 RockingWeb 2025 两项自选择调查的交叉推断", "https://microconf.com/state-of-independent-saas", "D",
       note="仅用于校准蒙特卡洛的成熟流量分布，不作为结论直接引用"),
    _s("indie_never_5k", "已上线的独立项目从未达到 5000 美元/月的比例", 82, "%",
       "RockingWeb 2025 (n=1,000)", "https://rockingweb.com/indie-hackers-statistics", "D"),
]

SOURCES: dict[str, Source] = {s.id: s for s in _SOURCES}
assert len(SOURCES) == len(_SOURCES), "存在重复的 Source id"


# ---------------------------------------------------------------------------
# 八、我方假设：无外部出处，必须标注推理与区间
# ---------------------------------------------------------------------------
def _a(*args, **kwargs) -> Assumption:
    return Assumption(*args, **kwargs)


_ASSUMPTIONS: list[Assumption] = [
    # --- 资本与投入 ---
    _a("cash_budget", "创始人可投入的自有现金上限", 6000, "美元",
       "用户给定区间 2,000–10,000 美元，取中值建模；超出即判定为'无法继续注资'而失败",
       low=2000, high=10000),
    _a("weekly_hours", "每周可投入工时", 20, "小时/周",
       "用户给定硬约束", low=15, high=25),
    _a("founder_hourly_cost", "创始人时间的机会成本单价", 25, "美元/小时",
       "无法从外部来源确定个人机会成本，取一个保守的可自证时薪；本项目将现金口径与"
       "含时间成本的全成本口径分别列示，避免只报现金 ROI 造成的系统性高估",
       low=10, high=60),

    # --- 流量结构 ---
    _a("mature_sessions_p22", "成熟期月会话数达到该值的概率为 22%（校准锚点一）", 50000, "会话/月",
       "50,000 会话/月约对应 1,000 美元/月广告收入；用已上线独立项目达到 1k MRR 的 20–30% "
       "区间下沿偏中位置作为校准点",
       low=40000, high=60000),
    _a("mature_sessions_p5", "成熟期月会话数达到该值的概率为 5%（校准锚点二）", 300000, "会话/月",
       "约对应 5,000 美元/月；调研结论为'36–48 个月且多数站点永远达不到'，取 5%",
       low=250000, high=350000),
    _a("ramp_midpoint_months", "流量爬坡的中点月份（logistic 曲线拐点）", 24, "月",
       "调研给出 1,000 美元/月需 20–30 个月；取区间中值，按正态抖动 σ=6 个月",
       low=18, high=32),
    _a("ramp_steepness", "流量爬坡陡度参数 k", 5.0, "月",
       "使 10%→90% 爬坡约耗时 22 个月，与 YMYL 新域名的实际观测节奏一致",
       low=3.0, high=8.0),

    # --- 算法与处罚风险 ---
    _a("algo_event_interval", "算法更新事件的平均间隔", 1.75, "月",
       "由 SOURCES.core_updates_28mo（28 个月 16 次）直接推得", low=1.5, high=2.5),
    _a("algo_shock_median", "单次算法事件对可见度的中位乘数", 0.985, "倍",
       "小型出版商长期承压：该中位数叠加事件频率后，年化中位拖累约 -10%，"
       "显著弱于 Chartbeat 观测到的 -60%，因为后者是存量站点且不含内容增量",
       low=0.96, high=1.00),
    _a("algo_shock_sigma", "单次算法事件乘数的对数标准差", 0.16, "-",
       "使约 5% 的事件造成 35% 以上的可见度损失，与 2026-03 更新中 24.1% 页面跌出前 100 的"
       "观测量级相容", low=0.10, high=0.25),
    _a("penalty_hazard_annual", "遭遇人工处罚/大规模内容滥用判罚的年风险率", 0.06, "/年",
       "全样本基准率为 1.9%（含大量人工站）；纯 AI 内容站的条件概率显著更高，"
       "本方案采用具名责任编辑与工具优先形态以压低该值，取 6% 并做敏感性",
       low=0.02, high=0.15),
    _a("penalty_traffic_residual", "遭处罚后残余流量比例", 0.05, "倍",
       "案例观测为整目录被移出索引，且 AI 引用同步消失", low=0.01, high=0.15),
    _a("penalty_recovery_prob", "处罚后 12 个月内实质恢复的概率", 0.22, "-",
       "Glenn Gabe 追踪的 HCU 受灾站中仅 22% 恢复了 20% 以上流量", low=0.10, high=0.35),

    # --- 变现 ---
    _a("pages_per_session", "每会话页面浏览数", 1.15, "-",
       "工具型与查询型内容以单页即走为主；用于会话 RPM 与 PV RPM 的换算",
       low=1.05, high=1.40),
    _a("rpm_adsense", "AdSense 阶段会话 RPM", 5.0, "美元/千会话",
       "调研给出 3–8 美元区间，取中值", low=3.0, high=8.0),
    _a("rpm_journey", "Journey by Mediavine 阶段会话 RPM", 8.5, "美元/千会话",
       "调研给出 5–12 美元区间，取中值", low=5.0, high=12.0),
    _a("rpm_premium", "Raptive / Mediavine Official 阶段会话 RPM（全年均值）", 19.0, "美元/千会话",
       "调研中心估计 16–22 美元：政府福利类为低商业意图的信息型流量，"
       "不享有信用卡/保险类金融内容的溢价", low=10.0, high=30.0),
    _a("rpm_annual_decay", "RPM 的年衰减率", 0.10, "/年",
       "Mediavine 发布商报告同比 -30%，但恒定 -30% 不可持续；取 -10% 作为长期结构性下行",
       low=0.00, high=0.25),
    _a("b2b_arpa", "B 端数据订阅的每账户月均收入", 79.0, "美元/月",
       "面向 fintech、AI 应用与地方媒体的结构化数据订阅，定价在 29–199 美元区间取中枢；"
       "该价位使 Stripe 固定手续费占比降至 3% 以下，规避了 0.99 美元微支付的致命结构",
       low=29.0, high=199.0),
    _a("b2b_conv_per_10k_sessions", "每 1 万月会话可转化的 B 端付费账户数", 0.35, "个",
       "消费者流量作为 B 端的发现渠道，转化率低但稳定；无外部基准，"
       "属本模型最弱的假设之一，已纳入敏感性分析", low=0.10, high=1.00),
    _a("b2b_monthly_churn", "B 端订阅月流失率", 0.05, "-",
       "小微 B2B 数据订阅的常见量级", low=0.03, high=0.10),
    _a("b2b_ramp_start_month", "B 端通道开始产生收入的月份", 13, "月",
       "第一年用于把 50 州发放规则做成可信数据集，无可售之物", low=9, high=18),
    _a("b2b_inbound_per_month", "不依赖消费者流量的 B 端月均自然获客数（目录、API 市场、开源渠道）",
       0.15, "个/月",
       "这是双通道方案真正的对冲价值所在：搜索流量归零时这条线仍在。"
       "泊松到达，稳态约 3 个账户；无外部基准，属弱假设", low=0.05, high=0.40),
    _a("p_sale_given_threshold", "达到可挂牌门槛后 5 年内实际成交的概率", 0.75, "-",
       "Empire Flippers 平均在市 101.8 天，但其自述会在估值前拒掉多数提交；"
       "含 AI 内容的资产平均多花 54% 时间才售出", low=0.50, high=0.90),

    # --- 成本 ---
    _a("content_pages_total", "五年内维护的页面总量", 900, "页",
       "50 州 × 约 4 类页面 + 联邦付款日历 + Direct Express 过渡 + 长尾问答；"
       "刻意不做规模化铺量，因为大规模内容滥用政策与页面数无关而与意图有关",
       low=400, high=2000),
    _a("llm_cost_per_page_cycle", "每页每次生成/更新的 LLM 成本", 0.03, "美元",
       "取 DeepSeek 0.0024 与 Opus 0.085 之间的偏保守值，含四段式核验流水线",
       low=0.0024, high=0.085),
    _a("page_refresh_per_year", "每页年均更新次数", 4, "次/年",
       "发放日历按月变动，州规则按年变动；这是本产品准确性的核心成本",
       low=2, high=12),
    _a("compliance_legal_reserve", "合规一次性支出（品牌与页面合规审查、条款与免责声明起草）", 800, "美元",
       "第 1140 条按每次浏览计罚，品牌名、域名、视觉与页面文案必须在发布前定型，"
       "这是发布前必须花的钱，不是事后审计项", low=300, high=2500),

    # --- 退出 ---
    _a("exit_multiple_base", "退出倍数基准（已计入 AI 内容折让）", 14.0, "×月净利",
       "Empire Flippers 30 万美元以下档为 22.42× 月净利；Motion Invest 实际成交显示"
       "含 AI 内容折让 39%，22.42 × 0.61 ≈ 13.7；B 端订阅收入占比可部分修复倍数",
       low=11.0, high=22.0),
    _a("exit_min_profit", "存在买家的最低月净利门槛", 200.0, "美元/月",
       "低于此规模的资产在主流经纪平台上基本无法挂牌成交", low=100.0, high=500.0),
    _a("exit_b2b_multiple_premium", "B 端订阅收入部分的倍数溢价系数", 1.8, "倍",
       "Acquire.com 已确认成交 SaaS 中位 3.9× 年净利，约为内容站 1.87× 的 2.1 倍；"
       "考虑到本方案 B 端体量小、客户集中，折半后取 1.8", low=1.0, high=2.5),

    # --- 模拟 ---
    _a("mc_paths", "蒙特卡洛路径数", 20000, "条", "在 3 秒内可完成且使各分位数稳定"),
    _a("mc_horizon_months", "模拟期长度", 60, "月", "与 5 年收益率口径一致"),
    _a("mc_seed", "随机种子", 20260726, "-", "固定种子以保证结论可复现"),
]

ASSUMPTIONS: dict[str, Assumption] = {a.id: a for a in _ASSUMPTIONS}
assert len(ASSUMPTIONS) == len(_ASSUMPTIONS), "存在重复的 Assumption id"


# ---------------------------------------------------------------------------
# 访问器：模型代码只能通过这两个函数取数
# ---------------------------------------------------------------------------
def S(key: str) -> Any:
    """取一条已引用来源的数值。"""
    if key not in SOURCES:
        raise KeyError(f"未登记的来源: {key}")
    return SOURCES[key].value


def A(key: str) -> Any:
    """取一条我方假设的数值。"""
    if key not in ASSUMPTIONS:
        raise KeyError(f"未登记的假设: {key}")
    return ASSUMPTIONS[key].value


def A_range(key: str) -> tuple[Any, Any]:
    a = ASSUMPTIONS[key]
    lo = a.low if a.low is not None else a.value
    hi = a.high if a.high is not None else a.value
    return lo, hi


def export_ledger(path: Path | None = None) -> Path:
    """把 SOURCES + ASSUMPTIONS 导出为可审计的 data/sources.csv。"""
    path = path or (DATA / "sources.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["类型", "编号", "论断", "数值", "单位", "发布方/推理", "URL", "置信度", "取数日期", "备注"])
    for s in _SOURCES:
        w.writerow(["来源", s.id, s.claim, s.value, s.unit, s.publisher, s.url,
                    s.confidence, s.retrieved, s.note])
    for a in _ASSUMPTIONS:
        rng = ""
        if a.low is not None or a.high is not None:
            rng = f"敏感性区间 {a.low} ~ {a.high}"
        w.writerow(["假设", a.id, a.claim, a.value, a.unit, a.rationale, "",
                    "假设", RETRIEVED, (a.note + " " + rng).strip()])
    # BOM 便于 Excel 直接打开中文 CSV
    path.write_text("\ufeff" + buf.getvalue(), encoding="utf-8")
    return path


def ledger_stats() -> dict[str, Any]:
    by_conf: dict[str, int] = {}
    for s in _SOURCES:
        by_conf[s.confidence] = by_conf.get(s.confidence, 0) + 1
    return {
        "n_sources": len(_SOURCES),
        "n_assumptions": len(_ASSUMPTIONS),
        "by_confidence": dict(sorted(by_conf.items())),
        "share_primary_pct": round(100.0 * by_conf.get("A", 0) / len(_SOURCES), 1),
    }


if __name__ == "__main__":
    enable_utf8_stdout()
    p = export_ledger()
    st = ledger_stats()
    print(f"来源账本已写入: {p}")
    print(f"来源 {st['n_sources']} 条 / 假设 {st['n_assumptions']} 条")
    print(f"置信度分布: {st['by_confidence']}  一手来源占比 {st['share_primary_pct']}%")
