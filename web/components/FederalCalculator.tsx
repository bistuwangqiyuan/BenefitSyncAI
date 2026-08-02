"use client";

import { useMemo, useState } from "react";
import { computeFederalSchedule } from "@/lib/deposit-engine";
import type { FederalRules } from "@/lib/types";

function formatDisplayDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString("en-US", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function FederalCalculator({ federal }: { federal: FederalRules }) {
  const [programId, setProgramId] = useState(federal.programs[0]?.id ?? "ssi");
  const [band, setBand] = useState<"1-10" | "11-20" | "21-31">("1-10");

  const program = federal.programs.find((p) => p.id === programId);

  const result = useMemo(() => {
    return computeFederalSchedule(federal, programId, {
      birthdayBand: band,
      months: 6,
    });
  }, [federal, programId, band]);

  const needsBand = program?.rule.type === "nth_wednesday_by_birthday_band";

  return (
    <div className="space-y-6">
      <label className="block space-y-2">
        <span className="text-sm font-medium text-[var(--ink)]">Benefit type</span>
        <select
          className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-[var(--ink)]"
          value={programId}
          onChange={(e) => setProgramId(e.target.value as typeof programId)}
        >
          {federal.programs.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>

      {program && (
        <p className="text-[var(--ink-soft)] leading-relaxed">{program.summary}</p>
      )}

      {needsBand && (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-[var(--ink)]">
            Birthday day-of-month band
          </legend>
          <p className="text-xs text-[var(--muted)]">
            We only ask which third of the month — never your full date of birth.
          </p>
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["1-10", "1st – 10th"],
                ["11-20", "11th – 20th"],
                ["21-31", "21st – 31st"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setBand(value)}
                className={`rounded-lg px-3 py-2 text-sm transition ${
                  band === value
                    ? "bg-[var(--accent)] text-white"
                    : "bg-[var(--surface)] text-[var(--ink)] border border-[var(--line)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {result.dates.length > 0 && (
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
          {result.explanation !== program?.summary && (
            <p className="mb-4 text-sm text-[var(--accent)]">{result.explanation}</p>
          )}
          <h3 className="text-sm font-medium text-[var(--ink)]">
            Next 6 payment dates
          </h3>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2">
            {result.dates.map((iso) => (
              <li
                key={iso}
                className="rounded-lg bg-[var(--surface-2)] px-3 py-2 font-mono text-sm text-[var(--ink)]"
              >
                {formatDisplayDate(iso)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
