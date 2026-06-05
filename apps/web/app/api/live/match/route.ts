import { NextResponse } from "next/server";

import { getLiveMatchSlots } from "@/lib/live-match";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload = await getLiveMatchSlots();

  return NextResponse.json(payload, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}
