"use client";

import { useMemo, useState } from "react";
import {
  computeStateDepositCalendar,
} from "@/lib/deposit-engine";
import type { StateBundle, StateRule } from "@/lib/types";

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

export function EbtCalculator({
  bundle,
  holidays,
}: {
  bundle: StateBundle;
  holidays: string[];
}) {
  const ruleIds = Object.keys(bundle.rules);
  const [ruleId, setRuleId] = useState(bundle.default_rule_id);
  const rule: StateRule = bundle.rules[ruleId];
  const [digit, setDigit] = useState("");
  const [twoDigits, setTwoDigits] = useState("");

  const result = useMemo(() => {
    if (!rule) return null;
    const kind = rule.input.kind;
    if (
      kind === "case_last_digit" ||
      kind === "edg_last_digit" ||
      kind === "business_day_last_digit"
    ) {
      if (!/^[0-9]$/.test(digit)) return null;
      return computeStateDepositCalendar(
        rule,
        { digit },
        { holidays, months: 6 },
      );
    }
    if (
      kind === "edg_last_two_digits_ranges" ||
      kind === "fl_digits_98_ranges" ||
      kind === "case_last_two_digits_ranges"
    ) {
      if (!/^\d{1,2}$/.test(twoDigits)) return null;
      const n = Number(twoDigits);
      if (n < 0 || n > 99) return null;
      return computeStateDepositCalendar(
        rule,
        { twoDigits: n },
        { holidays, months: 6 },
      );
    }
    return null;
  }, [rule, digit, twoDigits, holidays]);

  const needsTwo =
    rule?.input.kind === "edg_last_two_digits_ranges" ||
    rule?.input.kind === "fl_digits_98_ranges" ||
    rule?.input.kind === "case_last_two_digits_ranges";

  return (
    <div className="space-y-6">
      {ruleIds.length > 1 && (
        <label className="block space-y-2">
          <span className="text-sm font-medium text-[var(--ink)]">Schedule cohort</span>
          <select
            className="w-full rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-[var(--ink)]"
            value={ruleId}
            onChange={(e) => {
              setRuleId(e.target.value);
              setDigit("");
              setTwoDigits("");
            }}
          >
            {ruleIds.map((id) => (
              <option key={id} value={id}>
                {bundle.rules[id].program}
              </option>
            ))}
          </select>
        </label>
      )}

      <p className="text-[var(--ink-soft)] leading-relaxed">{rule.summary}</p>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-[var(--ink)]">{rule.input.label}</span>
        {needsTwo ? (
          <input
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={2}
            placeholder="00"
            value={twoDigits}
            onChange={(e) =>
              setTwoDigits(e.target.value.replace(/\D/g, "").slice(0, 2))
            }
            className="w-full max-w-[12rem] rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 font-mono text-lg text-[var(--ink)]"
            autoComplete="off"
            name="schedule-code"
          />
        ) : (
          <input
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            placeholder="0–9"
            value={digit}
            onChange={(e) =>
              setDigit(e.target.value.replace(/\D/g, "").slice(0, 1))
            }
            className="w-full max-w-[8rem] rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 font-mono text-lg text-[var(--ink)]"
            autoComplete="off"
            name="last-digit"
          />
        )}
        <span className="block text-xs text-[var(--muted)]">{rule.input.help}</span>
      </label>

      {result && result.dates.length > 0 && (
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
          <p className="text-sm text-[var(--accent)]">{result.explanation}</p>
          {result.day_of_month !== null && (
            <p className="mt-2 font-[family-name:var(--font-display)] text-4xl text-[var(--ink)]">
              Day {result.day_of_month}
            </p>
          )}
          <h3 className="mt-4 text-sm font-medium text-[var(--ink)]">
            Next 6 months
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

      {result && result.dates.length === 0 && result.explanation && (
        <p className="text-sm text-[var(--warn)]">{result.explanation}</p>
      )}

      {rule.notes.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-xs text-[var(--muted)]">
          {rule.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
