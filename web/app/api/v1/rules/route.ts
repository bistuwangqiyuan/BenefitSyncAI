import { NextRequest, NextResponse } from "next/server";
import { checkApiKey } from "@/lib/api-auth";
import { getAllRulesPayload } from "@/lib/data";

export async function GET(req: NextRequest) {
  const auth = checkApiKey(req);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.message }, { status: auth.status });
  }

  const payload = getAllRulesPayload();
  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
      "X-DepositDay-Version": payload.version,
    },
  });
}
