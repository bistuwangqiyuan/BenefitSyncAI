import { NextRequest } from "next/server";

/**
 * Optional API key gate for future B2B. When RULES_API_KEYS is unset,
 * the rules API is publicly readable (MVP falsification mode).
 * When set (comma-separated), require matching X-Api-Key header.
 */
export function checkApiKey(req: NextRequest): { ok: true } | { ok: false; status: number; message: string } {
  const configured = process.env.RULES_API_KEYS?.trim();
  if (!configured) return { ok: true };

  const keys = configured.split(",").map((k) => k.trim()).filter(Boolean);
  const provided = req.headers.get("x-api-key")?.trim();
  if (!provided || !keys.includes(provided)) {
    return {
      ok: false,
      status: 401,
      message: "Missing or invalid X-Api-Key. Contact DepositDay for a B2B key.",
    };
  }
  return { ok: true };
}
