import { NextResponse } from "next/server";
import { PRODUCTS } from "@/lib/config";
import { getDefaultBacktestConfig } from "@/lib/backtest";

export const dynamic = "force-dynamic";

export async function GET() {
  const items = Object.values(PRODUCTS)
    .filter((p) => p.name === "power_535")
    .map((p) => ({
      name: p.name,
      display: p.display,
      minValue: p.minValue,
      maxValue: p.maxValue,
      sizeOutput: p.sizeOutput,
      hasSpecial: p.hasSpecial,
      specialMin: p.specialMin,
      specialMax: p.specialMax,
      defaultConfig: getDefaultBacktestConfig(p),
    }));
  return NextResponse.json({ products: items });
}
