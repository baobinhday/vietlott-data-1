import { NextResponse } from "next/server";
import { fetchProducts } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const items = await fetchProducts();
    return NextResponse.json({ products: items });
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
