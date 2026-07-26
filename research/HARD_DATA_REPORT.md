# Hard Cost & Base-Rate Data — Bootstrapped One-Person AI Business

**Compiled 2026-07-26. All arithmetic reproducible via `cost_model.py` in this folder.**

## Confidence legend

| Flag | Meaning |
|---|---|
| **A — Primary** | Taken from the vendor's own pricing page/docs or a government statistical release that I retrieved directly. |
| **B — Secondary, corroborated** | Official page unreachable; figure agreed across ≥2 independent trackers. |
| **C — Secondary, single source / contested** | One source, or sources disagree. Verify before committing capital. |
| **D — Weak / self-selected** | Survey or convenience sample with known severe bias. Directional only. |

Two structural warnings that apply to the whole document:

1. **Prices verified on one day.** LLM pricing in particular moved repeatedly during 2025–26 (Anthropic has an introductory Sonnet 5 rate expiring 2026-08-31; Verisign raises `.com` wholesale on 2026-11-01; AWS SES changed default plans on 2026-07-21 — five days before this report).
2. **The base rates in §5 do not describe your business.** BLS measures payroll establishments; venture data measures VC-funded equity. A one-person no-employee content business is in neither universe. I say so explicitly in each subsection rather than laundering the numbers.

---

# 1. INFRASTRUCTURE COSTS

## 1.1 Domain registration (.com, annual)

| Registrar | Year 1 | Renewal | Flag | Source |
|---|---|---|---|---|
| Cloudflare Registrar | $10.44 | $10.44 | **C** | [cloudflare.com/products/registrar](https://www.cloudflare.com/products/registrar/) |
| Porkbun | $11.08 | $11.08 | **A** | [porkbun.com/products/domains](https://porkbun.com/products/domains) |
| Namecheap | $5.98 | $13.98 | **C** | trackers only |

Cloudflare states an at-cost model but **publishes no per-TLD price table** on the marketing page — the $10.44 figure is reconstructed as $10.26 Verisign wholesale + $0.18 ICANN fee. One tracker reports $10.46. Treat as **$10.44–$10.46**; the ~2¢ ambiguity is immaterial, the model being at-cost is what matters.

**Forward-looking, material:** Verisign raises `.com` wholesale from $10.26 → $10.97 effective **2026-11-01 04:00 UTC** (+6.9%), lifting Cloudflare to ~$11.15. Multi-year renewal before that date locks the current rate for the full term. Flag **B**. Source: [osir.com/en/blog/verisign-com-price-update-2026](https://osir.com/en/blog/verisign-com-price-update-2026/).

## 1.2 Hosting / edge

### Cloudflare — Flag **A** ([Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Workers limits](https://developers.cloudflare.com/workers/platform/limits/), [Pages](https://pages.cloudflare.com/))

| | Free | Paid ($5/mo minimum) |
|---|---|---|
| Worker requests | 100,000/day | 10M/mo incl., then **$0.30/M** |
| CPU time | **10 ms per invocation** | 30M CPU-ms/mo incl., then **$0.02/M**; 30 s default cap, 5 min max |
| Egress / bandwidth | **no charge, no limit** | no charge, no limit |
| Pages static bandwidth & requests | **unlimited, unmetered** | unlimited |
| Pages builds | 500/mo, 1 concurrent, 20-min timeout | 5,000/mo (Pro $25) |
| Pages projects | 100 per account (not routinely raised) | 100 |

**The binding constraint is CPU, not volume.** 10 ms/invocation on Free is not enough for a RAG handler doing vector retrieval plus LLM orchestration. Cloudflare's own docs note the *average* Worker uses ~2.2 ms, but real work lands at 10–20 ms. So the $5 Paid plan is a **requirement for the chatbot**, not a growth-triggered overage — my cost table reflects this.

### Vercel — Flag **A** ([vercel.com/pricing](https://vercel.com/pricing))

| Meter | Hobby (free) | Pro ($20/user/mo, incl. $20 usage credit) |
|---|---|---|
| Edge requests | 1M/mo | 10M/mo, then **$2/M** |
| Fast Data Transfer | 100 GB/mo | 1 TB/mo, then **$0.15/GB** |
| Function invocations | 1M/mo | then **$0.60/M** |
| Active CPU | 4 hrs/mo | **$0.128/hr** |
| Provisioned memory | 360 GB-hrs/mo | **$0.0106/GB-hr** |
| ISR reads / writes | 1M / 200K | $0.40/M / $4/M |
| Build minutes | not available | $0.014/min (standard) |
| Observability Plus | — | $1.20/M events |

**Hobby is restricted to "personal, non-commercial use"** by Vercel's own FAQ. A revenue-generating site cannot legitimately sit on Hobby — the real floor is **$20/mo**. Default on-demand budget is $200 with optional hard cap.

### Netlify — Flag **A** ([credit-based plans](https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/))

Netlify **replaced metered pricing with credits for all new accounts on 2025-09-04**, and re-rated credits on 2026-04-14. This is the single biggest structural change among the three hosts.

| Plan | Price | Credits/mo | Overage |
|---|---|---|---|
| Free | $0 | 300, **hard limit — sites pause** | none purchasable |
| Personal | $9 | 1,000 | 500 for $5 |
| Pro | $20 | 3,000 (up to 20,000) | 1,500 for $10 |

Credit rates: **bandwidth 20 credits/GB**, **web requests 2 credits/10,000**, compute 10 credits/GB-hour, production deploy 15 credits each, AI inference 180 credits per $1. Pro tiers: 3,000/$20 · 5,000/$33 · 10,000/$63 · 15,000/$95 · 20,000/$126 (rollover at ≥5,000). Unlimited seats on Pro since April 2026.

At 20 credits/GB, **1 GB of bandwidth ≈ $0.133** on Pro — Netlify is now the most expensive of the three for bandwidth-heavy static content.

## 1.3 Database / storage — all Flag **A**

| Service | Free tier | Paid |
|---|---|---|
| **Cloudflare D1** | 5 GB total; 5M rows read/day; 100K rows written/day | 25B rows read/mo + $0.001/M; 50M writes + $1.00/M; 5 GB + **$0.75/GB-mo**. No egress charge. |
| **Cloudflare R2** | 10 GB-mo; 1M Class A; 10M Class B | $0.015/GB-mo; Class A $4.50/M; Class B $0.36/M; **egress free**. Infrequent Access $0.01/GB-mo + $0.01/GB retrieval, 30-day minimum. |
| **Supabase** | 500 MB DB; 5 GB egress; 1 GB storage; 50K MAU; **paused after 1 week idle**, 2 projects max | Pro **$25/mo** + compute. Includes $10 compute credit (one Micro). 8 GB disk then $0.125/GB; 250 GB egress then $0.09/GB; 100 GB storage then $0.0213/GB; 2M edge invocations then $2/M. PITR +$100/mo per 7 days. |
| **Neon** | 100 CU-hrs/project; 0.5 GB/project; 5 GB egress; **always-on**; hitting any limit suspends compute till next month | Launch **$0.106/CU-hr** + **$0.35/GB-mo**; Scale $0.222/CU-hr. No monthly minimum. Scale-to-zero after 5 min. 500 GB egress/project incl., then $0.10/GB. Extra branches $1.50/branch-mo. |
| **Turso** | 5 GB; 100 DBs; 500M rows read/mo; 10M written; 3 GB syncs | Developer **$4.99/mo** (yearly) / $5.99 monthly: 9 GB, 2.5B reads, 25M writes. Scaler $24.92/mo: 24 GB, 100B reads. Pro $416.58/mo. |

Cheapest genuinely-free durable option for a content site: **D1 + R2** (no egress fees anywhere, no idle suspension). Supabase's 1-week idle pause and Neon's hard monthly suspension both make their free tiers unsuitable for production.

## 1.4 Email sending

| Provider | Free | Paid entry | Overage | Flag |
|---|---|---|---|---|
| **Resend** | 3,000/mo, **100/day cap**, 1 domain | Pro **$20/mo** = 50K; $35 = 100K | $0.90/1,000 | **A** ([resend.com/pricing](https://resend.com/pricing)) |
| **Postmark** | 100/mo, permanent | Basic **$15/mo** = 10K; Pro $16.50; Platform $18 | $1.80 / $1.30 / $1.20 per 1,000 | **A** ([postmarkapp.com/pricing](https://postmarkapp.com/pricing)) |
| **AWS SES** | **free tier withdrawn** | à-la-carte **$0.10/1,000** | +$0.12/GB attachments | **A** ([aws.amazon.com/ses/pricing](https://aws.amazon.com/ses/pricing/)) |

**AWS SES changed five days before this report.** From **2026-07-21**, all new SES accounts (and returning accounts idle since 2025-06-01) start on the **Essentials plan at $0.16/1,000** for the first 10M, not the $0.10 à-la-carte rate. You can switch to à-la-carte at any time, but it is no longer the default. The old 3,000-message free tier is gone. Flag **A** ([AWS Messaging blog](https://aws.amazon.com/blogs/messaging-and-targeting/introducing-amazon-simple-email-service-ses-pricing-plans/)).

Postmark restructured in early 2026 from volume tiers to three plans all starting at 10K included. At 100K emails/mo Postmark Basic costs $15 + $162 = **$177** vs Resend **$35** vs SES **$10–16**. Postmark's premium buys transactional deliverability (they refuse marketing mail), not volume.

## 1.5 Monitoring — free tiers

| Service | Free tier | Cheapest paid | Flag |
|---|---|---|---|
| **Sentry** | Developer: **5,000 errors/mo**, 5M spans, 50 replays, 5 GB logs, 1 cron + 1 uptime monitor, 1 user, 30-day retention | Team **$26/mo** annual (50K errors, unlimited users) | **A** ([docs.sentry.io/pricing](https://docs.sentry.io/pricing/)) |
| **Better Stack** | **10 monitors** + heartbeats, 1 status page, **100,000 exceptions/mo**, 5,000 replays, 3 GB logs (3-day) | Responder $29/mo annual; +50 monitors $25/mo | **A** ([betterstack.com/pricing.md](https://betterstack.com/pricing.md)) |
| **UptimeRobot** | 50 monitors, 5-min interval, 1 status page | Solo $7–9/mo; Team $29–38/mo | **A** ([uptimerobot.com/pricing](https://uptimerobot.com/pricing)) |

**UptimeRobot's free plan has barred commercial use since October 2024** (Flag **C** — reported by trackers, not stated on the pricing page I retrieved). For a commercial site the honest free option is **Better Stack (10 monitors)**, whose free exception allowance (100,000/mo) is **20× Sentry's 5,000**.

Sentry overage is tiered PAYG $0.0001875–$0.0003625/error. A single retry storm can burn a month's 5,000-error quota in hours — set a budget cap on day one.

## 1.6 Realistic total monthly infrastructure cost

Traffic-shape assumptions (mine, not vendor facts): **4 HTTP requests/pageview**, **400 KB/pageview** post-Brotli, **3% of pageviews** invoke a function.

| Monthly pageviews | HTTP req | Bandwidth | Cloudflare stack | Vercel Pro | Netlify |
|---|---|---|---|---|---|
| 10,000 | 40K | 4 GB | **$5.00** ($0 static-only) | $20.00 | $0 (148/300 credits) |
| 100,000 | 400K | 40 GB | **$5.00** ($0 static-only) | $20.00 | $20.00 (940 credits) |
| 1,000,000 | 4M | 400 GB | **$5.00** ($0 static-only) | $20.02 | **$60.00** (8,860 credits → 4 recharge packs) |

Cloudflare is flat at $5 across all three tiers because Pages static bandwidth and requests are unmetered and the $5 Workers minimum already covers 10M requests — 333× the dynamic load at 1M pageviews. **Bandwidth is the cost driver that separates the platforms, and Cloudflare simply does not bill it.**

Fixed all-in floor on the Cloudflare stack:

| Line | $/mo |
|---|---|
| `.com` domain amortised | 0.87 |
| Pages hosting | 0.00 |
| D1 + R2 | 0.00 |
| Resend (≤3K emails) | 0.00 |
| Sentry (≤5K errors) | 0.00 |
| Better Stack (10 monitors) | 0.00 |
| Google Search Console | 0.00 |
| Workers Paid (needed for RAG CPU) | 5.00 |
| **TOTAL** | **$5.87/mo ≈ $70/yr** |

This excludes LLM inference (§2) and SEO tooling (§3), which dominate real spend.

---

# 2. LLM API COSTS

## 2.1 Rate card, USD per 1M tokens, verified 2026-07-26

| Model | Input | Cached in | Output | Batch in/out | Flag |
|---|---|---|---|---|---|
| **DeepSeek V4-Flash** | 0.14 | **0.0028** | 0.28 | *no batch API* | **A** |
| **DeepSeek V4-Pro** | 0.435 | 0.003625 | 0.87 | *no batch API* | **A** |
| Groq GPT-OSS-120B | 0.15 | 0.075 | 0.60 | 0.075 / 0.30 | **B** |
| Groq Llama 3.1 8B Instant | 0.05 | — | 0.08 | 0.025 / 0.04 | **B** |
| Groq Llama 3.3 70B | 0.59 | — | 0.79 | 0.295 / 0.395 | **B** |
| Gemini 3.1 Flash-Lite | 0.25 | 0.025 | 1.50 | 0.125 / 0.75 | **B** |
| Gemini 3 Flash | 0.50 | 0.05 | 3.00 | 0.25 / 1.50 | **B** |
| Gemini 3.5 Flash | 1.50 | 0.15 | 9.00 | 0.75 / 4.50 | **B** |
| Gemini 3.1 Pro (≤200K) | 2.00 | 0.20 | 12.00 | 1.00 / 6.00 | **B** |
| Gemini 3.1 Pro (>200K) | 4.00 | 0.40 | 18.00 | 2.00 / 9.00 | **B** |
| GPT-5 mini | 0.25 | 0.025 | 2.00 | 0.125 / 1.00 | **B** |
| GPT-5.2 | 1.75 | 0.175 | 14.00 | 0.875 / 7.00 | **A** |
| GPT-5.4 | 2.50 | — | 15.00 | 1.25 / 7.50 | **C** |
| GPT-5.6 Luna / Terra / Sol | 1.00 / 2.50 / 5.00 | — | 6.00 / 15.00 / 30.00 | 50% off | **C** |
| **Claude Haiku 4.5** | 1.00 | 0.10 | 5.00 | 0.50 / 2.50 | **A** |
| **Claude Sonnet 5** (intro → 2026-08-31) | **2.00** | 0.20 | **10.00** | 1.00 / 5.00 | **A** |
| Claude Sonnet 5 (from 2026-09-01) | 3.00 | 0.30 | 15.00 | 1.50 / 7.50 | **A** |
| Claude Sonnet 4.6 | 3.00 | 0.30 | 15.00 | 1.50 / 7.50 | **A** |
| Claude Opus 4.8 / Opus 5 | 5.00 | 0.50 | 25.00 | 2.50 / 12.50 | **A** |
| Together DeepSeek V4 Pro | 1.74 | 0.20 | 3.48 | — | **A** |
| Together Llama 3.3 70B | 1.04 | — | 1.04 | — | **A** |

Anthropic (`platform.claude.com/docs/en/about-claude/pricing`), DeepSeek (`api-docs.deepseek.com`), Together (`together.ai/pricing`) and OpenAI's GPT-5.2 model page are **primary**. Google's `ai.google.dev` and OpenAI's main pricing page **both timed out repeatedly**, so Gemini and the newer GPT SKUs are corroborated-secondary — verify Gemini before budgeting.

## 2.2 Discount mechanics

- **Batch API — 50% off input and output.** Uniform across OpenAI, Anthropic, Google, and Groq. 24-hour SLA. **DeepSeek has no batch API** — its list price is already below everyone else's batch price.
- **Prompt caching — reads at 10% of base input** at Anthropic, Google and OpenAI (OpenAI's cached rate is exactly 0.1× base). **DeepSeek is the outlier: cache hits are $0.0028 vs $0.14 miss — a 50× discount, not 10×.**
- **Anthropic cache *writes* cost extra**: 1.25× base for a 5-minute TTL, 2× for 1-hour. Caching is only net-positive if the prefix is actually reused; a write-once-read-never cache costs 25% more than not caching.
- **Batch and caching stack.** Groq: 50% × 50% ≈ 25% of on-demand.
- **OpenRouter** adds ~5.5% credit fee with no inference markup (Flag **C**).
- Anthropic **US-only inference data residency costs 1.1×**.

## 2.3 Cost to generate 1,000 articles × ~1,500 words — full arithmetic

**Token conversion.** At OpenAI's published ~0.75 words/token, 1,500 words = **2,000 output tokens** of finished prose.

**Four-call pipeline per article** (design assumptions, deliberately not optimistic — the revision pass re-reads and regenerates the whole draft):

| Stage | Input tok | Output tok | Cacheable prefix |
|---|---|---|---|
| 1. Brief/outline from keyword + SERP data | 1,500 | 500 | 1,200 |
| 2. Full draft | 2,500 | 2,200 | 1,200 |
| 3. Revision pass (re-reads draft) | 3,500 | 2,300 | 1,200 |
| 4. Fact-check / claim extraction | 2,500 | 600 | 1,200 |
| **Per article** | **10,000** | **5,600** | **4,800** |

Output (5,600) is 2.8× the 2,000 tokens in the finished article because stage 3 regenerates the full text and stages 1/4 produce scaffolding you throw away. **Costing only the visible 2,000 tokens understates spend by ~64%.**

**Corpus: 1,000 articles = 10.0M input + 5.6M output tokens.**

### Worked example — DeepSeek V4-Flash, standard rates, no caching

```
input : 10.0M tok × $0.14/M = $1.40
output:  5.6M tok × $0.28/M = $1.57
                      TOTAL = $2.97
```

### Worked example — Claude Sonnet 4.6, batch + caching

```
cacheable prefix   4,800 tok/article × 90% hit rate = 4,320 cached tok/article
full-price input   10,000 − 4,320                   = 5,680 tok/article
batch multiplier                                    = 0.50

input : 5.68M × $3.00/M × 0.5 =  $8.52
cached: 4.32M × $0.30/M × 0.5 =  $0.65
output: 5.60M × $15.00/M × 0.5 = $42.00
                         TOTAL = $51.17
```

### Full comparison, 1,000 articles

| Model | Standard | + caching | + caching + batch |
|---|---|---|---|
| **DeepSeek V4-Flash** | **$2.97** | **$2.38** | $2.38 (no batch) |
| Groq GPT-OSS-120B | $4.86 | $4.54 | **$2.27** |
| DeepSeek V4-Pro | $9.22 | $7.36 | $7.36 (no batch) |
| Gemini 3.1 Flash-Lite | $10.90 | $9.93 | $4.96 |
| GPT-5 mini | $13.70 | $12.73 | $6.36 |
| Gemini 3 Flash | $21.80 | $19.86 | $9.93 |
| Claude Haiku 4.5 | $38.00 | $34.11 | $17.06 |
| Claude Sonnet 5 (intro) | $76.00 | $68.22 | $34.11 |
| Gemini 3.1 Pro | $87.20 | $79.42 | $39.71 |
| GPT-5.2 | $95.90 | $89.10 | $44.55 |
| Claude Sonnet 4.6 | $114.00 | $102.34 | $51.17 |
| Claude Opus 4.8 | $190.00 | $170.56 | $85.28 |

**Cost per article: $0.0024 (DeepSeek V4-Flash) to $0.085 (Opus 4.8).** Even the most expensive frontier route puts 1,000 verified articles under $90 — **LLM generation is not a meaningful cost constraint at this scale.** Assumed cache-hit rate 90% is an assumption; at 0% hit rate the "+caching" column collapses to the "standard" column, a ≤20% swing. The conclusion is insensitive to it.

**The real constraint is not cost.** At 20 hrs/week, 1,000 articles at even 3 minutes of human review each is 50 hours — two and a half weeks of your entire available time, reviewing nothing else. And per Empire Flippers' own 2026 report, commodity AI content is precisely what collapsed content-site multiples (§6).

---

# 3. SEO / OPERATIONS TOOLING

| Tool | Monthly | Annual equiv. | Notes | Flag |
|---|---|---|---|---|
| **Google Search Console** | **$0** | $0 | Own sites only. Non-optional. | **A** |
| **Ahrefs Starter** | **$29** | no annual discount | 50 tracked keywords, 1 project, 10K crawl credits, 1 mo history, 200 reports/mo. **Launched Jan 2026.** | **A** |
| Ahrefs Lite | $129 | $1,290 ($107.50/mo) | 750 keywords, 5 projects, 100K crawl credits, 6 mo history | **A** |
| Ahrefs Standard | $249 | $2,490 | 2,000 keywords, 20 projects, 24 mo history | **A** |
| Ahrefs Advanced / Enterprise | $449 / $1,499 | $4,490 / $17,988 | — | **A** |
| Ahrefs Free (Webmaster Tools) | $0 | $0 | Own sites only | **A** |
| Semrush Pro | $139.95 | $1,407.96 ($117.33/mo) | — | **B** |
| Semrush Guru | $249.95 | $2,499.96 | — | **B** |
| Semrush Business | $499.95 | $4,999.92 | — | **B** |
| **Screaming Frog SEO Spider** | — | **$279/yr** (£199) | Free version capped at 500 URLs. Per-user licence, 1-year term. | **A** |
| **Ubersuggest** | $29 / $49 / $99 | **$290 / $490 / $990 one-time lifetime** | Lifetime pays back in ~10 months | **B** |
| **Keywords Everywhere** | credits | **$10 per 100,000 credits** | Freemium, credit-based | **C** |
| Moz Pro Medium | $179 | $143/mo annual | 30-day trial | **C** |
| SE Ranking Core | $129 | $103.20/mo annual | 14-day trial | **C** |

**Under $50/mo, realistically:** Google Search Console ($0) + Ahrefs Starter ($29) + Keywords Everywhere ($10 per 100K credits) + Screaming Frog free tier (500 URLs) ≈ **$29–39/mo**. Adding Screaming Frog paid takes it to **$52/mo** ($279/yr ÷ 12 = $23.25).

**Ahrefs Starter at $29 is the single most consequential 2026 change** for a solo operator — Semrush has no comparable tier, its cheapest being Pro at $139.95, a 4.8× premium. Note both vendors raised prices sharply in 2025–26: Ahrefs Lite +30% ($99→$129), Standard +39% ($179→$249). Budget for annual increases.

Semrush figures are from trackers agreeing with each other; I could not retrieve `semrush.com/pricing` directly. Flag **B**.

---

# 4. PAYMENT AND TAX

## 4.1 Payment processing — Flag **A** unless noted

| Provider | Model | Fee | Tax liability |
|---|---|---|---|
| **Stripe** | Processor — **you** are merchant of record | **2.9% + 30¢** domestic cards | **Yours** |
| Stripe — international cards | | +1.5% | |
| Stripe — currency conversion | | +1% | |
| Stripe Tax | add-on | +0.5%/transaction | Calculation only — **registration and filing remain yours** |
| Stripe chargeback | | $15 each | Yours |
| **Stripe Managed Payments** | **Stripe as MoR** | **3.5% on top of Payments fees** | Stripe's — indirect tax in 75+ countries |
| **Paddle** | MoR | **5% + 50¢** | Paddle's |
| **Lemon Squeezy** | MoR | **5% + 50¢** | Lemon Squeezy's |

Sources: [stripe.com/pricing](https://stripe.com/pricing), [lemonsqueezy.com/pricing](https://www.lemonsqueezy.com/pricing). Paddle's 5% + 50¢ is Flag **B** (trackers only).

**Stripe Managed Payments is new and under-reported.** At 2.9% + 30¢ + 3.5% = **6.4% + 30¢** it is *more* expensive than Paddle/Lemon Squeezy's 5% + 50¢ above ~$14 ticket size, but keeps you inside Stripe's API. For the plan's **$0.99 price point** the fixed fee dominates catastrophically:

| Provider | Fee on $0.99 | % of revenue | Net |
|---|---|---|---|
| Stripe | $0.33 | **33.2%** | $0.66 |
| Lemon Squeezy / Paddle | $0.55 | **55.6%** | $0.44 |
| Stripe Managed Payments | $0.36 | **36.6%** | $0.63 |

**This is the single most important finding in this section.** The BP's $0.99 tier loses one-third to one-half of gross revenue to payment fees, versus the 11¢ (11%) of combined AWS+Stripe cost the plan currently assumes. A $0.99 one-time price is not viable on card rails. Either raise the entry price to ≥$5, bundle into an annual charge, or monetise via advertising/affiliate instead of micropayments.

## 4.2 Non-US solo founder selling to US customers

### Entity formation — Flag **A** ([docs.stripe.com/atlas/signup](https://docs.stripe.com/atlas/signup))

**Stripe Atlas: $500 one-time.** Covers Delaware C-corp or LLC formation *including* state filing fees, **EIN without requiring a US SSN** (the hardest obstacle for non-US founders), share issuance, Cooley-drafted templates, 83(b) election filed on your behalf within the 30-day window, and **first year of registered agent**. Renews at **$100/yr**.

Ongoing costs Atlas does *not* cover:

| Item | Annual | Flag |
|---|---|---|
| Registered agent (year 2+) | $100 | **A** |
| Delaware franchise tax — LLC | $300 | **C** |
| Delaware franchise tax — C-corp | $400+ | **C** |
| US CPA for a C-corp | $1,500–3,000 | **C** |

5-year total ≈ $2,600–2,800 excluding CPA. A Wyoming LLC runs ~$1,049–1,249 over 5 years. **Atlas is worth it for the EIN-without-SSN path and the 83(b) filing, not for the price.** Note: Atlas issues shares at a $100 FMV, which is wrong if you contribute substantially valuable IP.

Money movement: **Payoneer / Wise** are the standard routes for a non-US person to receive USD. I did not retrieve current fee schedules for either — **gap, not researched.**

### US tax withholding on advertising / affiliate income

This turns on one question, and the answer is favourable but fragile.

**The rule.** A nonresident alien is taxed by the US only on **US-source** income. Sourcing is determined by IRC §§861–865. Two categories are sourced by **opposite tests**:

| Income type | Sourced by | Authority |
|---|---|---|
| **Compensation for services** | **Where the services are performed** | IRC §862(a)(3); Treas. Reg. §1.861-4 |
| **Royalties** (patent, copyright, software) | **Where the property is used** | IRC §861(a)(4); Treas. Reg. §1.861-5 |

Sources: [IRS — Nonresident aliens, sourcing of income](https://www.irs.gov/individuals/international-taxpayers/nonresident-aliens-sourcing-of-income) (Flag **A**), [26 USC §862](https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title26-section862&num=0&edition=prelim) (Flag **A**), [IRS — U.S. withholding agent FAQ](https://irs.gov/businesses/international-businesses/us-withholding-agent-frequently-asked-questions) (Flag **A**).

**Applied to your case.** If you are a non-US individual who writes, hosts, and operates everything from outside the US, with no US employees and no US equipment:

- **Website display-advertising revenue (AdSense etc.) is treated as services income.** Google classifies website AdSense as "Services" in its own tax workflow. Services performed entirely abroad are **foreign-source** under §862(a)(3) → **outside Chapter 3 withholding, no 30% deduction, normally no Form 1042-S**.
- **Affiliate commissions, sponsorships, and membership access** are analysed the same way — services unless the contract separately licenses IP.
- **US customers alone do not create US-source income or ECI.** The residence of your payer, the location of your bank, and the nationality of your audience are all irrelevant to the services test. Only *where you perform the work* matters.
- **If any revenue stream is characterised as a royalty, the answer flips**: royalties are US-source to the extent the IP is used in the US, default **30% withholding** under §1441, reducible by treaty.

**Default rate and treaty relief.** Foreign persons are subject to 30% on US-source FDAP income — interest, dividends, rents, royalties, and compensation for services — imposed on the **gross** amount ([Instructions for Form W-8BEN](https://www.irs.gov/instructions/iw8ben), Flag **A**). **Form W-8BEN** establishes foreign status and claims treaty benefits. Failure to file it triggers withholding at 30% regardless of the underlying analysis.

Treaty rates are in **IRS Publication 515 Table 1** ([tax-treaty-table-1.pdf](https://www.irs.gov/pub/irs-lbi/tax-treaty-table-1.pdf), Rev. May 2023, Flag **A**). For the **US–China** treaty, **copyright royalties (income code 12) are withheld at 10%**, per treaty Article 11(2). Industrial royalties, know-how, patents and film/TV are also 10%.

**Practical W-8BEN mechanics:** if all services are performed abroad, you generally complete only **Line 9** (country of residence). **Line 10** — citing a specific treaty article and rate — is for passive income such as royalties. You need a foreign TIN or US TIN to claim treaty benefits.

> **This is a summary of published IRS rules, not tax advice.** The services-versus-royalty characterisation is the entire ballgame and is fact-specific. Before relying on the foreign-source conclusion for a revenue stream, get a written opinion from a US international tax practitioner. If any part of the work is performed in the US — including owning US-located equipment involved in generating revenue — that portion becomes US-source.

---

# 5. BASE RATES FOR RISK MODELLING

## 5.1 US business survival — BLS Business Employment Dynamics

**Table 7, "Survival of private sector establishments by opening year," Total Private.** Source: [bls.gov/bdm/us_age_naics_00_table7.txt](https://www.bls.gov/bdm/us_age_naics_00_table7.txt). Flag **A** (primary government release; note `bls.gov` blocks automated retrieval, so re-verify manually).

Percent of the original cohort surviving, by years since birth:

| Cohort (year ended March) | Yr 1 | Yr 2 | Yr 3 | Yr 4 | Yr 5 |
|---|---|---|---|---|---|
| 2019 | 79.2 | 70.2 | 64.0 | 56.7 | **51.5** |
| 2020 | 80.9 | 72.3 | 63.6 | 57.2 | **51.4** |
| 2021 | 79.1 | 67.0 | 59.1 | 52.4 | — |
| 2022 | 76.3 | 64.8 | 56.3 | — | — |
| 2023 | 78.2 | 65.9 | — | — | — |
| 2024 | 77.9 | — | — | — | — |
| **Mean of complete cohorts** | **80.1** | **71.2** | **63.8** | **57.0** | **51.5** |

**Headline base rate: ~51% of new US establishments survive 5 years; ~49% fail.** Long-run BLS series (1994–2015 cohorts) puts year-5 survival at 49.8–56.3%, so ~50% is stable across three decades.

**Three caveats that matter more than the number:**

1. **The March-2020 cohort is COVID/PPP-distorted.** Its year-1 survival of 80.9% is the *highest* in the series — pandemic support programmes suppressed exits. The March-2019 cohort is the cleaner reference.
2. **BLS counts *establishments with payroll employment*.** A one-person business with no employees is largely **outside this universe**. Treat 51% as an **upper bound** for a solo venture, not a central estimate.
3. **"Survival" ≠ "earning money."** BLS records continued positive employment, not profitability. A business can survive five years and never pay its founder. This is exactly the "zombie" state the BP's own model assigns 39.9% probability to — and the BLS number cannot distinguish it from success.

## 5.2 Venture-backed seed outcomes (for contrast)

**Correlation Ventures — 21,640 US venture financings, 2004–2013.** Flag **C**: the underlying study was never published directly; all citations trace to Seth Levine's write-up and Correlation's own Medium post. Widely cited but not independently verifiable.

| Realised gross MOIC | Share of financings | Midpoint used | Contribution |
|---|---|---|---|
| <1× (lost money) | 65.0% | 0.20× | 0.130 |
| 1×–5× | 25.0% | 2.30× | 0.575 |
| 5×–10× | 6.0% | 7.00× | 0.420 |
| 10×–20× | 2.5% | 14.00× | 0.350 |
| 20×–50× | 1.0% | 30.00× | 0.300 |
| >50× | 0.4% | 75.00× | 0.300 |
| **Expected MOIC** | | | **2.08×** |

Headline figures: **65% fail to return 1× capital. Only 10% return >5×. Only 4% return >10×.** Correlation did not release the intra-bucket distribution below 1×, so the 0.20× midpoint is **my assumption**; expected MOIC is sensitive to it (a 0.10× midpoint gives 2.01×, a 0.40× midpoint gives 2.21×).

Correlation's later dollar-weighted update: **<4% of capital returned ≥10×; 37% of dollars returned <1×.**

**Horsley Bridge — 7,000+ investments across hundreds of US funds, 1985–2014.** Flag **C** (aggregated data shared privately with a16z; not a public dataset). ~**6% of investments, representing 4.5% of dollars, produced ~60% of total returns.** ~**half of all investments returned <1×.** Home runs in good funds returned ~20×; in great funds ~70×. The **"Babe Ruth effect"**: great funds lose money *more often* than merely good funds, because they take more shots at the tail.

**VenCap — 11,350 startups, 259 funds, 1986–2018.** ~half lost money; **1.1% (121 companies) each returned their entire fund.** Flag **C**.

**AngelList.** Winning early-stage returns fit a power law with **α = 2.42**; after ~5.1 years the distribution crosses **α < 2 (unbounded mean)**, implying broad indexing beats selection at seed. Flag **B** — this one *is* a published paper with SEC-filed supplementary data ([angel.co/pdf/growth.pdf](https://angel.co/pdf/growth.pdf), [SEC filing](https://www.sec.gov/comments/s7-08-19/s70819-7773213-223398.pdf)), based on 684 syndicated investments.

I could not locate a current **Cambridge Associates** benchmark — their data is paywalled to subscribers. **Gap.**

## 5.3 Derived risk metrics from the Correlation distribution

| Metric | Value | Derivation |
|---|---|---|
| Win rate (MOIC ≥ 1×) | **34.9%** | 1 − 0.650 |
| Loss rate | **65.1%** | — |
| Mean MOIC given win | **5.57×** | Σ(p·MOIC)/Σp over winning buckets |
| Mean MOIC given loss | **0.20×** | assumption |
| **Payoff ratio b** | **5.72 : 1** | (5.57 − 1) / (1 − 0.20) |
| Expected MOIC | **2.08×** | Σ p·MOIC |
| **Kelly-optimal fraction** | **17.7%** | argmax_f E[log(1 + f(MOIC−1))] over the full 6-bucket distribution |
| Naive two-outcome Kelly | 23.5% | p − q/b |

**Use 17.7%, not 23.5%.** The naive `p − q/b` formula assumes a *total* loss on failure and a *single* win size. The full-distribution Kelly maximises E[log wealth] across all six buckets and is the defensible figure. Log-growth at f\* = 0.0545 per bet.

**Compare with the BP's current claims:** the plan asserts 22.1% win rate, 4.20:1 payoff, 1.14× expected MOIC. Against the Correlation base rate (34.9% / 5.72:1 / 2.08×) the plan is **more conservative on every axis**. That is defensible — a solo bootstrapped project should not claim VC-portfolio odds — but the plan should say *why* it discounts, rather than presenting the numbers as if derived from the same source.

## 5.4 Bootstrapped solo micro-business base rates — Flag **D**, weak evidence

**You were right to expect this to be poorly sourced. It is. Report it as directional only.**

| Finding | Source | Why it's weak |
|---|---|---|
| **28%** of independent SaaS companies are under **$1,000 MRR** — the single largest group | MicroConf *State of Independent SaaS* 2024, p.34, n=469 | Self-selected survey of founders who chose to respond to a conference's survey |
| **65%** have 1–10 paying customers; over half have <50 | same, p.25 | same |
| Full-time founders grow **30%** faster than part-time | same, p.45 | same — and directly relevant, since you have 20 hrs/week |
| **~70%** earn under $1,000/mo; **18%** in $1K–$5K; **1–2%** above $50K/mo; median **~$500 MRR** | RockingWeb 2025, n=1,000 products | Aggregator study; methodology not independently auditable |
| **95%** reach profitability within 12 months | same | Implausibly high — near-certain selection effect |
| Median time to $1,000/mo: **12–18 months** | same | — |
| **82%** never reach $5,000/mo; **93%** never reach $10,000/mo | same | — |
| 28% of 230 MicroConf *attendees* reported >$100K MRR | Freemius 2025 | **Extreme survivorship bias** — people who pay to attend a conference for successful founders |

**Honest reading:** P(a launched indie project reaches $1,000 MRR) ≈ **20–30%**, conditional on actually shipping. But every one of these samples counts products that **shipped and got listed somewhere**. The denominator excludes abandoned pre-launch projects entirely — the true unconditional rate is materially lower and **is not measured by any source I found**.

No usable published Stripe Atlas cohort data, Indie Hackers revenue distribution, or Gumroad/Product Hunt creator earnings distribution was retrievable. **Gap.** If those matter to the model, the defensible move is a sensitivity band, not a point estimate.

---

# 6. ACQUISITION / EXIT MULTIPLES FOR MICRO ONLINE ASSETS

## 6.1 Empire Flippers — 2026 State of the Industry Report (2025 transactions)

Flag **A** — broker's own published report. [PDF](https://info.empireflippers.com/hubfs/2026%20Lead%20Magnets/2026%20State%20of%20the%20Industry%20Report.pdf).

| Metric | 2024 | 2025 | Change |
|---|---|---|---|
| **Average sale multiple (× monthly net profit)** | 26.60× | **23.93×** | **−10.1%** |
| Average listing multiple | 32.38× | 28.69× | −11.4% |
| Average sale price | $272,038 | $270,803 | −0.5% |
| Avg days on market | 109.5 | 101.8 | −7.0% |
| Avg business age | 6.4 yrs | 5.7 yrs | −12.2% |

**23.93× monthly = 1.99× annual net profit.** Multiples are computed on **trailing-twelve-month average monthly net profit**.

### By deal size — the size premium is large

| Segment | n | % of deals | Avg price | × monthly | **× annual** |
|---|---|---|---|---|---|
| **Under $300K** | 129 | **77.7%** | $91,098 | **22.42×** | **1.87×** |
| $300K–$1M | 26 | 15.7% | $406,202 | 26.69× | 2.22× |
| Over $1M | 11 | 6.6% | $2,058,217 | 35.09× | 2.92× |

### By quality band

| Band | × monthly | × annual |
|---|---|---|
| 7-figure premium | 41.0× | 3.42× |
| Premium | 31.1× | 2.59× |
| **Typical** | **27.8×** | **2.32×** |
| **Distressed** | **13.7×** | **1.14×** |

Empire Flippers' own guidance: *"for any digital business, you will be looking at selling the business 2× to 5× your annual profit."* Their seller FAQ quotes a 20×–60×+ monthly range.

## 6.2 Flippa — H1 2026 Insights Report

Flag **A** — [flippa.com/blog/digital-ma-insights-h1-2026](https://flippa.com/blog/digital-ma-insights-h1-2026/). Multiples are **× annual profit**.

| Asset type | Average | Top quartile | Spread |
|---|---|---|---|
| Marketplace | 2.62× | 5.46× | 2.08× |
| App | 2.47× | 4.06× | 1.64× |
| **SaaS** | **2.47×** | **4.06×** | 1.64× |
| **Content site** | **2.32×** | **4.68×** | **2.02×** |
| Media & community | 1.63× | 3.89× | **2.39×** |
| YouTube | 1.57× | 2.65× | 1.69× |
| Ecommerce | 1.55× | 2.75× | 1.77× |
| Service | 1.43× | 2.31× | 1.62× |

**Buyers are not valuing categories; they are valuing revenue quality within them.** Every category shows top-quartile at ≥1.6× the average, and content shows more than double. Flippa's H1 2026 valuation mix: Ecommerce 30.4%, SaaS 27.1%, Content 13.1%, AI Apps & Tools 3.4% (brand-new transacting category).

By deal size on Flippa: $10K–$100K averages 2.24× (top quartile 5.96×); $100K–$250K 1.85×; $250K–$1M 1.82×; $1M+ 2.50×.

## 6.3 Cross-platform comparison

| Platform | Content sites | SaaS | Newsletters | Flag |
|---|---|---|---|---|
| **Empire Flippers** | 30–42× monthly (2.5–3.5× annual) | 42–72× monthly (3.5–6× annual) | not broken out | **C** |
| **Flippa** | 24–36× monthly (2.0–3.0× annual) | 36–60× monthly (3–5× annual) | not broken out | **C** |
| **Motion Invest** | 30–40× monthly (2.5–3.3× annual) | not offered | not offered | **C** |
| **Acquire.com** (asking, n=615) | 1.8× revenue / **2.9× profit** | 2.6× revenue / **10.7× profit** | — | **B** |

Empire Flippers commands a 15–25% premium over Flippa on comparable assets (vetted buyers, seller-side QA); Motion Invest sits in the middle and buys inventory wholesale before reselling. Acquire.com figures are **asking prices on live listings, not closed transactions** — treat as a ceiling. Bootstrapped SaaS on Acquire/MicroAcquire typically transacts at **3–5× ARR**; AI tools trade at a steep discount of **1–2.5×** on 1,200+ competing listings.

**Newsletters are not separately reported by any broker I found.** Figures circulating at "2–5× annual recurring revenue" are Flag **C** at best. Flippa's "Media & community" at 1.63× average is the closest published proxy. **Gap.**

## 6.4 The structural warning — read this before modelling any exit

Empire Flippers' own 2026 report is blunt about two things directly relevant to an AI-content business:

> Amazon FBA represented 36.1% of all deals sold in 2025, and **display advertising came a distant second at just 13.3%** … *"content sites have become less popular in general. Many known names in the affiliate SEO game have dipped out completely."* … *"As a stand alone business, acquiring these have become inherently more risky than before and have an uncertain future."*

And on SaaS:

> *"AI wounded the content site model deeply where content became an easy to produce commodity, AI is now also coming for the major moat that SaaS could boast about — the difficulty in creating the software itself."* … *"the valuations on the smaller scale SaaS likely will fall"* … most acute in **micro-SaaS under $500,000.**

They also state the 2020–22 multiple environment will not return absent multiple simultaneous black-swan events, and that current levels are a return to pre-COVID normal rather than a crash.

**Implication for the plan.** A solo AI-generated content site is in the *intersection* of the two categories brokers are most bearish on, in the under-$300K bracket (**22.42× monthly / 1.87× annual**) and the "Typical"-or-below quality band. The defensible base-case exit assumption is:

| Scenario | Multiple | On $2,000/mo net profit |
|---|---|---|
| Distressed / declining profit | 13.7× monthly (1.14× annual) | **$27,400** |
| **Base case (under-$300K segment)** | **22.42× monthly (1.87× annual)** | **$44,840** |
| Typical band | 27.8× monthly (2.32× annual) | $55,600 |
| Premium (requires a real moat) | 31.1× monthly (2.59× annual) | $62,200 |

**The BP currently assumes a 4× SDE/EBITDA multiple.** Against Empire Flippers' 2025 realised data, 4× annual sits **above the 7-figure premium band (3.42×)** — a multiple achieved by 6.6% of deals averaging $2.06M in sale price. For a sub-$300K solo content asset, **4× annual is not supportable**; 1.87× is the base rate and 2.32× is an optimistic-but-arguable ceiling. This single input change reduces the modelled exit value by **~53%**, which flows directly into the MOIC and Kelly figures.

---

# 7. GAPS AND FOLLOW-UPS

Things I could not source and did not fabricate:

1. **Payoneer / Wise fee schedules** for non-US USD receipt — not retrieved.
2. **Cambridge Associates** venture benchmarks — paywalled.
3. **Stripe Atlas cohort outcome data** — Stripe has never published survival or revenue distributions for Atlas companies.
4. **Indie Hackers / Gumroad / Product Hunt earnings distributions** — no methodologically credible public dataset found.
5. **Newsletter-specific exit multiples** — no broker publishes them.
6. **Google's official Gemini pricing page** and **OpenAI's main pricing page** both timed out; Gemini and post-5.2 OpenAI SKUs are corroborated-secondary. Verify before budgeting.
7. **Semrush** pricing not retrieved from source.
8. **Delaware franchise tax** and **US CPA cost** figures are secondary.
9. **UptimeRobot's non-commercial restriction** on the free tier is tracker-reported, not confirmed on the pricing page.

Highest-value verifications before committing: **(a)** the services-vs-royalty characterisation of your specific ad/affiliate contracts, with a written practitioner opinion; **(b)** Gemini rates from Google direct; **(c)** whether your revenue model survives the payment-fee arithmetic in §4.1.
