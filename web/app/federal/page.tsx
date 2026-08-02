import { AdSlot } from "@/components/AdSlot";
import { Byline } from "@/components/Byline";
import { FederalCalculator } from "@/components/FederalCalculator";
import { getFederalRules } from "@/lib/data";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Federal payment calendar",
  description:
    "SSI, Social Security Wednesday schedule, and VA typical deposit dates with holiday rules. Free, no login.",
};

export default function FederalPage() {
  const federal = getFederalRules();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--ink)]">
        Federal payment calendar
      </h1>
      <p className="mt-3 max-w-2xl text-[var(--ink-soft)]">
        Rule-based estimates from publicly described SSA/VA schedules. Not an official
        government calendar — always confirm with SSA.gov or VA.gov if a payment is late.
      </p>
      <Byline updatedAt={federal.updated_at} />
      <AdSlot slot="federal-top" />
      <div className="mt-8 max-w-xl">
        <FederalCalculator federal={federal} />
      </div>
      <ul className="mt-10 max-w-xl list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
        {federal.citations.map((c) => (
          <li key={c.url}>
            <a
              href={c.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--accent)] hover:underline"
            >
              {c.title}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
