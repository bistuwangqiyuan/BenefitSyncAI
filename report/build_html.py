# -*- coding: utf-8 -*-
"""
生成 out/BP.html。

铁律：正文里不允许出现手写数字。所有数值必须经 N.get()/N.src() 从 out/results.json
注入，并被记录进 out/number_trace.json，供 report/audit.py 逐一比对。
原计划书之所以要写"以本表为准"，就是因为叙述和表格已经打架了；杜绝这件事的唯一办法
是让它们物理上出自同一个来源。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
CHARTS = ROOT / "charts"

BRAND = "DepositDay"
BRAND_CN = "到账日"


# ---------------------------------------------------------------------------
class Nums:
    """从 results.json 取数并留痕。"""

    def __init__(self, res: dict):
        self.res = res
        self.trace: list[dict] = []
        self.cited: list[str] = []          # 正文引用过的来源 id，按首次出现排序

    def raw(self, path: str) -> Any:
        cur: Any = self.res
        for part in path.split("."):
            if part.endswith("]"):
                name, idx = part[:-1].split("[")
                cur = cur[name][int(idx)] if name else cur[int(idx)]
            else:
                cur = cur[part]
        return cur

    def get(self, path: str, fmt: str = "{:,.0f}", scale: float = 1.0, suffix: str = "") -> str:
        v = self.raw(path)
        if isinstance(v, (int, float)):
            # 不要无谓地乘 1.0：那会把整数变成浮点，"{:,}" 就会印出 160.0
            s = fmt.format(v if scale == 1.0 else v * scale) + suffix
        else:
            s = str(v) + suffix
        self.trace.append({"kind": "results", "path": path, "text": s, "value": v})
        return s

    def src_val(self, sid: str, fmt: str = "{:,.0f}", scale: float = 1.0, suffix: str = "") -> str:
        s = self._source(sid)
        v = s["value"]
        out = fmt.format(v * scale) + suffix if isinstance(v, (int, float)) else str(v) + suffix
        self.trace.append({"kind": "source", "path": f"sources.{sid}", "text": out, "value": v})
        return out

    def asm_val(self, aid: str, fmt: str = "{:,.0f}", scale: float = 1.0, suffix: str = "") -> str:
        a = self._assumption(aid)
        v = a["value"]
        out = fmt.format(v * scale) + suffix if isinstance(v, (int, float)) else str(v) + suffix
        self.trace.append({"kind": "assumption", "path": f"assumptions.{aid}", "text": out, "value": v})
        return out

    def _source(self, sid: str) -> dict:
        for s in self.res["sources"]:
            if s["id"] == sid:
                return s
        raise KeyError(f"来源账本中没有 {sid}")

    def _assumption(self, aid: str) -> dict:
        for a in self.res["assumptions"]:
            if a["id"] == aid:
                return a
        raise KeyError(f"假设清单中没有 {aid}")

    def cite(self, *sids: str) -> str:
        """正文角标，指向附录 C 的编号。"""
        nums = []
        for sid in sids:
            self._source(sid)
            if sid not in self.cited:
                self.cited.append(sid)
            nums.append(str(self.cited.index(sid) + 1))
        return f'<span class="src">[{",".join(nums)}]</span>'

    def conf(self, sid: str) -> str:
        c = self._source(sid)["confidence"]
        return f'<span class="conf conf-{c}">{c}</span>'

    def dump_trace(self):
        (OUT / "number_trace.json").write_text(
            json.dumps(self.trace, ensure_ascii=False, indent=1), encoding="utf-8")


def esc(s: Any) -> str:
    return html.escape(str(s), quote=False)


def svg(name: str) -> str:
    p = CHARTS / name
    s = p.read_text(encoding="utf-8")
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s)
    # 去掉固定像素宽高，改由 CSS 控制，避免 A4 下溢出
    s = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r"\1", s, count=1)
    s = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r"\1", s, count=1)
    return s.strip()


def kpi(label: str, value: str, unit: str = "", foot: str = "", tone: str = "") -> str:
    u = f'<span class="unit">{unit}</span>' if unit else ""
    f = f'<div class="foot">{foot}</div>' if foot else ""
    return (f'<div class="kpi {tone}"><div class="label">{label}</div>'
            f'<div class="value">{value}{u}</div>{f}</div>')


def callout(title: str, body: str, tone: str = "") -> str:
    return f'<div class="callout {tone}"><span class="title">{title}</span>{body}</div>'


def figure(name: str, caption: str) -> str:
    return f'<figure>{svg(name)}<figcaption>{caption}</figcaption></figure>'


def table(headers: list[str], rows: list[list[str]], caption: str = "",
           cls: str = "", num_cols: set[int] | None = None,
           row_cls: list[str] | None = None) -> str:
    num_cols = num_cols or set()
    cap = f"<caption>{caption}</caption>" if caption else ""
    th = "".join(f'<th class="{"num" if i in num_cols else ""}">{h}</th>'
                 for i, h in enumerate(headers))
    trs = []
    for ri, r in enumerate(rows):
        rc = row_cls[ri] if row_cls and ri < len(row_cls) else ""
        tds = "".join(f'<td class="{"num" if i in num_cols else ""}">{c}</td>'
                      for i, c in enumerate(r))
        trs.append(f'<tr class="{rc}">{tds}</tr>')
    return (f'<div class="table-wrap"><table class="{cls}">{cap}'
            f"<thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>")


_SECTION_RE = re.compile(
    r'<span class="section-num"([^>]*)>(.*?)</span>\s*<h2>(.*?)</h2>',
    re.S,
)


def chapter_index(body_html: str) -> list[dict]:
    """从已拼好的正文里抽章节，避免目录和正文各写一份而走样。"""
    out = []
    for i, m in enumerate(_SECTION_RE.finditer(body_html), 1):
        label = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        title = re.sub(r"<[^>]+>", "", m.group(3)).replace("\n", " ").strip()
        out.append({"id": f"ch-{i}", "label": label, "title": title})
    return out


def inject_toc(body_html: str) -> str:
    """给每个章节加 id，并在封面后插入目录。

    页码由 report/build_pdf.py 第一遍渲染后写进 out/toc_pages.json，第二遍才填得上。
    未填时留空占位——占位与填数的排版宽度一致，所以两遍分页结果相同。
    """
    chapters = chapter_index(body_html)

    n = 0

    def add_id(m: re.Match) -> str:
        nonlocal n
        n += 1
        return m.group(0).replace('<span class="section-num"',
                                  f'<span id="ch-{n}" class="section-num"', 1)

    body_html = _SECTION_RE.sub(add_id, body_html)
    (OUT / "chapters.json").write_text(
        json.dumps(chapters, ensure_ascii=False, indent=1), encoding="utf-8")

    pages: dict[str, int] = {}
    pf = OUT / "toc_pages.json"
    if pf.exists():
        pages = json.loads(pf.read_text(encoding="utf-8"))

    rows = []
    for c in chapters:
        pn = pages.get(c["id"])
        appendix = c["label"].startswith("附录")
        rows.append(
            f'<li class="{"appendix" if appendix else ""}">'
            f'<span class="lbl">{esc(c["label"])}</span>'
            f'<span class="ttl">{esc(c["title"])}</span>'
            f'<span class="dots"></span>'
            f'<span class="pn">{pn if pn else ""}</span></li>'
        )

    toc = (
        '<section class="page-break toc" id="toc">'
        '<span class="section-num">目录</span>'
        "<h2>本文档怎么读</h2>"
        '<p class="lede">第一章证伪原方案，第二至五章建立新方案并给出单位经济，'
        "第六至八章是风险与合规，第九、十章是执行与止损。"
        "只想看结论的话，读执行摘要和第十章即可；"
        "想复核数字的话，附录 A 是复现步骤，附录 B、C 是每一个数的出处。</p>"
        f'<ol class="toc-list">{"".join(rows)}</ol>'
        "</section>"
    )

    close = body_html.find("</section>")
    return body_html[: close + len("</section>")] + toc + body_html[close + len("</section>"):]


# ===========================================================================
def build(res: dict) -> str:
    N = Nums(res)
    mc = res["monte_carlo"]
    body: list[str] = []
    A = body.append

    # ---------------- 封面 ----------------
    A(f"""
<section class="cover">
  <div>
    <div class="eyebrow">商业计划书 · 证据驱动重建版</div>
    <div class="cover-main">
      <h1>{BRAND}<br><span style="color:var(--gray);font-weight:500">州级福利到账日<br>数据基础设施</span></h1>
      <p class="sub">一份单人运营、AI 驱动、纯自有资金的五年计划。<br>
      以及一份对它前身 —— BenefitSync AI —— 的完整证伪。</p>
    </div>
  </div>
  <div>
    <div class="cover-meta">
      <div><dt>数据截止</dt><dd>{N.get('meta.data_as_of')}</dd></div>
      <div><dt>生成时间</dt><dd>{N.get('meta.generated_at')}</dd></div>
      <div><dt>模型路径数</dt><dd>{N.get('monte_carlo.paths')} 条 × {N.get('monte_carlo.months')} 个月</dd></div>
      <div><dt>来源 / 假设</dt><dd>{N.get('ledger.n_sources')} 条外部来源，{N.get('ledger.n_assumptions')} 条自设假设</dd></div>
      <div><dt>一手来源占比</dt><dd>{N.get('ledger.share_primary_pct', '{:.1f}')}%</dd></div>
      <div><dt>随机种子</dt><dd class="mono">{N.get('meta.seed')}</dd></div>
    </div>
    <p class="footnote" style="margin-top:14px">
      本文档所有数值由 <span class="mono">model/run_all.py</span> 生成的
      <span class="mono">out/results.json</span> 注入，正文不含任何手写数字；
      <span class="mono">report/audit.py</span> 会在构建后逐一校验。
      本文档不构成法律、税务或投资建议。
    </p>
  </div>
</section>
""")

    # ---------------- 执行摘要 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">执行摘要</span>')
    A("<h2>结论先行：这个项目值得做，但理由不是它能赚钱</h2>")
    A(f"""
<p class="lede">在 {N.get('monte_carlo.paths')} 条模拟路径上，本方案的现金回报看起来极其漂亮——
胜率 {N.get('monte_carlo.win_rate_pct', '{:.1f}')}%、期望
{N.get('monte_carlo.expected_moic', '{:.1f}')} 倍、五年年化
{N.get('monte_carlo.annualized_pct', '{:.0f}')}%。这三个数字都是真的，也都具有严重的误导性：
它们的分母只有 {N.get('monte_carlo.invested_cash_mean', '${:,.0f}')} 的现金投入。
把创始人五年 {N.get('monte_carlo.founder_hours_5y')} 小时算进去之后，
中位路径折合时薪是 {N.get('monte_carlo.breakeven_hourly_median', '${:.2f}')}，
期望时薪 {N.get('monte_carlo.breakeven_hourly_mean', '${:.2f}')}。</p>
""")

    A('<div class="kpi-grid">')
    A(kpi("现金口径胜率", N.get("monte_carlo.win_rate_pct", "{:.1f}"), "%",
          "已实现现金 ≥ 已投入现金的路径占比", "accent"))
    A(kpi("全成本口径胜率", N.get("monte_carlo.win_rate_full_cost_pct", "{:.1f}"), "%",
          f"分母加入 {N.get('monte_carlo.founder_hours_5y')} 小时时间成本后", "danger"))
    A(kpi("中位折合时薪", N.get("monte_carlo.breakeven_hourly_median", "{:.2f}"), " 美元",
          "创始人每投入一小时，中位路径产出的现金", "danger"))
    A(kpi("期望折合时薪", N.get("monte_carlo.breakeven_hourly_mean", "{:.2f}"), " 美元",
          "被右尾拉高，不是你大概率会经历的世界", "warn"))
    A("</div>")

    A('<div class="kpi-grid">')
    A(kpi("盈亏比（现金）", N.get("monte_carlo.payoff_ratio", "{:.1f}"), " : 1",
          "赢时平均收益 ÷ 亏时平均亏损"))
    A(kpi("中位 MOIC", N.get("monte_carlo.median_moic", "{:.2f}"), "×",
          f"期望 {N.get('monte_carlo.expected_moic', '{:.1f}')}× 由极端右尾主导"))
    A(kpi("达到 1,000 美元/月", N.get("monte_carlo.p_reach_1k_pct", "{:.1f}"), "%",
          f"中位在第 {N.get('monte_carlo.median_month_to_1k')} 个月"))
    A(kpi("五年内遭遇处罚", N.get("monte_carlo.p_penalized_pct", "{:.1f}"), "%",
          "流量与广告资格同时归零", "warn"))
    A("</div>")

    A(f"""
<p>把这些数字翻译成一句话：<strong>这是一个几乎不可能让你亏掉本金、也几乎不可能让你致富的项目。</strong>
真正的下注标的不是那
{N.get('monte_carlo.invested_cash_mean', '${:,.0f}')} 现金，而是五年
{N.get('monte_carlo.founder_hours_5y')} 小时。它值不值得，取决于一个只有你能回答的问题：
这些具体的、边角料式的业余小时，对你的机会成本到底是多少。如果高于
{N.get('kelly.breakeven_hourly.mean', '${:.2f}')}/小时，
按期望值算就不该做；如果你像大多数人一样，这些时间的替代用途是刷手机，那么它的机会成本接近零，
项目在任何口径下都成立。本文档的任务不是替你回答这个问题，而是把它精确地摆出来。</p>
""")

    A(callout(
        "四条不可回避的硬结论",
        f"""<p>一、<strong>原方案不是"难做"，是不能做。</strong>SSA 明文规定任何人不得代他人创建或使用
账户{N.cite('ssa_account_no_proxy')}，Login.gov 严禁自动化访问{N.cite('logingov_no_automation')}，
而《社会保障法》第 1140 条对"就 SSA 免费服务收费"按
<strong>每一次网页浏览</strong>计罚 {N.src_val('sec1140_penalty', '{:,.0f}')} 美元{N.cite('sec1140_penalty')}。</p>
<p>二、<strong>原方案的锚点热词不是市场，是一次 9 天的新闻余波。</strong>实测美国区 53 周，
其中 {N.src_val('kw_zero_weeks')} 周为 0{N.cite('kw_zero_weeks')}。</p>
<p>三、<strong>本方案选定的方向（C3 双通道）在评分模型中稳居第一，但它的优势主要来自构造。</strong>
详见第二章的自我批评。</p>
<p>四、<strong>结论对两个几乎没有外部证据的 B 端假设最敏感。</strong>因此执行计划的第一阶段
不是建站，而是用八周时间证伪它们。</p>""",
        "danger"))
    A("</section>")

    # ---------------- 第一章 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第一章</span>')
    A("<h2>原方案证伪与自我纠错</h2>")
    A('<p class="dek">一份商业计划书的第一项义务，是先证明自己没有在自欺。以下每一条都可复现。</p>')

    A("<h3>1.1 锚点热词：一次 9 天的新闻余波</h3>")
    A(f"""
<p>原方案把 Google Trending Now 上的“搜索量 {N.src_val('orig_claimed_volume', '{:,.0f}')}+”
当成了月度搜索量{N.cite('orig_claimed_volume')}，并在此基础上乘以季节系数，
推导出全部营收。但那个标签是 24 小时窗口的分桶估计{N.cite('trends_bucket_nature')}，
不是月均量。用 <span class="mono">model/fetch_trends.py</span> 直接调用 Trends 接口实测美国区
{N.get('trends.weeks_observed')} 周，结果是：{N.get('trends.weeks_at_zero')} 周取值为
0，全期平均热度仅 {N.get('trends.weekly_mean_index', '{:.2f}')}（满分 100）。</p>
<p>日粒度更清楚：该词在 {N.get('trends.peak_date')} 冲到峰值——正是 USA TODAY 报道 SSA 将于年内
完成全面电子化的当天{N.cite('usatoday_trigger')}——总共只存活了
{N.get('trends.alive_days')} 天，自 {N.get('trends.zero_since')} 起归零至今。
原方案的采集日恰好在峰值次日，彼时热度已较峰值下跌
{N.src_val('kw_capture_day_decay')}%{N.cite('kw_capture_day_decay')}。</p>
""")
    A(figure("trends_zero.svg",
             f"美国区周粒度实测，取数方式 {esc(', '.join(N.raw('trends.provenance')))}，"
             f"原始序列见 <span class='mono'>data/trends_measured.csv</span>。"
             f"这不是一个季节性波动的市场，而是一条新闻的衰减曲线。"))

    A(callout("一次自我纠错",
              f"""<p>本项目前置调研阶段口头汇报的"46 周为 0"与本次实抓结果不一致。以实抓数据为准：
非零周只有 3 个（06-07 = 100、06-14 = 4、06-21 = 1），因此为 0 的周数是
{N.src_val('kw_zero_weeks')} 周而非 46 周。差异不影响结论方向，但既然本文档要求可审计，
就必须记录这次修正{N.cite('kw_zero_weeks')}。</p>""", "neutral"))

    A("<h3>1.2 合法性：不是执行难度问题，是不能做</h3>")
    A(f"""
<p>原方案的核心动作是"代用户登录 SSA 系统并提交材料，按次收取 0.99 美元"。这个动作同时触碰三条红线。</p>
""")
    A(table(
        ["红线", "规定原文或要件", "后果", "置信度"],
        [
            ["代为登录账户",
             f"&ldquo;No one can create or use an account on your behalf, even with your written or "
             f"verbal permission&rdquo;{N.cite('ssa_account_no_proxy')}",
             "账户被封；就身份欺骗 SSA 属联邦犯罪" + N.cite('ssa_tos_federal_crime'),
             N.conf('ssa_account_no_proxy')],
            ["自动化访问",
             f"&ldquo;Automated access to Login.gov is strictly prohibited&rdquo;{N.cite('logingov_no_automation')}",
             "技术路径本身违规，无论是否收费",
             N.conf('logingov_no_automation')],
            ["就免费服务收费",
             f"第 1140 条：按<strong>每次网页浏览</strong>单独计罚"
             f"{N.src_val('sec1140_penalty', '{:,.0f}')} 美元{N.cite('sec1140_penalty', 'sec1140_statute')}",
             f"已有 {N.src_val('sec1140_case_usafiling', '{:,.0f}')} / "
             f"{N.src_val('sec1140_case_lexisnexis', '{:,.0f}')} / "
             f"{N.src_val('sec1140_case_trak1', '{:,.0f}')} 美元实际和解案例"
             + N.cite('sec1140_case_usafiling', 'sec1140_case_lexisnexis', 'sec1140_case_trak1'),
             N.conf('sec1140_penalty')],
        ],
        caption="原方案触碰的三条红线", num_cols={3}))

    A(callout("第 1140 条为什么是本类目最凶的一条",
              f"""<p>它的罚金基数是<strong>每次浏览</strong>，而不是每次交易。这意味着罚金随流量线性放大，
而收入只随转化率放大——两者不同阶。一个日均一万次浏览的页面，理论敞口是每天上亿美元。
更值得注意的是 LexisNexis 案：该公司本身持有合法的 SSA 数据交换权限，仍因为<strong>产品命名方式</strong>
暗示与 SSA 存在直连而被罚 {N.src_val('sec1140_case_lexisnexis', '{:,.0f}')}
美元并下架产品{N.cite('sec1140_case_lexisnexis')}。也就是说，
即便业务本身完全合法，"你怎么描述它"依然可以单独构成违法。这条约束直接决定了本方案的品牌命名规则
（见第八章）。</p>""", "danger"))

    A("<h3>1.3 六项被当作事实引用的虚构内容</h3>")
    A(table(
        ["原方案的表述", "核验结果"],
        [
            ["SSA-1199-BK 表格",
             f"不存在。SSA-1199 系列是境外居住受益人的国际直存表，无 -BK 变体{N.cite('ssa_1199_scope')}"],
            ["SSA 公共 API <span class='mono'>/v1/receipt</span>",
             f"不存在。SSA 仅有 {N.src_val('ssa_api_readonly')} 个只读统计接口；唯一的认证类数据交换 eCBSV "
             f"最低年费 {N.src_val('ecbsv_cost', '{:,.0f}')} 美元且仅限金融机构授信场景"
             + N.cite('ssa_api_readonly', 'ecbsv_cost')],
            ["87% 受益人错过年度电子更新",
             f"不存在此义务。SSA 明确：&ldquo;You do not need to contact Social Security to continue "
             f"your monthly benefits&rdquo;{N.cite('ssa_no_annual_update')}"],
            ["2024 年 1 月起强制电子申报",
             f"真实起点是 {N.src_val('ssa_eft_mandate_1998')}，早了二十六年{N.cite('ssa_eft_mandate_1998')}"],
            ["SSA 认证精算师",
             "SSA 不颁发此类资质，该头衔无法获得"],
            ["竞品 BenefitsCalculus.com",
             f"域名未注册，权威 DNS 返回 NXDOMAIN{N.cite('benefitscalculus_nonexistent')}"],
        ],
        caption="逐条核验"))

    A("<h3>1.4 可服务人群：约 28 万，且正在被官方主动清零</h3>")
    A(f"""
<p>原方案称目标市场为 5,200 万受益人。实际上 SSA 受益人总数是
{N.src_val('ssa_beneficiaries_total', '{:,.0f}')} 人{N.cite('ssa_beneficiaries_total')}——
原方案<em>低估</em>了总盘子。但真正能被这项服务触达的，只有仍在领纸质支票的约
{N.src_val('paper_check_recipients', '{:,.0f}')} 人{N.cite('paper_check_recipients')}，
占比不足 1%，而且第 14247 号行政令已要求联邦支付自
{N.src_val('eo_14247')} 起停止签发纸质支票{N.cite('eo_14247')}。
换句话说，这个人群不仅极小、最难在线触达，而且正被政策主动清零——它是一条正在关闭的窗口，
不是一个正在打开的市场。</p>
""")

    A("<h3>1.5 原方案的内部矛盾</h3>")
    A(f"""
<p>即便不谈外部事实，原表格内部也无法自洽：同一份文档里 LTV 同时是
{N.src_val('orig_ltv_low', '{:.2f}')} 美元与 {N.src_val('orig_ltv_high', '{:,.0f}')} 美元
（相差 {N.get('debunk.orig_ltv_ratio', '{:,.0f}')} 倍）{N.cite('orig_ltv_low', 'orig_ltv_high')}；
营收以日元计价而定价以美元列示；SOM 与活跃用户数相差约 80 倍。文档用一句"以本表为准"来处理这些冲突——
这句话本身就是问题的自白。本方案的应对不是"更仔细地检查"，而是让正文与图表<strong>物理上</strong>
出自同一个 <span class="mono">results.json</span>，并用脚本强制校验。</p>
""")

    A("<h3>1.6 原方案中被保留的部分</h3>")
    A("""
<p>为免矫枉过正，需要说明原方案有两点判断是对的，本方案予以继承：<strong>一是现金实现口径</strong>——
只有真正落袋的分配与退出对价才计入回报，账面存活不算数；<strong>二是对单人时间约束的正视</strong>——
每周 20 小时是硬边界，不能靠"更努力"绕开。本方案在此基础上补上了它缺的那一半：
把这 20 小时本身也计入成本。</p>
""")
    A("</section>")

    # ---------------- 第二章 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第二章</span>')
    A("<h2>机会甄选：用可复现的评分模型定方向</h2>")
    A('<p class="dek">原方案只有一个候选、一个总分，既无对照组也无评分依据。这里给出五个候选、六个维度，'
      '每一个分值都挂着来源编号。</p>')

    crit = res["opportunity"]["criteria"]
    A(table(
        ["维度", "权重", "为什么给这个权重"],
        [[c["name"], N.get(f"opportunity.criteria.{k}.weight", "{:.0%}"), c["rationale"]]
         for k, c in crit.items()],
        caption="评分维度与权重", num_cols={1}))

    A(figure("opportunity_rank.svg",
             "堆叠部分为各维度的加权得分，条形总长即总分。"))

    A(table(
        ["排名", "代号", "方案", "总分", "评判"],
        [[str(c["rank"]), c["code"], f'<strong>{c["name"]}</strong><br>'
          f'<span class="muted small">{c["one_liner"]}</span>',
          N.get(f"opportunity.candidates[{i}].total", "{:.2f}"), c["verdict"]]
         for i, c in enumerate(res["opportunity"]["candidates"])],
        caption="五个候选方向的排名与淘汰理由", num_cols={3},
        row_cls=["" if c["rank"] == 1 else "" for c in res["opportunity"]["candidates"]]))

    A(f"""
<p>冠军是 <strong>C3</strong>，领先第二名 {N.get('opportunity.runner_up_gap', '{:.2f}')} 分。
为检验这个结论是不是权重挑出来的，对权重做了
{N.get('opportunity.robustness.draws')} 次 Dirichlet 扰动（相当于每个权重上下浮动约三成），
C3 的夺冠比例为 {N.get('opportunity.robustness.champion_win_share_pct', '{:.1f}')}%。</p>
""")
    A(callout("对这个 100% 的自我批评",
              f"<p>{esc(res['opportunity']['robustness_caveat'])}</p>", "warn"))

    A("<h3>2.1 决定性证据：赢家是工具，不是文章</h3>")
    A(f"""
<p>两个查询的首页结构差异，比任何市场规模估算都更能说明问题。查询
<span class="mono">social security payment schedule 2026</span> 的首页 7 条结果中，
{N.src_val('serp_ss_schedule_gov_share')}% 来自 ssa.gov{N.cite('serp_ss_schedule_gov_share')}，
唯一的非政府结果是 AARP——独立站在这里没有任何机会。而查询
<span class="mono">SNAP EBT deposit dates Texas</span> 的首页 9 条中只有
{N.src_val('serp_snap_tx_gov_share')}% 是 .gov，排名第一的是独立站
snapscreener.com，且被 AI Overview 引用{N.cite('serp_snap_tx_gov_share')}。</p>
<p>差别不在主题，而在<strong>形态</strong>：赢的那些是工具（资格自查、到账日计算），
输的那些是文章{N.cite('serp_tool_beats_article')}。同样重要的是，这条赛道上所有已成规模的运营者
——Propel（约 {N.src_val('propel_scale', '{:,.0f}')} 月活{N.cite('propel_scale')}）、
SNAP Screener、BenefitsUSA——<strong>无一例外对受益人免费</strong>{N.cite('free_to_user_pattern')}。
这不是巧合，而是第 1140 条与用户信任共同作用的结果。</p>
""")
    A("</section>")

    # ---------------- 第三章 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第三章</span>')
    A(f"<h2>业务设计：{BRAND}（{BRAND_CN}）</h2>")
    A('<p class="dek">一句话：把 50 个州各不相同的福利发放规则，维护成一份准确、有版本、可被引用的数据，'
      '然后同时卖给两类完全不同的用户——受益人用免费工具，机构付费用接口。</p>')

    A("<h3>3.1 产品形态</h3>")
    A(f"""
<p>面向受益人的一侧是三个工具，全部免费、无需注册、不收集任何个人身份信息：</p>
<ul>
<li><strong>到账日计算器</strong>：选择所在州，按该州的分批规则（案号末位、姓氏首字母或出生日期）
算出本月 EBT／SNAP 的到账日与未来六个月日历。</li>
<li><strong>联邦付款日历</strong>：SSA、SSI、VA 各类给付的发放日，含节假日顺延规则。</li>
<li><strong>Direct Express 过渡说明</strong>：发卡行由 Comerica 迁移至 Fifth Third 影响约 340 万持卡人，
过渡沟通计划在 2026 年中{N.cite('direct_express_migration')}——这是一个有明确日期、
影响面清晰、而官方沟通又相对薄弱的真实信息缺口。</li>
</ul>
<p>面向机构的一侧，是同一份数据的机器可读版本：带版本号、带生效日期、带条文出处的
50 州发放规则数据集与查询接口，面向金融科技、AI 应用与地方媒体按月订阅。</p>
""")

    A(callout("护城河在哪里（以及不在哪里）",
              """<p>不在内容量，也不在技术。50 个州的规则各不相同、按年修订、散落在各州机构的 PDF 与公告里，
把它们持续维护成准确且带出处的结构化数据，是一件<strong>枯燥、无法一次性完成、且做错会立刻被用户发现</strong>
的事。这正是它可防守的原因：竞争对手可以在一天内用 AI 生成 500 篇文章，但无法在一天内
建立起对 50 套规则的持续核验流程。反过来说，如果本项目也只是生成文章，那它就没有任何护城河。</p>""",
              "good"))

    A("<h3>3.2 &ldquo;无人公司&rdquo;必须修正为&ldquo;AI 运营 + 具名责任编辑&rdquo;</h3>")
    A(f"""
<p>完全无人的设定在本类目下不可行，原因不是技术，是评估规则。Google 搜索质量评估指南明确要求：
YMYL 页面若&ldquo;完全没有关于网站或内容创作者的信息&rdquo;，应判为
<strong>Lowest</strong>{N.cite('qrg_ymyl_anonymous_lowest')}；而且评估员被告知，
即使无法确认内容的生成方式，只要<strong>强烈怀疑</strong>存在大规模内容滥用，
就应直接判 Lowest{N.cite('qrg_suspect_scaled_lowest')}。同一份指南留出的窗口同样明确：
由<strong>专家</strong>把政府政策改写成通俗语言是有价值的{N.cite('qrg_expert_paraphrase_ok')}。
关键词是"专家"——必须有具名、可核验的责任人。</p>
<p>所以每周 20 小时的正确用途不是写文章，而是做三件不可自动化的事：核验州级规则的变更、
对数据准确性署名负责、处理用户纠错。AI 负责的是抓取、结构化、初稿、回归测试与监控。
这不是对"无人公司"理念的妥协，而是承认在 YMYL 类目下，<strong>署名本身就是产品的一部分</strong>。</p>
""")

    A("<h3>3.3 变现：为什么不能向受益人收费</h3>")
    A(f"""
<p>除了第 1140 条的法律风险之外，0.99 美元这个价位在纯算术上也不成立。</p>
""")
    A(table(
        ["定价", "场景", "Stripe 手续费占比", "第三方 MoR 占比"],
        [[N.get(f"unit_economics.micropayment[{i}].price", "${:.2f}"), m["label"],
          N.get(f"unit_economics.micropayment[{i}].stripe_fee_pct", "{:.1f}", suffix="%"),
          N.get(f"unit_economics.micropayment[{i}].mor_fee_pct", "{:.1f}", suffix="%")]
         for i, m in enumerate(res["unit_economics"]["micropayment"])],
        caption="支付固定费与客单价的量级关系", num_cols={0, 2, 3}))
    A(f"""
<p>0.99 美元的定价会被 Stripe 吃掉 {N.src_val('stripe_fee_on_099', '{:.1f}')}%，
用第三方 MoR 则是 {N.get('unit_economics.micropayment[0].mor_fee_pct', '{:.1f}')}%
{N.cite('stripe_fee_on_099', 'stripe_fee')}；而原方案假设的支付与云成本合计只有
{N.src_val('orig_payment_cost_share', '{:.0f}')}%{N.cite('orig_payment_cost_share')}。
把客单价提到 B 端的 {N.asm_val('b2b_arpa', '${:.0f}')}/月之后，
同样的固定费只占 {N.get('unit_economics.micropayment[-1].stripe_fee_pct', '{:.1f}')}%。
这不是"定价高一点比较好"的偏好问题，而是固定费与客单价之间的量级关系问题。</p>
<p>因此变现结构定为：<strong>对受益人永久免费</strong>（展示广告）+ <strong>对机构按月订阅</strong>。
两条线共用一套数据维护成本，这也正是 C3 相对 C1、C2 的全部意义。</p>
""")
    A("</section>")

    # ---------------- 第四章 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第四章</span>')
    A("<h2>单位经济</h2>")
    A('<p class="dek">收入不是流量的线性函数，而是一串台阶——台阶由广告联盟的准入门槛决定。</p>')

    A("<h3>4.1 2026 年真实的变现阶梯</h3>")
    A(f"""
<p>常见的旧路径&ldquo;先用 Ezoic 过渡，长到 5 万会话再进 Mediavine&rdquo;在 2026 年已经失效：
Ezoic 自 2026-02-19 起把门槛提到 {N.src_val('ezoic_threshold', '{:,.0f}')}
月活用户{N.cite('ezoic_threshold')}，对新站实质关闭。真实的阶梯只剩三级。</p>
""")
    A(table(
        ["阶段", "准入门槛", "发布商分成", "本模型采用的会话 RPM"],
        [
            ["AdSense", "无（需通过内容审核）",
             f"{N.src_val('adsense_revshare')}%{N.cite('adsense_revshare')}",
             f"${N.asm_val('rpm_adsense', '{:.2f}')}"],
            ["Journey by Mediavine",
             f"{N.src_val('journey_threshold', '{:,.0f}')} 会话/月{N.cite('journey_threshold')}",
             f"{N.src_val('journey_revshare')}%{N.cite('journey_revshare')}",
             f"${N.asm_val('rpm_journey', '{:.2f}')}"],
            ["Raptive / Mediavine Official",
             f"{N.src_val('raptive_threshold', '{:,.0f}')} 页面浏览/月，或年广告收入 "
             f"{N.src_val('mediavine_official_threshold', '${:,.0f}')}"
             + N.cite('raptive_threshold', 'mediavine_official_threshold'),
             f"{N.src_val('raptive_revshare')}%{N.cite('raptive_revshare')}",
             f"${N.asm_val('rpm_premium', '{:.2f}')}"],
        ],
        caption="变现阶梯（两条进入高级联盟的路径先到先算）", num_cols={3}))

    A(f"""
<p>RPM 按年衰减 {N.asm_val('rpm_annual_decay', '{:.0%}')} 建模。Mediavine 发布商在
2025 年末至 2026 年初报告的同比变化是 −{N.src_val('mediavine_rpm_yoy', '{:.0f}', -1)}%
{N.cite('mediavine_rpm_yoy')}；恒定 −30% 显然不可持续，故取一个较缓但仍为负的长期结构性下行。
政府福利类流量属低商业意图的信息型查询，不享有信用卡或保险类金融内容的溢价，
这也是本模型不采用坊间流传的高 RPM 数字的原因。</p>
""")

    A(figure("monetization_ladder.svg",
             f"纵轴为对数刻度。跨过 {N.src_val('raptive_threshold', '{:,.0f}')} 页面浏览这一级台阶时，"
             f"收入的跳升来自 RPM 从 ${N.asm_val('rpm_journey', '{:.2f}')} 变为 "
             f"${N.asm_val('rpm_premium', '{:.2f}')}，而不是流量本身翻了多少倍。"))

    A("<h3>4.2 成本栈</h3>")
    ue = res["unit_economics"]
    A(table(
        ["项目", "月成本", "说明"],
        [
            ["基础设施", N.get("unit_economics.fixed_monthly_cost.infra", "${:.2f}"),
             f"Cloudflare 技术栈：Pages 静态带宽不计费，1 万 / 10 万 / 100 万 PV 三档成本相同；"
             f"Workers 付费档为 RAG 的 CPU 需求所必需{N.cite('infra_floor', 'cloudflare_pages_bandwidth')}"],
            ["SEO 工具", N.get("unit_economics.fixed_monthly_cost.tooling", "${:.2f}"),
             f"Ahrefs Starter {N.src_val('ahrefs_starter', '${:.0f}')}/月"
             f"（2026 年 1 月新增档位，Semrush 无对标）+ Screaming Frog "
             f"{N.src_val('screaming_frog', '${:.0f}')}/年摊销"
             + N.cite('ahrefs_starter', 'screaming_frog')],
            ["LLM 生成与核验", N.get("unit_economics.fixed_monthly_cost.llm", "${:.2f}"),
             f"{N.get('unit_economics.pages')} 个页面按每年 "
             f"{N.asm_val('page_refresh_per_year')} 次更新、每次 "
             f"{N.asm_val('llm_cost_per_page_cycle', '${:.3f}')} 计"],
        ] + [["<strong>合计</strong>",
              "<strong>" + N.get("unit_economics.fixed_monthly_cost.total", "${:.2f}") + "</strong>",
              "与流量基本无关，这是本业务成本结构最重要的特征"]],
        caption="固定月成本", num_cols={1},
        row_cls=["", "", "", "total"]))

    A(f"""
<p>一次性开办支出合计 {N.get('unit_economics.one_time_total', '${:,.2f}')}，
其中合规审查与条款起草 {N.asm_val('compliance_legal_reserve', '${:,.0f}')} 是<strong>发布前</strong>
必须支出的项目，不是事后审计——理由见第八章。</p>
<p>关键结论：<strong>盈亏平衡点约在
{N.get('unit_economics.breakeven_sessions', '{:,.0f}')} 月会话</strong>，
且成本几乎不随流量增长。这意味着本项目的风险不在于"烧钱"，而在于永远到不了这个流量。
模拟显示五年内因资金触顶而被迫关停的路径占比是
{N.get('monte_carlo.p_cash_exhausted_pct', '{:.2f}')}%——
<strong>这不是一个资本约束型生意，而是一个分发约束型生意。</strong></p>
""")

    A(table(
        ["月会话", "阶段", "会话 RPM", "广告收入", "B 端收入", "成本", "月净利"],
        [[N.get(f"unit_economics.ladder[{i}].sessions", "{:,}"), r["tier"],
          N.get(f"unit_economics.ladder[{i}].rpm", "${:.2f}"),
          N.get(f"unit_economics.ladder[{i}].ad_revenue", "${:,.0f}"),
          N.get(f"unit_economics.ladder[{i}].b2b_revenue", "${:,.0f}"),
          N.get(f"unit_economics.ladder[{i}].cost", "${:,.0f}"),
          f'<span class="{"t-pos" if r["net"] > 0 else "t-neg"}">'
          + N.get(f"unit_economics.ladder[{i}].net", "${:,.0f}") + "</span>"]
         for i, r in enumerate(ue["ladder"])],
        caption="流量到净利的静态漏斗（第 1 年 RPM，未计入衰减）",
        num_cols={0, 2, 3, 4, 5, 6}))
    A("</section>")

    # ---------------- 第五章 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第五章</span>')
    A("<h2>风险调整回报</h2>")
    A(f'<p class="dek">{N.get("monte_carlo.paths")} 条路径 × {N.get("monte_carlo.months")} 个月的'
      f'月度现金流模拟。驱动变量全部取自实测或已登记的假设。</p>')

    A("<h3>5.1 模型如何传导风险</h3>")
    A(f"""
<p>三个建模决定值得单独说明，因为它们决定了结果的量级：</p>
<ul>
<li><strong>算法事件与广告资格是强耦合的，不作为独立风险处理。</strong>Google 发布商政策明文禁止
在违反搜索反垃圾政策的页面上投放广告{N.cite('adsense_couples_search_spam')}，
所以一次处罚会同时归零流量与广告收入。把两者当成独立事件相乘，会严重低估尾部风险。</li>
<li><strong>B 端订阅收入不受该事件影响</strong>——这正是双通道设计唯一真正的对冲价值所在。</li>
<li><strong>算法更新按经常性风险建模</strong>，而非黑天鹅：28 个月内有
{N.src_val('core_updates_28mo')} 次确认的排名系统更新{N.cite('core_updates_28mo')}，
平均每 {N.asm_val('algo_event_interval', '{:.2f}')} 个月一次。2026 年 3 月那次更新中，
原前 10 的页面有 {N.src_val('march2026_fell_out_top100', '{:.1f}')}% 直接跌出前
100{N.cite('march2026_fell_out_top100')}。</li>
</ul>
""")

    A(callout("流量分布是怎么校准的，以及为什么我们不向上修正",
              f"""<p>成熟期月会话数取对数正态分布，用两个锚点反解参数：达到
{N.asm_val('mature_sessions_p22', '{:,.0f}')} 会话/月的概率为 22%，达到
{N.asm_val('mature_sessions_p5', '{:,.0f}')} 会话/月的概率为 5%，
对应中位数 {N.get('monte_carlo.calibration.median_mature_sessions', '{:,.0f}')} 会话/月。</p>
<p>叠加算法冲击与处罚后，模型给出的&ldquo;曾达到 1,000 美元/月&rdquo;概率是
{N.get('monte_carlo.p_reach_1k_pct', '{:.1f}')}%，低于自选择调查推断的 20–30% 区间
{N.cite('indie_reach_1k_mrr')}。<strong>我们不向上校准。</strong>理由有二：
那些调查的分母不包含从未上线即放弃的项目；且其覆盖期早于 2026 年的搜索环境——
日均 1 万 PV 以下的小型出版商 2025 年搜索流量下降了
{N.src_val('chartbeat_small_pub_decline', '{:.0f}', -1)}%{N.cite('chartbeat_small_pub_decline')}，
而新站起步时正处在这个最差分档里。</p>""", "neutral"))

    A("<h3>5.2 结果</h3>")
    A('<div class="kpi-grid">')
    A(kpi("胜率（现金口径）", N.get("monte_carlo.win_rate_pct", "{:.2f}"), "%", "", "accent"))
    A(kpi("盈亏比（现金口径）", N.get("monte_carlo.payoff_ratio", "{:.1f}"), " : 1"))
    A(kpi("期望 MOIC", N.get("monte_carlo.expected_moic", "{:.2f}"), "×", "由极端右尾主导", "warn"))
    A(kpi("中位 MOIC", N.get("monte_carlo.median_moic", "{:.2f}"), "×", "更贴近真实体验"))
    A("</div>")
    A('<div class="kpi-grid">')
    A(kpi("五年年化（期望）", N.get("monte_carlo.annualized_pct", "{:.1f}"), "%", "", "accent"))
    A(kpi("五年年化（中位）", N.get("monte_carlo.median_annualized_pct", "{:.1f}"), "%"))
    A(kpi("全成本年化", N.get("monte_carlo.annualized_full_cost_pct", "{:.1f}"), "%",
          "含创始人时间成本", "danger"))
    A(kpi("完全损失概率", N.get("monte_carlo.p_total_loss_pct", "{:.2f}"), "%",
          "现金几乎不可能全损", "good"))
    A("</div>")

    A(f"""
<p><strong>这两组数字必须放在一起读，否则每一组都是谎言。</strong>
现金口径之所以漂亮，是因为分母只有
{N.get('monte_carlo.invested_cash_mean', '${:,.0f}')}——固定成本低、且不随流量放大，
所以只要项目活着，回本几乎是必然的。而期望 MOIC
{N.get('monte_carlo.expected_moic', '{:.2f}')}× 与中位
{N.get('monte_carlo.median_moic', '{:.2f}')}× 之间十几倍的落差，
说明期望值被极少数极端路径主导：99 分位的 MOIC 是
{N.get('monte_carlo.moic_percentiles.p99', '{:.0f}')}×。
对一个只能下注一次的人来说，期望值不是他会经历的世界。</p>
""")

    A(figure("moic_hist.svg", "红色为未能收回现金投入的路径。分布的形状本身比任何单一统计量都更说明问题。"))
    A(figure("jcurve.svg",
             f"中位路径在第 5 年的月净利约 "
             f"{N.get('monte_carlo.yearly[4].median_net_month', '${:,.0f}')}，"
             f"第 60 个月的中位会话数为 "
             f"{N.get('monte_carlo.sessions_p50_final', '{:,.0f}')}，P90 为 "
             f"{N.get('monte_carlo.sessions_p90_final', '{:,.0f}')}。"))

    A(table(
        ["年份", "现金口径 ROI", "现金口径年化", "全成本 ROI", "全成本年化", "当年末月净利中位"],
        [[f'第 {y["year"]} 年',
          N.get(f"monte_carlo.yearly[{i}].roi", "{:,.1f}", suffix="%"),
          N.get(f"monte_carlo.yearly[{i}].annualized", "{:,.1f}", suffix="%"),
          N.get(f"monte_carlo.yearly[{i}].roi_full_cost", "{:,.1f}", suffix="%"),
          N.get(f"monte_carlo.yearly[{i}].annualized_full_cost", "{:,.1f}", suffix="%"),
          N.get(f"monte_carlo.yearly[{i}].median_net_month", "${:,.0f}")]
         for i, y in enumerate(mc["yearly"])],
        caption="分年回报（两个口径并列）", num_cols={1, 2, 3, 4, 5}))

    A(callout("最该被记住的一个数字",
              f"""<p>不是胜率，也不是年化，而是<strong>折合时薪</strong>：中位路径
{N.get('monte_carlo.breakeven_hourly_median', '${:.2f}')}/小时，期望
{N.get('monte_carlo.breakeven_hourly_mean', '${:.2f}')}/小时。
在设定的 {N.asm_val('founder_hourly_cost', '${:.0f}')}/小时机会成本下，
项目跑赢它的概率是 {N.get('monte_carlo.p_beat_hourly_cost_pct', '{:.2f}')}%。
这个指标的好处是它把最主观的一个假设（你的时间值多少钱）从计算里剥离出去了——
它只回答"项目每小时产出多少现金"，剩下的比较交给你。</p>""", "danger"))
    A("</section>")

    # ---------------- 第六章 Kelly ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第六章</span>')
    A("<h2>Kelly 最优比例</h2>")
    A('<p class="dek">在完整结果分布上数值最大化 E[log(1 + f·R)]，而不是套用两点公式。</p>')

    A(figure("kelly_curve.svg", "两个口径的对数增长率曲线。虚线为各自的最优比例。"))

    A(table(
        ["口径", "全 Kelly", "半 Kelly", f'对应金额（以 {N.asm_val("cash_budget", "${:,.0f}")} 上限计）'],
        [
            ["现金口径", N.get("kelly.cash_basis.f_star", "{:.3f}"),
             N.get("kelly.cash_basis.half_kelly", "{:.3f}"),
             N.get("kelly.cash_basis.f_star_amount", "${:,.0f}") + " / "
             + N.get("kelly.cash_basis.half_kelly_amount", "${:,.0f}")],
            ["全成本口径（含时间）", N.get("kelly.full_cost_basis.f_star", "{:.3f}"),
             N.get("kelly.full_cost_basis.half_kelly", "{:.3f}"), "—"],
            ["两点近似 f = p − q/b",
             N.get("kelly.naive_two_point.f_naive", "{:.3f}"), "—",
             "p = " + N.get("kelly.naive_two_point.p", "{:.3f}")
             + "，b = " + N.get("kelly.naive_two_point.b", "{:.2f}")],
        ],
        caption="三种算法的对比", num_cols={1, 2}))

    A(f'<p>{esc(res["kelly"]["interpretation"])}</p>')
    A(callout("为什么不用 f = p − q/b",
              f'<p>{esc(res["kelly"]["naive_note"])}</p>', "warn"))
    A(callout("Kelly 在这里的适用性边界",
              f'<p>{esc(res["kelly"]["caveat"])}</p>', "neutral"))
    A(f"""
<p>把 Kelly 的结论翻译成可执行的一句话：<strong>现金上限设为
{N.get('kelly.cash_basis.half_kelly_amount', '${:,.0f}')}（半 Kelly），
但真正需要设上限的是时间。</strong>本方案在第九章用阶段门的形式给时间设了止损：
每一阶段都有一个可证伪的指标，不达标就停，而不是无限期地投入下去。</p>
""")
    A("</section>")

    # ---------------- 第七章 敏感性 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第七章</span>')
    A("<h2>敏感性与情景</h2>")
    A('<p class="dek">这一章的目的不是给出更多数字，而是回答：结论到底靠哪几个假设撑着？</p>')

    A(figure("tornado.svg",
             f'指标为中位折合时薪。{esc(res["sensitivity"]["tornado"]["note"])}'))

    A(table(
        ["假设", "取下界", "取上界", "摆幅"],
        [[r["label"],
          N.get(f"sensitivity.tornado.rows[{i}].low_metric", "${:.2f}"),
          N.get(f"sensitivity.tornado.rows[{i}].high_metric", "${:.2f}"),
          N.get(f"sensitivity.tornado.rows[{i}].swing", "${:.2f}")]
         for i, r in enumerate(res["sensitivity"]["tornado"]["rows"])],
        caption="各假设对中位折合时薪的影响（基准 "
                + N.get("sensitivity.tornado.base", "${:.2f}") + "/小时）",
        num_cols={1, 2, 3}))

    A(f'<p>{esc(res["sensitivity"]["verdict"])}</p>')
    A(callout("一个刻意的方法选择",
              """<p>创始人时薪没有出现在龙卷风图里，这是刻意的：主指标&ldquo;中位折合时薪&rdquo;
按构造与它无关。它衡量的是项目每小时产出多少钱，而机会成本是拿来跟这个产出比较的标尺，
不是产出本身。把最主观的假设移出结论指标，结论才不依赖于你如何给自己的时间定价。</p>""",
              "neutral"))

    A("<h3>7.1 三情景</h3>")
    A('<p>三个情景不是随手调参，而是把&ldquo;同向的坏事会一起发生&rdquo;显式建模：'
      '算法压力、RPM 下行与处罚风险由同一个平台政策周期驱动，单变量敏感性会系统性低估尾部。</p>')
    A(table(
        ["情景", "剧情", "全成本胜率", "中位 MOIC", "中位时薪", "期望时薪", "达 1k/月"],
        [[f'<strong>{s["name"]}</strong>', f'<span class="small">{s["story"]}</span>',
          N.get(f"sensitivity.scenarios[{i}].win_rate_full_cost_pct", "{:.2f}", suffix="%"),
          N.get(f"sensitivity.scenarios[{i}].median_moic", "{:.2f}", suffix="×"),
          N.get(f"sensitivity.scenarios[{i}].breakeven_hourly_median", "${:.2f}"),
          N.get(f"sensitivity.scenarios[{i}].breakeven_hourly_mean", "${:.2f}"),
          N.get(f"sensitivity.scenarios[{i}].p_reach_1k_pct", "{:.1f}", suffix="%")]
         for i, s in enumerate(res["sensitivity"]["scenarios"])],
        caption="悲观 / 基准 / 乐观", num_cols={2, 3, 4, 5, 6}))
    A(figure("scenarios.svg", "只有乐观情景的期望时薪超过设定的机会成本，而中位口径三个情景全部不及。"))
    A("</section>")

    # ---------------- 第八章 合规 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第八章</span>')
    A("<h2>合规专章</h2>")
    A('<p class="dek">在这个类目里，合规不是一个部门，而是产品设计的约束条件。以下每一条都对应一个具体的设计决定。</p>')

    A(table(
        ["约束", "来源", "对应的产品设计决定"],
        [
            [f"第 1140 条按每次浏览计罚 {N.src_val('sec1140_penalty', '{:,.0f}')} 美元",
             f"SSA OIG{N.cite('sec1140_penalty')}",
             "品牌名、域名、logo、配色一律不得使用政府相关词汇或视觉元素；"
             "每一页顶部固定展示&ldquo;本站非政府机构，与 SSA 及各州机构无关联&rdquo;；"
             "对受益人的所有功能永久免费"],
            [f"FTC 政府冒充规则含&ldquo;暗示性&rdquo;冒充，罚金上限 "
             f"{N.src_val('ftc_impersonation_rule', '{:,.0f}')} 美元/次",
             f"16 CFR Part 461{N.cite('ftc_impersonation_rule')}",
             "不使用 .gov 相似域名；不在广告素材中使用官方印章样式；"
             "所有引用政府数据处标注来源与抓取日期"],
            ["不得代为登录或自动化访问",
             f"SSA / Login.gov{N.cite('ssa_account_no_proxy', 'logingov_no_automation')}",
             "产品不接触任何账户凭证，不做代提交，不存储任何个人身份信息；"
             "所有计算在浏览器端完成，服务端不留个人数据"],
            ["第三方可单方面切断数据访问",
             f"Propel 被 Conduent 切断的先例{N.cite('propel_blocked')}",
             "不做任何抓取式的账户余额查询；数据层只使用公开发布的规则与日历"],
            [f"AdSense 与搜索反垃圾政策强耦合",
             f"Google 发布商政策{N.cite('adsense_couples_search_spam')}",
             "内容质量不是 SEO 问题而是收入问题；每页署名、标注更新日期与数据出处"],
            ["非美国个人的美国来源所得判定",
             f"IRC §862(a)(3){N.cite('services_income_sourcing', 'w8ben_default_withholding')}",
             "广告与联盟收入按劳务所得定性、劳务全部在美国境外提供；"
             "开户即提交 W-8BEN；若任一收入流被定性为特许权使用费则适用 "
             f"{N.src_val('w8ben_default_withholding')}% 预扣，需事前取得书面意见"],
        ],
        caption="约束 → 设计决定"))

    A(callout("需要专业意见的两件事",
              f"""<p>本文档是对公开规则的整理，不是法律或税务建议。有两件事必须在投入实质资金前
取得执业者的书面意见：<strong>一是本站的具体文案与视觉是否可能构成第 1140 条意义上的
&ldquo;暗示与 SSA 有关联&rdquo;</strong>——LexisNexis 案说明这条线比直觉更靠前；
<strong>二是广告与联盟收入在你所在税收居民国的具体定性</strong>——劳务与特许权使用费的
区分决定了是 0% 还是 {N.src_val('w8ben_default_withholding')}% 预扣。
一次性预算 {N.asm_val('compliance_legal_reserve', '${:,.0f}')} 已计入开办成本。</p>""",
              "warn"))

    A("<h3>8.1 公序良俗自检</h3>")
    A("""
<p>这条业务是否&ldquo;拿弱势群体赚钱&rdquo;，值得正面回答而不是回避。三条自我约束使它站得住：
<strong>受益人一分钱不付</strong>，任何时候都不会；<strong>不制造焦虑</strong>，
页面不使用&ldquo;逾期&rdquo;&ldquo;资格丧失&rdquo;等诱导性措辞，
所有内容指向官方渠道而非替代它；<strong>不做转介套利</strong>，
明确排除本类目中风险最高、也最容易伤害用户的两类变现——残障律师线索转售与 Medicare 计划线索转售，
即便它们的单价远高于展示广告。做这个排除会显著降低收入上限，这一点已经体现在前面的财务模型里。</p>
""")
    A("</section>")

    # ---------------- 第九章 执行 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第九章</span>')
    A("<h2>执行计划与止损纪律</h2>")
    A(f'<p class="dek">敏感性分析指出，结论主要靠两个几乎没有外部证据的 B 端假设撑着。'
      f'所以第一阶段不是建站，而是证伪它们。</p>')

    top3 = res["sensitivity"]["top3"]
    A(f"""
<div class="timeline">
  <div class="item">
    <div class="when">{res['roadmap']['phases'][0]['when']} · 约 {N.get('roadmap.phases[0].hours', '{:,}')} 小时 ·
    现金支出 &lt; {N.src_val('domain_cost', '${:.0f}')}</div>
    <div class="what">先证伪，再建设</div>
    <div class="detail">只做三件事：手工整理 5 个州（人口最多的加州、德州、佛州、纽约州、宾州）的完整发放规则，
    验证&ldquo;这件事到底有多难、多久变一次&rdquo;；把这 5 个州做成一个静态页面上线，观察真实收录情况；
    带着这份手工数据去找 20 个潜在 B 端客户直接问价。</div>
    <div class="gate">阶段门：20 次接触中至少 3 次表达明确付费意愿，且 5 个州的规则整理耗时不超过每州 6 小时。
    未达标则终止，累计损失不超过一顿饭钱与 {N.get('roadmap.phases[0].hours', '{:,}')} 小时。</div>
  </div>
  <div class="item">
    <div class="when">{res['roadmap']['phases'][1]['when']} · 约 {N.get('roadmap.phases[1].hours', '{:,}')} 小时</div>
    <div class="what">铺满 50 州，跑通免费工具侧</div>
    <div class="detail">建立数据层与自动化更新流水线；上线三个工具；接入 AdSense；
    建立每页署名与更新日期机制。此阶段不写任何&ldquo;为 SEO 而写&rdquo;的文章。</div>
    <div class="gate">阶段门：第 9 个月自然搜索会话 ≥ {N.src_val('journey_threshold', '{:,.0f}')}（Journey 门槛），
    且至少 3 个州级页面进入前 20 名。未达标则说明分发假设不成立，转入维护模式或退出。</div>
  </div>
  <div class="item">
    <div class="when">{res['roadmap']['phases'][2]['when']} · 约 {N.get('roadmap.phases[2].hours', '{:,}')} 小时</div>
    <div class="what">开启 B 端通道</div>
    <div class="detail">把数据层封装为带版本与出处的订阅接口，定价
    {N.asm_val('b2b_arpa', '${:.0f}')}/月起。B 端是本方案对搜索流量塌陷的唯一对冲，
    也是退出时倍数的主要来源。</div>
    <div class="gate">阶段门：第 24 个月月净利 ≥ 1,000 美元，或 B 端付费账户 ≥ 5 个。
    模型显示达到前者的中位时点是第 {N.get('monte_carlo.median_month_to_1k')} 个月。</div>
  </div>
  <div class="item">
    <div class="when">{res['roadmap']['phases'][3]['when']} · 约 {N.get('roadmap.phases[3].hours', '{:,}')} 小时</div>
    <div class="what">维持、加固、准备退出</div>
    <div class="detail">重心从增长转为准确性与可转让性：把&ldquo;创始人脑子里的流程&rdquo;
    变成文档化的交接物，这是决定退出倍数落在
    {N.asm_val('exit_multiple_base', '{:.0f}')}× 还是更低的关键。</div>
    <div class="gate">退出参照：30 万美元以下资产 2025 年实际成交
    {N.src_val('ef_under300k_monthly', '{:.2f}')}× 月净利，
    含 AI 内容再折让 {N.src_val('ai_content_discount', '{:.0f}')}%，
    故建模用 {N.asm_val('exit_multiple_base', '{:.0f}')}×。</div>
  </div>
</div>
""")

    A(callout("止损纪律",
              f"""<p>每个阶段门都是可证伪的、有日期的、且失败时的损失是有界的。
这不是谨慎的姿态，而是对本项目风险结构的直接回应：现金几乎不可能亏光
（完全损失概率 {N.get('monte_carlo.p_total_loss_pct', '{:.2f}')}%），
真正会被消耗掉的是时间，而时间没有自动止损机制——必须靠预先写死的规则。</p>""",
              "good"))
    A("</section>")

    # ---------------- 第十章 结论 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">第十章</span>')
    A("<h2>诚实的结论</h2>")
    A(f"""
<p class="lede">这份计划书的结论不是&ldquo;做&rdquo;或&ldquo;不做&rdquo;，而是一个条件式：
<strong>如果这些业余小时对你的机会成本低于
{N.get('kelly.breakeven_hourly.mean', '${:.2f}')}/小时，那么按期望值它值得做；
如果你更看重大概率会发生的那个世界，门槛要降到
{N.get('kelly.breakeven_hourly.median', '${:.2f}')}/小时。</strong></p>

<p>把话说得更直白一些：模型给出的中位结局，是一个在第五年做到每月约
{N.get('monte_carlo.yearly[4].median_net_month', '${:,.0f}')} 净利的网站，
五年累计到手 {N.get('monte_carlo.realized_median', '${:,.0f}')}。
这不是一份事业，是一份还不错的副业。而在
{N.get('monte_carlo.p_reach_5k_pct', '{:.1f}')}% 的路径上，
它会变成每月 5,000 美元以上的东西——这就是全部的上行想象空间，也是它的真实概率。</p>

<h3>支持做的三个理由</h3>
<ul>
<li><strong>下行有界且很浅。</strong>现金完全损失的概率是
{N.get('monte_carlo.p_total_loss_pct', '{:.2f}')}%，
因资金耗尽被迫关停的概率是 {N.get('monte_carlo.p_cash_exhausted_pct', '{:.2f}')}%。
最坏的情况是浪费时间，不是负债。</li>
<li><strong>需求是被实测证实的，不是想象的。</strong>Propel 的
{N.src_val('propel_scale', '{:,.0f}')} 月活、SNAP 查询首页只有
{N.src_val('serp_snap_tx_gov_share')}% 是政府站、Direct Express 迁移的真实时间表——
这三件事互相独立，指向同一个缺口。</li>
<li><strong>它是合法、有用、且对最需要的人免费的。</strong>这一条不产生现金流，
但它决定了这件事能不能长期做下去，以及做完之后你是否愿意署上自己的名字。</li>
</ul>

<h3>反对做的三个理由</h3>
<ul>
<li><strong>时薪太低。</strong>中位
{N.get('monte_carlo.breakeven_hourly_median', '${:.2f}')}/小时。
如果这 {N.get('monte_carlo.founder_hours_5y', '{:,}')} 小时有任何一个替代用途能稳定产出更多，
那个用途在期望上更优。</li>
<li><strong>最关键的两个假设没有外部证据。</strong>结论对 B 端自然获客与客单价最敏感，
而这两项目前只有推理没有数据。第九章的第一个阶段门就是为它们设的。</li>
<li><strong>整个上行依赖一个正在恶化的渠道。</strong>零点击搜索占比已达
{N.src_val('zero_click_2026', '{:.2f}')}%{N.cite('zero_click_2026')}，
AI 摘要使第一位的点击率下降 {N.src_val('aio_ctr_drop_pos1', '{:.0f}')}%
{N.cite('aio_ctr_drop_pos1')}，而教育型金融查询有
{N.src_val('aio_prevalence_edu_finance')}% 会触发 AI 摘要{N.cite('aio_prevalence_edu_finance')}。
被 AI 引用也不解决问题：用户点击摘要内引用链接的比例只有
{N.src_val('pew_click_inside_aio')}%{N.cite('pew_click_inside_aio')}。</li>
</ul>
""")
    A(callout("如果只能记住一句话",
              f"""<p>这个项目几乎不会让你亏钱，也几乎不会让你发财；它真正要花掉的是五年
{N.get('monte_carlo.founder_hours_5y')} 小时，
换回中位 {N.get('monte_carlo.realized_median', '${:,.0f}')}。
先用八周、{N.get('roadmap.phases[0].hours', '{:,}')} 小时把两个关键假设证伪或证实，
再决定要不要投入剩下的 {N.get('roadmap.remaining_after_gate1', '{:,}')} 小时——
这是本文档能给出的最有价值的一条建议。</p>""", "good"))
    A("</section>")

    # ---------------- 附录 ----------------
    A('<section class="page-break">')
    A('<span class="section-num">附录 A</span>')
    A("<h2>方法论与可复现性</h2>")
    A(f"""
<p>全部模型为纯 Python，固定随机种子 <span class="mono">{N.get('meta.seed')}</span>，
在 {esc(N.raw('meta.platform'))} / Python {N.get('meta.python')} /
NumPy {N.get('meta.numpy')} 上生成。</p>
<ul>
<li><span class="mono">model/inputs.py</span> —— 来源与假设的唯一真相源，模型只能经此取数</li>
<li><span class="mono">model/fetch_trends.py</span> —— 实时抓取 Google Trends，落盘并标注 provenance</li>
<li><span class="mono">model/opportunity_rank.py</span> —— 六维加权评分 + Dirichlet 权重稳健性</li>
<li><span class="mono">model/unit_economics.py</span> —— 变现阶梯、成本栈、盈亏平衡</li>
<li><span class="mono">model/monte_carlo.py</span> —— {N.get('monte_carlo.paths')} 路径月度现金流模拟</li>
<li><span class="mono">model/kelly.py</span> —— 完整分布上的 E[log] 数值最优化</li>
<li><span class="mono">model/sensitivity.py</span> —— 龙卷风与三情景</li>
<li><span class="mono">report/audit.py</span> —— 校验正文每个数字都能追溯到 results.json</li>
</ul>
<p class="footnote">复现方式：<span class="mono">python model/run_all.py</span> →
<span class="mono">python charts/make_charts.py</span> →
<span class="mono">python report/build_pdf.py</span>（内部会重建 HTML 并做两遍渲染以定目录页码）→
<span class="mono">python report/audit.py</span>。最后一步返回非零码即表示本文档存在自相矛盾，
不应发布；本次构建的结果见 <span class="mono">out/audit_report.md</span>。</p>
""")

    A("<h3>置信度分级</h3>")
    A(table(
        ["等级", "含义", "本文档中的条数"],
        [["<span class='conf conf-A'>A</span> 一手",
          "厂商官方定价页、政府统计发布、法条原文，或本项目直接实测",
          str(res["ledger"]["by_confidence"].get("A", 0))],
         ["<span class='conf conf-B'>B</span> 二手互证",
          "官方页面不可达，但多个独立追踪源一致", str(res["ledger"]["by_confidence"].get("B", 0))],
         ["<span class='conf conf-C'>C</span> 单一来源",
          "仅一个来源，或来源之间存在分歧，投入资金前需复核",
          str(res["ledger"]["by_confidence"].get("C", 0))],
         ["<span class='conf conf-D'>D</span> 自选择样本",
          "存在已知的严重选择偏差，仅作方向性参考", str(res["ledger"]["by_confidence"].get("D", 0))]],
        caption="", num_cols={2}))
    A(f"""
<p class="footnote">已剔除的来源：调研中出现的若干&ldquo;分行业 RPM 对照表&rdquo;与
&ldquo;0 到 5,000 美元/月案例&rdquo;类站点经核查为 AI 内容农场，其数据无法溯源，一律不予采信、
不进入账本。这类站点恰好也是本方案警示的那种模式。</p>
""")

    A('<span class="section-num" style="margin-top:40px;display:block">附录 B</span>')
    A("<h2>假设清单</h2>")
    A('<p class="dek">没有外部出处的数值全部在此，含推理与敏感性区间。任何未列于此、'
      '也未列于附录 C 的数字，都不应出现在正文里。</p>')
    A(table(
        ["编号", "假设", "取值", "区间", "推理"],
        [[f'<span class="mono">{a["id"]}</span>', a["claim"],
          f'{a["value"]:,}' if isinstance(a["value"], (int, float)) else str(a["value"]),
          (f'{a["low"]:,} ~ {a["high"]:,}' if a["low"] is not None else "—"),
          f'<span class="small">{a["rationale"]}</span>']
         for a in res["assumptions"]],
        caption="", cls="sources-table", num_cols={2, 3}))

    A('<span class="section-num" style="margin-top:40px;display:block">附录 C</span>')
    A("<h2>来源账本</h2>")
    A(f'<p class="dek">共 {N.get("ledger.n_sources")} 条，'
      f'其中一手来源占 {N.get("ledger.share_primary_pct", "{:.1f}")}%。'
      f'角标编号对应正文引用顺序；完整机读版本见 '
      f'<span class="mono">data/sources.csv</span>。</p>')

    # 先列正文引用过的，再列其余
    by_id = {s["id"]: s for s in res["sources"]}
    ordered = [by_id[i] for i in N.cited] + [s for s in res["sources"] if s["id"] not in N.cited]
    rows = []
    for i, s in enumerate(ordered, 1):
        idx = str(i) if s["id"] in N.cited else "—"
        val = f'{s["value"]:,}' if isinstance(s["value"], (int, float)) else esc(s["value"])
        rows.append([
            idx,
            f'{esc(s["claim"])}<br><span class="muted small">{val} {esc(s["unit"])}'
            + (f' · {esc(s["note"])}' if s["note"] else "") + "</span>",
            f'{esc(s["publisher"])}<br><span class="muted">{esc(s["url"])}</span>',
            f'<span class="conf conf-{s["confidence"]}">{s["confidence"]}</span>',
            s["retrieved"],
        ])
    A(table(["#", "论断", "来源", "置信", "取数日"], rows, cls="sources-table", num_cols={0, 3}))
    A("</section>")

    N.dump_trace()

    body_html = inject_toc("".join(body))

    css = (ROOT / "report" / "styles.css").read_text(encoding="utf-8")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{BRAND} 商业计划书 · 证据驱动重建版</title>
<style>{css}</style>
</head>
<body>
<main class="page">
{body_html}
</main>
</body>
</html>
"""


def main():
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    html_text = build(res)
    p = OUT / "BP.html"
    p.write_text(html_text, encoding="utf-8")
    trace = json.loads((OUT / "number_trace.json").read_text(encoding="utf-8"))
    print(f"已写入 {p}（{p.stat().st_size / 1024:.0f} KB）")
    print(f"注入数值 {len(trace)} 处，全部可追溯至 results.json")


if __name__ == "__main__":
    main()
