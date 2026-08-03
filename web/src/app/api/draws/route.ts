import { NextResponse } from "next/server";
import { getProduct } from "@/lib/config";
import { loadDraws, loadPrizes } from "@/lib/data";
import type { Draw, ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const productName = (searchParams.get("product") ?? "power_535") as ProductName;
  const limit = Math.max(1, Math.min(200, Number(searchParams.get("limit") ?? "20")));
  const includePrizes = searchParams.get("prizes") === "1";
  try {
    const product = getProduct(productName);
    const draws = loadDraws(product);
    let responseDraws: Draw[] = draws.slice(0, limit);
    if (includePrizes) {
      const records = loadPrizes(product);
      const prizeById = new Map(records.map((r) => [r.id, r.prizes]));
      responseDraws = responseDraws.map((d) => {
        const p = prizeById.get(d.id);
        return p ? { ...d, prizes: p } : d;
      });
    }
    return NextResponse.json({
      product: product.name,
      display: product.display,
      total: draws.length,
      draws: responseDraws,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 400 });
  }
}
