import { NextResponse } from "next/server";
import { fetchPredict } from "@/lib/api";
import { getDefaultBacktestConfig } from "@/lib/api";
import type { BacktestConfig, ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  let body: { product?: ProductName; strategy?: string; config?: Partial<BacktestConfig>; target_date?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  const productName = (body.product ?? "power_535") as ProductName;
  try {
    const config: BacktestConfig = {
      ...getDefaultBacktestConfig(productName),
      ...((body.config ?? {}) as BacktestConfig),
    };
    if (body.strategy && !config.strategy) config.strategy = body.strategy;
    const result = await fetchPredict(productName, config);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
