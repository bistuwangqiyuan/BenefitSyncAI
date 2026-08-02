/** Versioned SNAP/EBT deposit rule types for DepositDay. */

export type RuleKind =
  | "case_last_digit"
  | "case_last_two_digits_ranges"
  | "edg_last_digit"
  | "edg_last_two_digits_ranges"
  | "fl_digits_98_ranges"
  | "business_day_last_digit";

export interface Citation {
  title: string;
  url: string;
  publisher: string;
  retrieved_at: string;
}

export interface DayRangeMapping {
  /** Inclusive range of the key digits, e.g. [0, 3] for 00-03 */
  from: number;
  to: number;
  day_of_month: number;
}

export interface LastDigitMapping {
  /** Key is digit character "0".."9" → calendar day of month (1-31) */
  [digit: string]: number;
}

export interface BusinessDayLastDigitMapping {
  /** Key is digit "0".."9" → nth business day of the month (1-based) */
  [digit: string]: number;
}

export interface StateRuleBase {
  state_code: string;
  state_name: string;
  program: string;
  version: string;
  effective_from: string;
  updated_at: string;
  status: "live" | "coming_soon";
  summary: string;
  notes: string[];
  citations: Citation[];
  input_hint: string;
  /** What the UI should ask for — never full case numbers or SSN */
  input: {
    kind: RuleKind;
    label: string;
    help: string;
  };
}

export interface CaseLastDigitRule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "case_last_digit" };
  mapping: LastDigitMapping;
}

export interface CaseLastTwoRangesRule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "case_last_two_digits_ranges" };
  ranges: DayRangeMapping[];
}

export interface EdgLastDigitRule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "edg_last_digit" };
  mapping: LastDigitMapping;
  cohort: "pre_2020_06_01" | "post_2020_06_01";
}

export interface EdgLastTwoRangesRule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "edg_last_two_digits_ranges" };
  ranges: DayRangeMapping[];
  cohort: "pre_2020_06_01" | "post_2020_06_01";
}

export interface FlDigits98Rule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "fl_digits_98_ranges" };
  ranges: DayRangeMapping[];
}

export interface BusinessDayLastDigitRule extends StateRuleBase {
  input: StateRuleBase["input"] & { kind: "business_day_last_digit" };
  mapping: BusinessDayLastDigitMapping;
  holiday_calendar: "us_federal";
}

export type StateRule =
  | CaseLastDigitRule
  | CaseLastTwoRangesRule
  | EdgLastDigitRule
  | EdgLastTwoRangesRule
  | FlDigits98Rule
  | BusinessDayLastDigitRule;

export interface StateBundle {
  state_code: string;
  state_name: string;
  status: "live" | "coming_soon";
  default_rule_id: string;
  rules: Record<string, StateRule>;
  coming_soon_note?: string;
}

export type FederalBenefitKind =
  | "ssi"
  | "ssa_birthday_wed"
  | "ssa_third"
  | "va_compensation";

export interface FederalRules {
  version: string;
  updated_at: string;
  citations: Citation[];
  programs: {
    id: FederalBenefitKind;
    name: string;
    summary: string;
    rule:
      | { type: "first_of_month_prev_business"; notes: string }
      | {
          type: "nth_wednesday_by_birthday_band";
          bands: { from_day: number; to_day: number; wednesday_n: number }[];
          notes: string;
        }
      | { type: "third_of_month_prev_business"; notes: string }
      | { type: "first_business_day"; notes: string };
  }[];
  /** ISO dates that are US federal holidays (YYYY-MM-DD) for engine rollover */
  federal_holidays: string[];
}

export interface DirectExpressInfo {
  version: string;
  updated_at: string;
  title: string;
  summary: string;
  timeline: { date: string; event: string }[];
  cardholder_notes: string[];
  official_links: { label: string; url: string }[];
  citations: Citation[];
}

export interface DepositResult {
  day_of_month: number | null;
  dates: string[]; // ISO YYYY-MM-DD for next N months
  explanation: string;
  warnings: string[];
}
