import { NextRequest, NextResponse } from "next/server";
import { checkApiKey } from "@/lib/api-auth";
import { getStateBundle } from "@/lib/data";

type Props = { params: Promise<{ state: string }> };

export async function GET(req: NextRequest, { params }: Props) {
  const auth = checkApiKey(req);
  if (!auth.ok) {
    return NextResponse.json({ error: auth.message }, { status: auth.status });
  }

  const { state } = await params;
  const bundle = getStateBundle(state);
  if (!bundle) {
    return NextResponse.json(
      { error: `State '${state}' not found. Live: CA, TX, FL, NY, PA.` },
      { status: 404 },
    );
  }

  return NextResponse.json(
    {
      state_code: bundle.state_code,
      state_name: bundle.state_name,
      status: bundle.status,
      default_rule_id: bundle.default_rule_id,
      rules: bundle.rules,
    },
    {
      headers: {
        "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
      },
    },
  );
}
