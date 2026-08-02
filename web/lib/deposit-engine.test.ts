import { describe, expect, it } from "vitest";
import ca from "@/data/states/ca.json";
import fl from "@/data/states/fl.json";
import tx from "@/data/states/tx.json";
import federal from "@/data/federal/calendar.json";
import {
  computeFederalSchedule,
  computeStateDepositCalendar,
  dayFromRanges,
  nthBusinessDayOfMonth,
  nthWednesdayOfMonth,
  previousBusinessDay,
  toIso,
} from "./deposit-engine";
import type { FederalRules, StateBundle, StateRule } from "./types";

const caRule = (ca as StateBundle).rules.calfresh_case_last_digit as StateRule;
const flRule = (fl as StateBundle).rules.snap_digits_98 as Extract<
  StateRule,
  { ranges: unknown }
>;
const txPost = (tx as StateBundle).rules.snap_edg_post_2020 as Extract<
  StateRule,
  { ranges: unknown }
>;
const fed = federal as FederalRules;

describe("CA case last digit", () => {
  it("maps digit 6 → day 6", () => {
    const r = computeStateDepositCalendar(caRule, { digit: "6" }, {
      from: new Date("2026-08-01T12:00:00Z"),
      months: 1,
    });
    expect(r.day_of_month).toBe(6);
    expect(r.dates[0]).toBe("2026-08-06");
  });

  it("maps digit 0 → day 10", () => {
    const r = computeStateDepositCalendar(caRule, { digit: "0" }, {
      from: new Date("2026-08-01T12:00:00Z"),
      months: 1,
    });
    expect(r.day_of_month).toBe(10);
    expect(r.dates[0]).toBe("2026-08-10");
  });
});

describe("FL digits 9/8 ranges", () => {
  it("maps 00–03 → 1st", () => {
    expect(dayFromRanges(0, flRule.ranges)).toBe(1);
    expect(dayFromRanges(3, flRule.ranges)).toBe(1);
  });

  it("maps 96–99 → 28th", () => {
    const r = computeStateDepositCalendar(flRule, { twoDigits: 97 }, {
      from: new Date("2026-08-01T12:00:00Z"),
      months: 1,
    });
    expect(r.day_of_month).toBe(28);
  });
});

describe("TX EDG post-2020", () => {
  it("maps 42–45 → 28th", () => {
    const r = computeStateDepositCalendar(txPost, { twoDigits: 42 }, {
      from: new Date("2026-08-01T12:00:00Z"),
      months: 1,
    });
    expect(r.day_of_month).toBe(28);
  });
});

describe("federal helpers", () => {
  it("previous business day before New Year 2026", () => {
    const holidays = new Set(fed.federal_holidays);
    const jan1 = new Date(Date.UTC(2026, 0, 1));
    expect(toIso(2025, 11, 31)).toBe(
      (() => {
        const d = previousBusinessDay(jan1, holidays);
        return toIso(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
      })(),
    );
  });

  it("2nd Wednesday of August 2026 is Aug 12", () => {
    const d = nthWednesdayOfMonth(2026, 7, 2);
    expect(toIso(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toBe(
      "2026-08-12",
    );
  });

  it("SSI schedule rolls Jan 2026 to Dec 31 2025", () => {
    const r = computeFederalSchedule(fed, "ssi", {
      from: new Date("2026-01-01T12:00:00Z"),
      months: 1,
    });
    expect(r.dates[0]).toBe("2025-12-31");
  });

  it("birthday band 1-10 uses 2nd Wednesday", () => {
    const r = computeFederalSchedule(fed, "ssa_birthday_wed", {
      birthdayBand: "1-10",
      from: new Date("2026-08-01T12:00:00Z"),
      months: 1,
    });
    expect(r.dates[0]).toBe("2026-08-12");
  });

  it("1st business day of Aug 2026 is Aug 3 (weekend start)", () => {
    // Aug 1 2026 is Saturday
    const holidays = new Set(fed.federal_holidays);
    const d = nthBusinessDayOfMonth(2026, 7, 1, holidays);
    expect(toIso(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toBe(
      "2026-08-03",
    );
  });
});
