import { NextResponse } from "next/server";
import { fetchBacktest, getDefaultBacktestConfig } from "@/lib/api";
import type { BacktestConfig, ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

export async function POST(request: Request) {
  let body: { product?: ProductName; config?: Partial<BacktestConfig> };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  const productName = (body.product ?? "power_535") as ProductName;
  try {
    const config = { ...getDefaultBacktestConfig(productName), ...((body.config ?? {}) as BacktestConfig) };
    // NOTE: the Python backend merges sub-configs deep-ish over the same
    // defaults (a superset of the old TS shallow spread), so partial
    // sub-configs are safe to pass through.
    const summary = await fetchBacktest(productName, config);
    return NextResponse.json(summary);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
