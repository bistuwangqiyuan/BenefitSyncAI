import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Rules API",
  description: "Machine-readable DepositDay rules API for institutions.",
};

export default function ApiDocsPage() {
  const base = SITE.url.replace(/\/$/, "");

  return (
    <article className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
        Rules API
      </h1>
      <p className="mt-4 text-[var(--ink-soft)] leading-relaxed">
        Versioned, cited SNAP/EBT and federal schedule data as JSON. MVP is publicly readable
        so partners can evaluate the dataset. When <code>RULES_API_KEYS</code> is configured,
        send <code>X-Api-Key</code>.
      </p>

      <h2 className="mt-8 font-[family-name:var(--font-display)] text-xl">Endpoints</h2>
      <ul className="mt-4 space-y-4 text-sm">
        <li className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <code className="text-[var(--accent)]">GET /api/v1/rules</code>
          <p className="mt-2 text-[var(--ink-soft)]">All live state bundles + federal + Direct Express.</p>
          <a href={`${base}/api/v1/rules`} className="mt-2 inline-block text-[var(--accent)] hover:underline">
            {base}/api/v1/rules
          </a>
        </li>
        <li className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <code className="text-[var(--accent)]">GET /api/v1/rules/{"{state}"}</code>
          <p className="mt-2 text-[var(--ink-soft)]">One state, e.g. <code>ca</code>.</p>
          <a href={`${base}/api/v1/rules/ca`} className="mt-2 inline-block text-[var(--accent)] hover:underline">
            {base}/api/v1/rules/ca
          </a>
        </li>
      </ul>

      <p className="mt-8 text-sm text-[var(--muted)]">
        Paid B2B subscriptions (target ARPA per BP) are not enabled in this MVP. No Stripe
        checkout yet — evaluate the data first.
      </p>
    </article>
  );
}
