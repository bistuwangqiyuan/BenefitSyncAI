import type {
  DayRangeMapping,
  DepositResult,
  FederalRules,
  StateRule,
} from "./types";

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

export function toIso(y: number, m0: number, d: number): string {
  return `${y}-${pad2(m0 + 1)}-${pad2(d)}`;
}

export function parseIso(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

export function formatIsoUTC(d: Date): string {
  return toIso(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

export function isWeekend(d: Date): boolean {
  const day = d.getUTCDay();
  return day === 0 || day === 6;
}

export function isHoliday(d: Date, holidays: Set<string>): boolean {
  return holidays.has(formatIsoUTC(d));
}

export function isBusinessDay(d: Date, holidays: Set<string>): boolean {
  return !isWeekend(d) && !isHoliday(d, holidays);
}

/** Move to previous calendar day until business day. */
export function previousBusinessDay(d: Date, holidays: Set<string>): Date {
  const cur = new Date(d.getTime());
  while (!isBusinessDay(cur, holidays)) {
    cur.setUTCDate(cur.getUTCDate() - 1);
  }
  return cur;
}

/** Nth business day of a month (1-based), UTC. */
export function nthBusinessDayOfMonth(
  year: number,
  month0: number,
  n: number,
  holidays: Set<string>,
): Date {
  const cur = new Date(Date.UTC(year, month0, 1));
  let count = 0;
  while (cur.getUTCMonth() === month0) {
    if (isBusinessDay(cur, holidays)) {
      count += 1;
      if (count === n) return new Date(cur.getTime());
    }
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  throw new Error(`Month has fewer than ${n} business days`);
}

/** Nth Wednesday of month (1-based). */
export function nthWednesdayOfMonth(
  year: number,
  month0: number,
  n: number,
): Date {
  const cur = new Date(Date.UTC(year, month0, 1));
  let count = 0;
  while (cur.getUTCMonth() === month0) {
    if (cur.getUTCDay() === 3) {
      count += 1;
      if (count === n) return new Date(cur.getTime());
    }
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  throw new Error(`Month has fewer than ${n} Wednesdays`);
}

export function dayFromRanges(
  value: number,
  ranges: DayRangeMapping[],
): number | null {
  for (const r of ranges) {
    if (value >= r.from && value <= r.to) return r.day_of_month;
  }
  return null;
}

export function monthsAhead(
  from: Date,
  count: number,
): { year: number; month0: number }[] {
  const out: { year: number; month0: number }[] = [];
  let y = from.getUTCFullYear();
  let m = from.getUTCMonth();
  for (let i = 0; i < count; i++) {
    out.push({ year: y, month0: m });
    m += 1;
    if (m > 11) {
      m = 0;
      y += 1;
    }
  }
  return out;
}

function datesForCalendarDay(
  dayOfMonth: number,
  from: Date,
  months: number,
): string[] {
  return monthsAhead(from, months).map(({ year, month0 }) => {
    const lastDay = new Date(Date.UTC(year, month0 + 1, 0)).getUTCDate();
    const d = Math.min(dayOfMonth, lastDay);
    return toIso(year, month0, d);
  });
}

export function resolveStateDayOfMonth(
  rule: StateRule,
  input: { digit?: string; twoDigits?: number },
): { day: number | null; error?: string } {
  if ("mapping" in rule) {
    if (input.digit === undefined || !/^[0-9]$/.test(input.digit)) {
      return { day: null, error: "Enter a single digit 0–9." };
    }
    const day = rule.mapping[input.digit];
    return day === undefined
      ? { day: null, error: "Unknown digit mapping." }
      : { day };
  }

  if ("ranges" in rule) {
    if (
      input.twoDigits === undefined ||
      input.twoDigits < 0 ||
      input.twoDigits > 99 ||
      !Number.isInteger(input.twoDigits)
    ) {
      return { day: null, error: "Enter a two-digit code from 00 to 99." };
    }
    const day = dayFromRanges(input.twoDigits, rule.ranges);
    return day === null
      ? { day: null, error: "No mapping for that code." }
      : { day };
  }

  return { day: null, error: "Unsupported rule kind." };
}

export function computeStateDepositCalendar(
  rule: StateRule,
  input: { digit?: string; twoDigits?: number },
  options?: {
    from?: Date;
    months?: number;
    holidays?: string[];
  },
): DepositResult {
  const from = options?.from ?? new Date();
  const fromUTC = new Date(
    Date.UTC(from.getFullYear(), from.getMonth(), from.getDate()),
  );
  const months = options?.months ?? 6;
  const holidaySet = new Set(options?.holidays ?? []);
  const resolved = resolveStateDayOfMonth(rule, input);

  if (resolved.error || resolved.day === null) {
    return {
      day_of_month: null,
      dates: [],
      explanation: resolved.error ?? "Could not resolve deposit day.",
      warnings: rule.notes,
    };
  }

  if (rule.input.kind === "business_day_last_digit") {
    const nth = resolved.day;
    const dates = monthsAhead(fromUTC, months).map(({ year, month0 }) =>
      formatIsoUTC(nthBusinessDayOfMonth(year, month0, nth, holidaySet)),
    );
    return {
      day_of_month: null,
      dates,
      explanation: `Staggered schedule: ${nth}${ordinal(nth)} business day of each month (digit ${input.digit}).`,
      warnings: rule.notes,
    };
  }

  return {
    day_of_month: resolved.day,
    dates: datesForCalendarDay(resolved.day, fromUTC, months),
    explanation: `Benefits are typically available on day ${resolved.day} of each month under ${rule.program}.`,
    warnings: rule.notes,
  };
}

function ordinal(n: number): string {
  const j = n % 10;
  const k = n % 100;
  if (j === 1 && k !== 11) return "st";
  if (j === 2 && k !== 12) return "nd";
  if (j === 3 && k !== 13) return "rd";
  return "th";
}

export function computeFederalSchedule(
  federal: FederalRules,
  programId: string,
  options?: {
    birthdayBand?: "1-10" | "11-20" | "21-31";
    from?: Date;
    months?: number;
  },
): DepositResult {
  const program = federal.programs.find((p) => p.id === programId);
  if (!program) {
    return {
      day_of_month: null,
      dates: [],
      explanation: "Unknown program.",
      warnings: [],
    };
  }

  const from = options?.from ?? new Date();
  const fromUTC = new Date(
    Date.UTC(from.getFullYear(), from.getMonth(), from.getDate()),
  );
  const months = options?.months ?? 6;
  const holidays = new Set(federal.federal_holidays);
  const rule = program.rule;

  if (rule.type === "first_of_month_prev_business") {
    const dates = monthsAhead(fromUTC, months).map(({ year, month0 }) => {
      const first = new Date(Date.UTC(year, month0, 1));
      return formatIsoUTC(previousBusinessDay(first, holidays));
    });
    return {
      day_of_month: 1,
      dates,
      explanation: program.summary,
      warnings: [rule.notes],
    };
  }

  if (rule.type === "third_of_month_prev_business") {
    const dates = monthsAhead(fromUTC, months).map(({ year, month0 }) => {
      const third = new Date(Date.UTC(year, month0, 3));
      return formatIsoUTC(previousBusinessDay(third, holidays));
    });
    return {
      day_of_month: 3,
      dates,
      explanation: program.summary,
      warnings: [rule.notes],
    };
  }

  if (rule.type === "first_business_day") {
    const dates = monthsAhead(fromUTC, months).map(({ year, month0 }) =>
      formatIsoUTC(nthBusinessDayOfMonth(year, month0, 1, holidays)),
    );
    return {
      day_of_month: null,
      dates,
      explanation: program.summary,
      warnings: [rule.notes],
    };
  }

  if (rule.type === "nth_wednesday_by_birthday_band") {
    const band = options?.birthdayBand;
    if (!band) {
      return {
        day_of_month: null,
        dates: [],
        explanation: "Select your birthday day-of-month band.",
        warnings: [rule.notes],
      };
    }
    const [fromDay, toDay] = band.split("-").map(Number) as [number, number];
    const match = rule.bands.find(
      (b) => b.from_day === fromDay && b.to_day === toDay,
    );
    if (!match) {
      return {
        day_of_month: null,
        dates: [],
        explanation: "Unknown birthday band.",
        warnings: [rule.notes],
      };
    }
    const dates = monthsAhead(fromUTC, months).map(({ year, month0 }) =>
      formatIsoUTC(nthWednesdayOfMonth(year, month0, match.wednesday_n)),
    );
    return {
      day_of_month: null,
      dates,
      explanation: `Paid on the ${match.wednesday_n}${ordinal(match.wednesday_n)} Wednesday of each month (birthday days ${band}).`,
      warnings: [rule.notes],
    };
  }

  return {
    day_of_month: null,
    dates: [],
    explanation: "Unsupported federal rule.",
    warnings: [],
  };
}
