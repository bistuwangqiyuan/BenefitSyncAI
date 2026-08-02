import Link from "next/link";
import { AdSlot } from "@/components/AdSlot";
import { Byline } from "@/components/Byline";
import { getIndex, listLiveStates } from "@/lib/data";
import { SITE } from "@/lib/site";

export default function HomePage() {
  const states = listLiveStates();
  const index = getIndex();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 md:py-14">
      <section className="max-w-2xl">
        <p className="text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
          {SITE.nameCn} · public rules · no login
        </p>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-4xl leading-[1.1] tracking-tight text-[var(--ink)] md:text-5xl">
          {SITE.name}
        </h1>
        <p className="mt-4 text-lg text-[var(--ink-soft)] leading-relaxed">
          Free deposit-date tools for state EBT/SNAP and federal benefit calendars.
          Built from published government schedules — not guesswork, not account access.
        </p>
        <Byline updatedAt={index.updated_at} />
      </section>

      <AdSlot slot="home-top" />

      <section className="mt-10">
        <h2 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ink)]">
          EBT / SNAP deposit calculator
        </h2>
        <p className="mt-2 max-w-2xl text-[var(--ink-soft)]">
          Pick your state. Enter only a last digit or two-digit schedule code — never a
          full case number, SSN, or card number.
        </p>
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {states.map((s) => (
            <li key={s.state_code}>
              <Link
                href={`/ebt/${s.state_code.toLowerCase()}`}
                className="group flex h-full flex-col rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)] hover:shadow-[0_8px_28px_rgba(13,122,95,0.08)]"
              >
                <span className="font-mono text-xs text-[var(--accent)]">
                  {s.state_code}
                </span>
                <span className="mt-1 font-[family-name:var(--font-display)] text-xl text-[var(--ink)] group-hover:text-[var(--accent-deep)]">
                  {s.state_name}
                </span>
                <span className="mt-2 text-sm text-[var(--muted)]">
                  Live · USDA FNS–sourced rules
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-[var(--muted)]">
          Other states: coming soon. We only ship rules we can cite and verify.
        </p>
      </section>

      <section className="mt-12 grid gap-4 md:grid-cols-2">
        <Link
          href="/federal"
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)]"
        >
          <h2 className="font-[family-name:var(--font-display)] text-xl">
            Federal payment calendar
          </h2>
          <p className="mt-2 text-sm text-[var(--ink-soft)]">
            SSA birthday Wednesdays, SSI first-of-month rules, VA typical dates — with
            holiday rollover.
          </p>
        </Link>
        <Link
          href="/direct-express"
          className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-6 transition hover:border-[var(--accent)]"
        >
          <h2 className="font-[family-name:var(--font-display)] text-xl">
            Direct Express transition
          </h2>
          <p className="mt-2 text-sm text-[var(--ink-soft)]">
            What cardholders should know about the issuer transition — official links only.
          </p>
        </Link>
      </section>
    </div>
  );
}
