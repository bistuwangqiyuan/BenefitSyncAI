import { SITE } from "@/lib/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
};

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="font-[family-name:var(--font-display)] text-3xl text-[var(--ink)]">
        Privacy
      </h1>
      <div className="mt-6 space-y-4 text-[var(--ink-soft)] leading-relaxed">
        <p>
          {SITE.name} is designed for minimal data. Calculator inputs (a single digit or
          two-digit schedule code, or a birthday band) are processed in your browser. We do
          not create user accounts and we do not ask for full case numbers, names, dates of
          birth, SSNs, bank details, or card numbers.
        </p>
        <p>
          Hosting and analytics (if enabled later) may collect standard technical logs such as
          IP address, user agent, and pages visited — common to any website. We do not sell
          personal data. We do not use beneficiary inputs for lead generation to disability
          lawyers or Medicare plan sellers.
        </p>
        <p>
          The optional rules API may later require an API key for institutional subscribers.
          Keys identify the organization, not individual beneficiaries.
        </p>
        <p>
          Questions: open an issue at{" "}
          <a
            href={SITE.githubIssues}
            className="text-[var(--accent)] hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          .
        </p>
      </div>
    </article>
  );
}
