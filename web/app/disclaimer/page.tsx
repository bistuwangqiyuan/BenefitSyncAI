import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Disclaimer",
};

export default function DisclaimerPage() {
  return (
    <article className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
        Disclaimer
      </h1>
      <div className="mt-6 space-y-4 text-[var(--ink-soft)] leading-relaxed">
        <p>{SITE.nonAffiliation}</p>
        <p>
          Deposit dates shown are estimates derived from publicly published issuance rules.
          Actual posting times can vary by county, case status, holidays, banking cutoffs, and
          agency actions. If a payment is late or missing, contact the issuing agency or your
          financial institution through official channels.
        </p>
        <p>
          This site does not provide legal, tax, or benefits-eligibility advice. It does not
          file forms, open accounts, or act as your representative before any agency.
        </p>
        <p>
          Information may become outdated when states revise schedules. Please{" "}
          <a
            href={SITE.githubIssues}
            className="text-[var(--accent)] hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            report a correction
          </a>{" "}
          if you find an error.
        </p>
      </div>
    </article>
  );
}
