import { NextResponse } from "next/server";
import { getProduct } from "@/lib/config";
import { getDefaultBacktestConfig } from "@/lib/backtest";
import { generatePrediction } from "@/lib/predict";
import type { BacktestConfig, ProductName } from "@/lib/types";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(request: Request) {
  let body: { product?: ProductName; config?: Partial<BacktestConfig> };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }
  const productName = body.product ?? "power_535";
  try {
    const product = getProduct(productName);
    const config: BacktestConfig = { ...getDefaultBacktestConfig(product), ...(body.config ?? {}) };
    const result = generatePrediction(product, config);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
