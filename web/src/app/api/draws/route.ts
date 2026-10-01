import { NextResponse } from "next/server";
import { fetchDraws } from "@/lib/api";
import type { Draw, ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const productName = (searchParams.get("product") ?? "power_535") as ProductName;
  const limit = Math.max(1, Math.min(200, Number(searchParams.get("limit") ?? "20")));
  const includePrizes = searchParams.get("prizes") === "1";
  try {
    const data = await fetchDraws(productName, limit, includePrizes);
    // Normalize: the backend may emit `prizes: null` when missing.
    const draws: Draw[] = data.draws.map((d) => (d.prizes == null ? { ...d, prizes: undefined } : d));
    return NextResponse.json({
      product: productName,
      display: data.display,
      total: data.total,
      draws,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 400 });
  }
}
