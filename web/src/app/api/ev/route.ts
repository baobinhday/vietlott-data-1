import { NextResponse } from "next/server";
import { fetchEv } from "@/lib/api";
import type { ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";

interface EvRequest {
  product?: ProductName;
  numTickets?: number;
  jackpotBase?: number;
  historyLimit?: number;
  historyEndId?: string;
  tierMode?: "fixed" | "historical_mean";
}

export async function POST(request: Request) {
  let body: EvRequest;
  try {
    body = (await request.json()) as EvRequest;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const productName = (body.product ?? "power_535") as ProductName;
  try {
    const ev = await fetchEv({
      product: productName,
      numTickets: body.numTickets,
      jackpotBase: body.jackpotBase,
      historyLimit: body.historyLimit,
      historyEndId: body.historyEndId,
      tierMode: body.tierMode,
    });
    return NextResponse.json(ev);
  } catch (e) {
    // Backend returns 400 for "fewer than 2 draws with prize data" etc.;
    // mirror the old handler's status semantics.
    const msg = String(e);
    const status = msg.startsWith("Error: ") || msg.startsWith("HTTP 400") ? 400 : 500;
    return NextResponse.json({ error: msg }, { status });
  }
}
