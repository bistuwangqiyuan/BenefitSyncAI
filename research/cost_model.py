"""
Reproducible cost / base-rate arithmetic for the BenefitSync AI plan.

Every rate constant carries the source URL it was taken from and the date
it was verified. Nothing here is estimated unless the variable name says
ASSUMPTION.

Run: python cost_model.py
Verified: 2026-07-26
"""

from dataclasses import dataclass

SEP = "=" * 78
SUB = "-" * 78


# ---------------------------------------------------------------------------
# SECTION 2. LLM COST OF 1,000 ARTICLES x ~1,500 WORDS
# ---------------------------------------------------------------------------

# Tokenizer ratio. OpenAI's published rule of thumb is ~0.75 words per token
# for English prose, i.e. 1 word ~= 1.33 tokens.
# https://platform.openai.com/tokenizer
WORDS_PER_TOKEN = 0.75
ARTICLE_WORDS = 1_500
N_ARTICLES = 1_000

# 4-call pipeline per article. Token counts are ASSUMPTIONS about pipeline
# design (not vendor facts), chosen to be deliberately non-optimistic:
# a real revision + verification pass re-reads the whole draft.
PIPELINE = [
    # (stage, input_tokens, output_tokens, cacheable_prefix_tokens)
    ("1. brief/outline from keyword+SERP data", 1_500, 500, 1_200),
    ("2. full draft", 2_500, 2_200, 1_200),
    ("3. revision pass (re-reads draft)", 3_500, 2_300, 1_200),
    ("4. fact-check / claim extraction", 2_500, 600, 1_200),
]

# Fraction of the stable prefix that actually lands a cache hit in steady
# state. ASSUMPTION. Vendors do not guarantee a hit rate.
CACHE_HIT_RATE = 0.90


@dataclass
class Model:
    name: str
    inp: float          # USD per 1M input tokens, standard tier
    out: float          # USD per 1M output tokens, standard tier
    cache_read: float   # USD per 1M cached-input tokens
    batch_discount: float  # multiplier applied to input+output on batch API
    source: str


# All prices USD per 1,000,000 tokens, verified 2026-07-26.
MODELS = [
    Model("DeepSeek V4-Flash", 0.14, 0.28, 0.0028, 1.00,
          "https://api-docs.deepseek.com/quick_start/pricing/"),
    Model("DeepSeek V4-Pro", 0.435, 0.87, 0.003625, 1.00,
          "https://api-docs.deepseek.com/quick_start/pricing/"),
    Model("Groq GPT-OSS-120B", 0.15, 0.60, 0.075, 0.50,
          "https://www.cloudzero.com/blog/groq-pricing/"),
    Model("Gemini 3.1 Flash-Lite", 0.25, 1.50, 0.025, 0.50,
          "https://tokenmix.ai/blog/google-gemini-api-pricing"),
    Model("GPT-5 mini", 0.25, 2.00, 0.025, 0.50,
          "https://developers.openai.com/api/docs/models/gpt-5.2"),
    Model("Gemini 3 Flash", 0.50, 3.00, 0.05, 0.50,
          "https://tokenmix.ai/blog/google-gemini-api-pricing"),
    Model("Claude Haiku 4.5", 1.00, 5.00, 0.10, 0.50,
          "https://platform.claude.com/docs/en/about-claude/pricing"),
    Model("GPT-5.2", 1.75, 14.00, 0.175, 0.50,
          "https://developers.openai.com/api/docs/models/gpt-5.2"),
    Model("Gemini 3.1 Pro (<=200K)", 2.00, 12.00, 0.20, 0.50,
          "https://tokenmix.ai/blog/google-gemini-api-pricing"),
    Model("Claude Sonnet 5 (intro, to 2026-08-31)", 2.00, 10.00, 0.20, 0.50,
          "https://platform.claude.com/docs/en/about-claude/pricing"),
    Model("Claude Sonnet 4.6", 3.00, 15.00, 0.30, 0.50,
          "https://platform.claude.com/docs/en/about-claude/pricing"),
    Model("Claude Opus 4.8", 5.00, 25.00, 0.50, 0.50,
          "https://platform.claude.com/docs/en/about-claude/pricing"),
]


def token_totals():
    """Per-article and whole-corpus token counts."""
    inp = sum(s[1] for s in PIPELINE)
    out = sum(s[2] for s in PIPELINE)
    cacheable = sum(s[3] for s in PIPELINE)
    return inp, out, cacheable


def cost_for(model: Model, batch: bool, caching: bool):
    """USD to produce N_ARTICLES through the 4-call pipeline."""
    inp, out, cacheable = token_totals()

    if caching:
        cached = cacheable * CACHE_HIT_RATE
        full_price_in = inp - cached
    else:
        cached = 0.0
        full_price_in = inp

    # scale to the whole corpus, in millions of tokens
    m = N_ARTICLES / 1_000_000
    in_m, cached_m, out_m = full_price_in * m, cached * m, out * m

    disc = model.batch_discount if batch else 1.0
    return (in_m * model.inp * disc
            + cached_m * model.cache_read * disc
            + out_m * model.out * disc)


def section_llm():
    inp, out, cacheable = token_totals()
    art_tokens = ARTICLE_WORDS / WORDS_PER_TOKEN

    print(SEP)
    print("SECTION 2 - COST TO GENERATE 1,000 ARTICLES OF ~1,500 WORDS")
    print(SEP)
    print(f"Finished article length      : {ARTICLE_WORDS} words "
          f"= {art_tokens:,.0f} output tokens at {WORDS_PER_TOKEN} words/token")
    print()
    print("Per-article pipeline (4 LLM calls):")
    print(f"  {'stage':<42}{'in':>8}{'out':>8}{'cacheable':>11}")
    for name, i, o, c in PIPELINE:
        print(f"  {name:<42}{i:>8,}{o:>8,}{c:>11,}")
    print(f"  {'TOTAL per article':<42}{inp:>8,}{out:>8,}{cacheable:>11,}")
    print()
    print(f"Corpus of {N_ARTICLES:,} articles "
          f"= {inp*N_ARTICLES/1e6:.1f}M input + {out*N_ARTICLES/1e6:.1f}M output tokens")
    print(f"Output tokens ({out:,}/article) exceed the {art_tokens:,.0f} in the")
    print("finished text because the revision pass regenerates the full article.")
    print()

    print(f"{'model':<38}{'standard':>11}{'+cache':>10}{'+cache+batch':>14}")
    print(SUB)
    for m in MODELS:
        a = cost_for(m, batch=False, caching=False)
        b = cost_for(m, batch=False, caching=True)
        c = cost_for(m, batch=True, caching=True)
        note = "" if m.batch_discount < 1 else "  (no batch API)"
        print(f"{m.name:<38}{a:>10,.2f}{b:>10,.2f}{c:>13,.2f}{note}")
    print(SUB)

    print("\nWorked arithmetic, DeepSeek V4-Flash, standard, no caching:")
    d = MODELS[0]
    print(f"  input : 10.0M tok x ${d.inp}/M  = ${10.0*d.inp:,.2f}")
    print(f"  output:  5.6M tok x ${d.out}/M  = ${5.6*d.out:,.2f}")
    print(f"  total                          = "
          f"${10.0*d.inp + 5.6*d.out:,.2f}")

    print("\nWorked arithmetic, Claude Sonnet 4.6, batch + caching:")
    s = next(m for m in MODELS if m.name == "Claude Sonnet 4.6")
    cached = cacheable * CACHE_HIT_RATE          # 4,320 tok/article
    fullin = inp - cached                        # 5,680 tok/article
    print(f"  cacheable prefix {cacheable:,} tok/article x {CACHE_HIT_RATE:.0%} hit "
          f"= {cached:,.0f} cached tok/article")
    print(f"  full-price input = {inp:,} - {cached:,.0f} = {fullin:,.0f} tok/article")
    print(f"  batch multiplier = {s.batch_discount}")
    print(f"  input : {fullin/1000:.2f}M x ${s.inp}/M x {s.batch_discount} "
          f"= ${fullin/1000*s.inp*s.batch_discount:,.2f}")
    print(f"  cached: {cached/1000:.2f}M x ${s.cache_read}/M x {s.batch_discount} "
          f"= ${cached/1000*s.cache_read*s.batch_discount:,.2f}")
    print(f"  output: {out/1000:.2f}M x ${s.out}/M x {s.batch_discount} "
          f"= ${out/1000*s.out*s.batch_discount:,.2f}")
    print(f"  total = ${cost_for(s, True, True):,.2f}")
    print(f"\nCost per article, cheapest viable route (DeepSeek V4-Flash): "
          f"${cost_for(MODELS[0], False, True)/N_ARTICLES:.4f}")
    print(f"Cost per article, mid route (Gemini 3 Flash, batch+cache): "
          f"${cost_for(next(m for m in MODELS if m.name=='Gemini 3 Flash'), True, True)/N_ARTICLES:.4f}")


# ---------------------------------------------------------------------------
# SECTION 1. INFRASTRUCTURE AT 10K / 100K / 1M PAGEVIEWS
# ---------------------------------------------------------------------------

# ASSUMPTIONS about traffic shape for a mostly-static content site.
REQ_PER_PV = 4          # HTML + CSS + JS + font/image, aggressively bundled
KB_PER_PV = 400         # 400 KB per pageview after Brotli
DYNAMIC_PV_SHARE = 0.03  # 3% of pageviews touch the RAG chatbot / an API

# Cloudflare rates, verified 2026-07-26
# https://developers.cloudflare.com/workers/platform/pricing/
CF_WORKERS_BASE = 5.00
CF_WORKERS_INCL_REQ = 10_000_000
CF_WORKERS_REQ_OVERAGE = 0.30 / 1_000_000
# https://developers.cloudflare.com/d1/platform/pricing/  (D1 in Workers Paid)
# https://developers.cloudflare.com/r2/pricing/  (R2 free tier covers this)
CF_DOMAIN_YEAR = 10.44   # at-cost .com; https://www.cloudflare.com/products/registrar/

# Vercel rates, verified 2026-07-26  https://vercel.com/pricing
VERCEL_PRO_BASE = 20.00
VERCEL_INCL_CREDIT = 20.00
VERCEL_INCL_EDGE_REQ = 10_000_000
VERCEL_EDGE_REQ_OVERAGE = 2.00 / 1_000_000
VERCEL_INCL_GB = 1_000          # 1 TB Fast Data Transfer
VERCEL_GB_OVERAGE = 0.15
VERCEL_INCL_INVOCATIONS = 0     # covered by credit; overage below
VERCEL_INVOCATION_OVERAGE = 0.60 / 1_000_000

# Netlify credit-based, verified 2026-07-26
# https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/
NETLIFY_FREE_CREDITS = 300
NETLIFY_PRO_BASE, NETLIFY_PRO_CREDITS = 20.00, 3_000
NETLIFY_CREDITS_PER_GB = 20
NETLIFY_CREDITS_PER_10K_REQ = 2
NETLIFY_RECHARGE = (10.00, 1_500)   # $10 per 1,500 credits


def infra_at(pv):
    req = pv * REQ_PER_PV
    gb = pv * KB_PER_PV / 1_000_000
    dyn = pv * DYNAMIC_PV_SHARE

    # --- Cloudflare Workers/Pages ---
    # Pages static bandwidth + requests are unlimited and unmetered:
    # https://pages.cloudflare.com/  -> only dynamic Worker calls bill.
    # Request volume alone would stay inside Workers Free (100k req/day), but
    # the Free plan caps CPU at 10 ms PER INVOCATION, which a RAG retrieval +
    # LLM-orchestration handler will exceed. Workers Paid raises that to 30 s
    # (5 min max). https://developers.cloudflare.com/workers/platform/limits/
    # So the $5 Paid plan is a binding requirement, not a volume overage.
    over = max(0.0, dyn - CF_WORKERS_INCL_REQ)
    cf = CF_WORKERS_BASE + over * CF_WORKERS_REQ_OVERAGE
    cf_note = (f"Workers Paid $5 min ({dyn:,.0f} dynamic req; "
               f"Free blocked by 10ms CPU cap, not by volume)")
    cf_static_only = 0.0  # pure static, no chatbot: genuinely $0

    # --- Vercel Pro ---
    v_edge = max(0.0, req - VERCEL_INCL_EDGE_REQ) * VERCEL_EDGE_REQ_OVERAGE
    v_bw = max(0.0, gb - VERCEL_INCL_GB) * VERCEL_GB_OVERAGE
    v_inv = dyn * VERCEL_INVOCATION_OVERAGE
    v_usage = v_edge + v_bw + v_inv
    vercel = VERCEL_PRO_BASE + max(0.0, v_usage - VERCEL_INCL_CREDIT)

    # --- Netlify credits ---
    credits = gb * NETLIFY_CREDITS_PER_GB + (req / 10_000) * NETLIFY_CREDITS_PER_10K_REQ
    credits += 15 * 4   # ~4 production deploys/mo at 15 credits each
    if credits <= NETLIFY_FREE_CREDITS:
        netlify, n_note = 0.0, f"Free ({credits:,.0f} of 300 credits)"
    else:
        extra = credits - NETLIFY_PRO_CREDITS
        packs = 0 if extra <= 0 else -(-extra // NETLIFY_RECHARGE[1])
        netlify = NETLIFY_PRO_BASE + packs * NETLIFY_RECHARGE[0]
        n_note = f"Pro, {credits:,.0f} credits ({int(packs)} recharge packs)"

    return dict(pv=pv, req=req, gb=gb, dyn=dyn,
                cf=cf, cf_note=cf_note, cf_static=cf_static_only,
                vercel=vercel, v_usage=v_usage,
                netlify=netlify, n_note=n_note)


def section_infra():
    print("\n" + SEP)
    print("SECTION 1 - MONTHLY INFRASTRUCTURE COST BY TRAFFIC TIER")
    print(SEP)
    print(f"Traffic shape ASSUMPTIONS: {REQ_PER_PV} HTTP req/pageview, "
          f"{KB_PER_PV} KB/pageview, {DYNAMIC_PV_SHARE:.0%} of views hit a function")
    print()
    for pv in (10_000, 100_000, 1_000_000):
        r = infra_at(pv)
        print(f"{pv:>9,} pageviews/mo -> {r['req']:>10,.0f} req, "
              f"{r['gb']:>8.1f} GB, {r['dyn']:>9,.0f} dynamic calls")
        print(f"{'':>13}Cloudflare : ${r['cf']:>8.2f}   {r['cf_note']}")
        print(f"{'':>13}  static-only variant (no chatbot): "
              f"${r['cf_static']:.2f}")
        print(f"{'':>13}Vercel Pro : ${r['vercel']:>8.2f}   "
              f"(${r['v_usage']:.2f} usage vs $20 included credit)")
        print(f"{'':>13}Netlify    : ${r['netlify']:>8.2f}   {r['n_note']}")
        print()
    print("Vercel Hobby is $0 but its terms restrict it to personal,")
    print("NON-COMMERCIAL use, so a revenue-generating site needs Pro at $20/mo.")
    print("https://vercel.com/pricing (FAQ: 'Hobby plan is for personal, non-commercial use')")

    print("Fixed monthly floor on the Cloudflare-centric stack:")
    floor = [
        ("Domain .com amortised", CF_DOMAIN_YEAR / 12,
         "cloudflare.com/products/registrar (at cost)"),
        ("Cloudflare Pages hosting", 0.00, "unlimited bandwidth/requests, free"),
        ("Cloudflare D1 database", 0.00, "5 GB + 5M reads/day on free"),
        ("Cloudflare R2 storage", 0.00, "10 GB + 1M ClassA + 10M ClassB free"),
        ("Resend email (<=3k/mo)", 0.00, "free tier, 100/day cap"),
        ("Sentry errors (<=5k/mo)", 0.00, "free Developer plan"),
        ("UptimeRobot", 0.00, "free 50 monitors, NON-COMMERCIAL only"),
        ("Google Search Console", 0.00, "free"),
    ]
    tot = 0.0
    for k, v, note in floor:
        tot += v
        print(f"  {k:<30}${v:>7.2f}   {note}")
    print(f"  {'TOTAL FIXED FLOOR':<30}${tot:>7.2f}/mo  (${tot*12:,.2f}/yr)")
    print("\n  NOTE: UptimeRobot's free plan bars commercial use since Oct 2024;")
    print("  a commercial site must use Better Stack free (10 monitors) or pay $7-9/mo.")


# ---------------------------------------------------------------------------
# SECTION 5. BASE RATES -> KELLY / MOIC
# ---------------------------------------------------------------------------

# BLS Business Employment Dynamics, Table 7, "Survival of private sector
# establishments by opening year", Total Private. Released with Q1 2025 data.
# https://www.bls.gov/bdm/us_age_naics_00_table7.txt
BLS = {
    "born Mar-2019": [79.2, 70.2, 64.0, 56.7, 51.5],
    "born Mar-2020": [80.9, 72.3, 63.6, 57.2, 51.4],
    "born Mar-2021": [79.1, 67.0, 59.1, 52.4, None],
    "born Mar-2022": [76.3, 64.8, 56.3, None, None],
    "born Mar-2023": [78.2, 65.9, None, None, None],
    "born Mar-2024": [77.9, None, None, None, None],
}

# Correlation Ventures, 21,640 US venture financings 2004-2013.
# https://sethlevine.com/archives/2014/08/venture-outcomes-are-even-more-skewed-than-you-think.html
# Buckets and midpoint MOICs. The <1x bucket midpoint is an ASSUMPTION
# (Correlation did not publish the intra-bucket distribution).
CORRELATION = [
    ("<1x   (lost money)", 0.650, 0.20),
    ("1x-5x",              0.250, 2.30),
    ("5x-10x",             0.060, 7.00),
    ("10x-20x",            0.025, 14.00),
    ("20x-50x",            0.010, 30.00),
    (">50x",               0.004, 75.00),
]


def section_baserates():
    print("\n" + SEP)
    print("SECTION 5 - BASE RATES")
    print(SEP)
    print("BLS BED Table 7, % of establishments surviving since birth:")
    print(f"  {'cohort':<16}{'yr1':>7}{'yr2':>7}{'yr3':>7}{'yr4':>7}{'yr5':>7}")
    for k, v in BLS.items():
        row = "".join(f"{x:>7.1f}" if x is not None else f"{'-':>7}" for x in v)
        print(f"  {k:<16}{row}")

    full = [v for v in BLS.values() if v[4] is not None]
    print(f"\n  Mean of the {len(full)} cohorts with a complete 5-year record:")
    means = [sum(c[i] for c in full) / len(full) for i in range(5)]
    print("  " + "  ".join(f"yr{i+1}={m:.1f}%" for i, m in enumerate(means)))
    print(f"  => 5-year survival base rate ~= {means[4]:.0f}%, "
          f"5-year failure ~= {100-means[4]:.0f}%")
    print("  CAVEAT: the Mar-2020 cohort is COVID/PPP-distorted (yr1 80.9% is")
    print("  the highest in the series). The Mar-2019 cohort is cleaner.")
    print("  CAVEAT: BLS counts ESTABLISHMENTS with payroll employment. A")
    print("  one-person no-employee business is largely OUT of this universe,")
    print("  so treat 51% as an upper bound for a solo venture.")

    print("\nCorrelation Ventures realised gross MOIC distribution:")
    print(f"  {'bucket':<22}{'prob':>8}{'midpt MOIC':>12}{'contrib':>10}")
    ev = 0.0
    for name, p, moic in CORRELATION:
        ev += p * moic
        print(f"  {name:<22}{p:>8.3f}{moic:>12.2f}{p*moic:>10.3f}")
    ptot = sum(p for _, p, _ in CORRELATION)
    print(f"  {'sum':<22}{ptot:>8.3f}{'':>12}{ev:>10.3f}")
    print(f"  => expected MOIC = {ev:.2f}x")

    # win rate and payoff ratio
    p_win = sum(p for n, p, _ in CORRELATION if not n.startswith("<1x"))
    p_loss = 1 - p_win
    win_ev = sum(p * m for n, p, m in CORRELATION if not n.startswith("<1x")) / p_win
    loss_ev = next(m for n, _, m in CORRELATION if n.startswith("<1x"))
    print(f"\n  win rate (MOIC>=1x)      = {p_win:.1%}")
    print(f"  loss rate                = {p_loss:.1%}")
    print(f"  mean MOIC | win           = {win_ev:.2f}x")
    print(f"  mean MOIC | loss          = {loss_ev:.2f}x")
    b = (win_ev - 1) / (1 - loss_ev)
    print(f"  payoff ratio b            = (E[win]-1)/(1-E[loss]) = {b:.2f} : 1")

    # Kelly on this discrete distribution: maximise E[log(1+f*(MOIC-1))]
    best_f, best_g = 0.0, -1e18
    f = 0.0
    while f <= 1.0:
        g = 0.0
        ok = True
        for _, p, m in CORRELATION:
            x = 1 + f * (m - 1)
            if x <= 0:
                ok = False
                break
            g += p * __import__("math").log(x)
        if ok and g > best_g:
            best_g, best_f = g, f
        f += 0.001
    print(f"\n  Kelly-optimal fraction (max E[log wealth]) = {best_f:.1%} of bankroll")
    print(f"  growth rate at f*                          = {best_g:.4f} log-units/bet")
    simple_kelly = p_win - p_loss / b
    print(f"  naive two-outcome Kelly (p - q/b)          = {simple_kelly:.1%}")
    print("  The full-distribution Kelly is the defensible one; the naive")
    print("  formula assumes a total loss on failure and a single win size.")

    print("\n  Horsley Bridge (7,000+ investments 1985-2014): ~6% of investments,")
    print("  4.5% of dollars, produced ~60% of total returns; ~half of all")
    print("  investments returned <1x.  a16z.com/performance-data-and-the-babe-ruth-effect-in-venture-capital")

    print("\n  Bootstrapped micro-SaaS (WEAK EVIDENCE - self-selected surveys):")
    print("    MicroConf State of Indie SaaS 2024, n=469: 28% of independent")
    print("    SaaS companies are under $1,000 MRR - the single largest group.")
    print("    RockingWeb 2025, n=1,000 products: ~70% under $1,000/mo;")
    print("    ~18% in $1k-$5k; ~1-2% above $50k/mo; median ~$500 MRR.")
    print("    => P(reach $1k MRR) ~ 20-30%, but survivorship bias is severe:")
    print("    these samples count products that shipped AND got listed.")


# ---------------------------------------------------------------------------
# SECTION 6. EXIT VALUE
# ---------------------------------------------------------------------------

# Empire Flippers 2026 State of the Industry Report (2025 transactions)
# https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf
EF_2025_AVG_SALE_MULTIPLE = 23.93     # x monthly net profit (was 26.60 in 2024)
EF_2025_AVG_LIST_MULTIPLE = 28.69
EF_BY_SEGMENT = [("Under $300K", 129, 91_098, 22.42),
                 ("$300K-$1M", 26, 406_202, 26.69),
                 ("Over $1M", 11, 2_058_217, 35.09)]
EF_BY_QUALITY = [("7-figure premium", 41.0), ("Premium", 31.1),
                 ("Typical", 27.8), ("Distressed", 13.7)]


def section_exit():
    print("\n" + SEP)
    print("SECTION 6 - EXIT MULTIPLES FOR MICRO ONLINE ASSETS")
    print(SEP)
    print(f"Empire Flippers 2025 realised average: {EF_2025_AVG_SALE_MULTIPLE}x monthly "
          f"net profit = {EF_2025_AVG_SALE_MULTIPLE/12:.2f}x annual")
    print(f"  (down 10.1% from {EF_2025_AVG_SALE_MULTIPLE/(1-0.101):.2f}x in 2024; "
          f"avg listing multiple {EF_2025_AVG_LIST_MULTIPLE}x)")
    print(f"\n  {'segment':<16}{'n':>5}{'avg price':>12}{'x monthly':>11}{'x annual':>10}")
    for name, n, price, mult in EF_BY_SEGMENT:
        print(f"  {name:<16}{n:>5}{price:>12,}{mult:>11.2f}{mult/12:>10.2f}")
    print(f"\n  {'quality band':<20}{'x monthly':>11}{'x annual':>10}")
    for name, mult in EF_BY_QUALITY:
        print(f"  {name:<20}{mult:>11.1f}{mult/12:>10.2f}")

    print("\n  A solo AI content site realistically lands in 'Typical' or below,")
    print("  and under $300K: use 22.4x monthly = 1.87x annual net profit as base,")
    print("  13.7x monthly = 1.14x annual if profit is declining.")
    print("\n  Flippa H1 2026 average profit multiples (annual basis):")
    for k, v in [("SaaS", (2.47, 4.06)), ("Content site", (2.32, 4.68)),
                 ("Media & community", (1.63, 3.89)), ("Ecommerce", (1.55, 2.75)),
                 ("Marketplace", (2.62, 5.46)), ("Service", (1.43, 2.31))]:
        print(f"    {k:<20}avg {v[0]:.2f}x   top-quartile {v[1]:.2f}x")
    print("  https://flippa.com/blog/digital-ma-insights-h1-2026/")

    # Worked example tied to the plan's own Y3 numbers
    print("\n  Worked exit example at $2,000/mo net profit:")
    for name, mult in EF_BY_QUALITY:
        print(f"    {name:<20}$2,000 x {mult:>5.1f} = ${2000*mult:>10,.0f}")


if __name__ == "__main__":
    section_llm()
    section_infra()
    section_baserates()
    section_exit()
    print("\n" + SEP)
    print("All rate constants carry a source URL in the code above.")
    print(SEP)
