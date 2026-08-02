import { Byline } from "@/components/Byline";
import { getIndex } from "@/lib/data";
import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description: `About ${SITE.name}: methodology, editorial responsibility, and what we will never build.`,
};

export default function AboutPage() {
  const index = getIndex();

  return (
    <article className="mx-auto max-w-2xl px-4 py-10 prose-deposit">
      <h1 className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
        About {SITE.name}
      </h1>
      <Byline updatedAt={index.updated_at} />

      <div className="mt-6 space-y-4 text-[var(--ink-soft)] leading-relaxed">
        <p>
          {SITE.name} ({SITE.nameCn}) turns publicly published benefit issuance rules into
          free, no-login calculators. One maintained data layer serves beneficiaries now and
          a machine-readable API for institutions later.
        </p>
        <p>
          This product follows the revised business plan opportunity <strong>C3</strong>: dual
          channel, free-to-user tools plus future B2B data subscriptions. We explicitly reject
          proxy login, automated filing, credential vaults, and charging beneficiaries for
          access to public schedule information.
        </p>

        <h2 className="pt-4 font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
          Methodology
        </h2>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            State SNAP/EBT rules are transcribed from the USDA FNS{" "}
            <em>Monthly Issuance Schedule All States</em> PDF, with per-rule citations and
            retrieval dates.
          </li>
          <li>
            Federal calendars apply publicly described SSA/VA timing rules plus a listed U.S.
            federal holiday set for business-day rollover.
          </li>
          <li>
            Calculations are deterministic pure functions. Anyone can re-run the same inputs
            via the open-source engine and <code>scripts/validate_rules.py</code>.
          </li>
          <li>
            We ship a state only when rules are citable. “Coming soon” beats inventing dates.
          </li>
        </ul>

        <h2 className="pt-4 font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
          Editorial responsibility
        </h2>
        <p>
          Named editor: <strong>{SITE.editorName}</strong>. In YMYL categories, anonymous
          fully automated sites fail quality evaluation. AI assists scraping, structuring,
          drafting, and monitoring; a human verifies rule changes and owns corrections.
        </p>

        <h2 className="pt-4 font-[family-name:var(--font-display)] text-xl text-[var(--ink)]">
          What we will never build
        </h2>
        <ul className="list-disc space-y-2 pl-5">
          <li>Logging into SSA.gov, Login.gov, or state portals on your behalf</li>
          <li>Storing passwords, full case numbers, SSNs, or EBT card numbers</li>
          <li>Scraping account balances</li>
          <li>Charging beneficiaries for schedule information</li>
          <li>Implying government affiliation</li>
        </ul>
      </div>
    </article>
  );
}
