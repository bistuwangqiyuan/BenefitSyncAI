import ca from "@/data/states/ca.json";
import fl from "@/data/states/fl.json";
import ny from "@/data/states/ny.json";
import pa from "@/data/states/pa.json";
import tx from "@/data/states/tx.json";
import federal from "@/data/federal/calendar.json";
import directExpress from "@/data/direct-express.json";
import index from "@/data/index.json";
import type {
  DirectExpressInfo,
  FederalRules,
  StateBundle,
  StateRule,
} from "./types";

const bundles: Record<string, StateBundle> = {
  CA: ca as StateBundle,
  TX: tx as StateBundle,
  FL: fl as StateBundle,
  NY: ny as StateBundle,
  PA: pa as StateBundle,
};

export function getIndex() {
  return index;
}

export function listLiveStates(): StateBundle[] {
  return index.live_states.map((code) => bundles[code]).filter(Boolean);
}

export function getStateBundle(code: string): StateBundle | null {
  return bundles[code.toUpperCase()] ?? null;
}

export function getDefaultRule(code: string): StateRule | null {
  const b = getStateBundle(code);
  if (!b) return null;
  return b.rules[b.default_rule_id] ?? null;
}

export function getRule(code: string, ruleId: string): StateRule | null {
  const b = getStateBundle(code);
  if (!b) return null;
  return b.rules[ruleId] ?? null;
}

export function getFederalRules(): FederalRules {
  return federal as FederalRules;
}

export function getDirectExpress(): DirectExpressInfo {
  return directExpress as DirectExpressInfo;
}

export function getAllRulesPayload() {
  return {
    product: index.product,
    version: index.version,
    updated_at: index.updated_at,
    live_states: index.live_states,
    states: Object.fromEntries(
      Object.entries(bundles).map(([code, bundle]) => [
        code,
        {
          state_code: bundle.state_code,
          state_name: bundle.state_name,
          status: bundle.status,
          default_rule_id: bundle.default_rule_id,
          rules: bundle.rules,
        },
      ]),
    ),
    federal: getFederalRules(),
    direct_express: getDirectExpress(),
  };
}
