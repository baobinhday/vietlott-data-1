import { NextResponse } from "next/server";
import { getProduct } from "@/lib/config";
import { loadDraws, loadPrizes } from "@/lib/data";
import {
  attachPrizes,
  computeEv,
  type DrawWithPrizes,
  POWER_535_JACKPOT_BASE,
  POWER_535_TICKET_PRICE,
} from "@/lib/ev";
import type { ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";

interface EvRequest {
  product?: ProductName;
  numTickets?: number;
  jackpotBase?: number;
  historyLimit?: number;
  /** Optional draw id; if set, the 10-draw window ends at this id (inclusive). */
  historyEndId?: string;
  /** Tier payout model. "fixed" = standard table (default). "historical_mean" = mean across data. */
  tierMode?: "fixed" | "historical_mean";
}

export async function POST(request: Request) {
  let body: EvRequest;
  try {
    body = (await request.json()) as EvRequest;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const productName = body.product ?? "power_535";
  const numTickets = Math.max(1, Math.min(200, Math.trunc(body.numTickets ?? 8)));
  const jackpotBase = body.jackpotBase ?? POWER_535_JACKPOT_BASE;
  const historyLimit = Math.max(2, Math.min(50, Math.trunc(body.historyLimit ?? 10)));
  const tierMode = body.tierMode === "historical_mean" ? "historical_mean" : "fixed";

  try {
    const product = getProduct(productName);
    const draws = loadDraws(product);
    const prizeRecords = loadPrizes(product);

    // Sort newest-first.
    const sortedDraws = [...draws].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

    // Attach prizes; only the ones with prize data are usable.
    const withPrizesAll: DrawWithPrizes[] = attachPrizes(sortedDraws, prizeRecords);

    let withPrizes: DrawWithPrizes[];
    if (body.historyEndId) {
      const endIdx = withPrizesAll.findIndex((d) => d.id === body.historyEndId);
      if (endIdx < 0) {
        return NextResponse.json(
          { error: `historyEndId=${body.historyEndId} not found` },
          { status: 400 },
        );
      }
      withPrizes = withPrizesAll.slice(endIdx, endIdx + historyLimit);
    } else {
      withPrizes = withPrizesAll.slice(0, historyLimit);
    }

    if (withPrizes.length < 2) {
      return NextResponse.json(
        {
          error: `Cần ít nhất 2 kỳ có dữ liệu giải để ước lượng EV. Hiện có ${withPrizes.length} kỳ.`,
        },
        { status: 400 },
      );
    }

    const ev = computeEv(withPrizes, numTickets, jackpotBase, tierMode);

    return NextResponse.json({
      product: product.name,
      display: product.display,
      ticketPrice: POWER_535_TICKET_PRICE,
      jackpotBase,
      historySampleSize: withPrizes.length,
      historyEndId: withPrizes[0]?.id ?? null,
      tierMode,
      ...ev,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
