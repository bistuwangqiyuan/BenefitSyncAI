import { notFound } from "next/navigation";
import { AdSlot } from "@/components/AdSlot";
import { Byline } from "@/components/Byline";
import { EbtCalculator } from "@/components/EbtCalculator";
import { getFederalRules, getStateBundle, listLiveStates } from "@/lib/data";
import type { Metadata } from "next";
import Link from "next/link";

type Props = { params: Promise<{ state: string }> };

export async function generateStaticParams() {
  return listLiveStates().map((s) => ({ state: s.state_code.toLowerCase() }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { state } = await params;
  const bundle = getStateBundle(state);
  if (!bundle) return { title: "State not found" };
  return {
    title: `${bundle.state_name} EBT deposit dates`,
    description: `Calculate ${bundle.state_name} SNAP/EBT deposit dates from published USDA FNS rules. Free, no login, no full case numbers.`,
  };
}

export default async function StateEbtPage({ params }: Props) {
  const { state } = await params;
  const bundle = getStateBundle(state);
  if (!bundle || bundle.status !== "live") notFound();

  const federal = getFederalRules();
  const rule = bundle.rules[bundle.default_rule_id];
  const citations = Object.values(bundle.rules).flatMap((r) => r.citations);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <p className="text-sm">
        <Link href="/" className="text-[var(--accent)] hover:underline">
          ← All states
        </Link>
      </p>
      <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--ink)]">
        {bundle.state_name} EBT deposit dates
      </h1>
      <Byline updatedAt={rule.updated_at} />
      <AdSlot slot="ebt-top" />
      <div className="mt-8 max-w-xl">
        <EbtCalculator bundle={bundle} holidays={federal.federal_holidays} />
      </div>
      <div className="mt-10 max-w-xl text-sm text-[var(--muted)]">
        <p className="font-medium text-[var(--ink-soft)]">Primary sources</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {citations.map((c) => (
            <li key={`${c.url}-${c.title}`}>
              <a
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] hover:underline"
              >
                {c.title}
              </a>
              <span> — {c.publisher}, retrieved {c.retrieved_at}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
