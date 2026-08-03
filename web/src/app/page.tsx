"use client";

import { useEffect, useMemo, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { BacktestView } from "@/components/BacktestView";
import { PredictionView } from "@/components/PredictionView";
import { TabBar } from "@/components/TabBar";
import type { BacktestConfig, BacktestSummary, Draw, PredictionResult, ProductName } from "@/lib/types";

interface ProductInfo {
  name: ProductName;
  display: string;
  minValue: number;
  maxValue: number;
  sizeOutput: number;
  hasSpecial: boolean;
  specialMin: number;
  specialMax: number;
  defaultConfig: BacktestConfig;
}

export default function Home() {
  const [products, setProducts] = useState<ProductInfo[]>([]);
  const [product, setProduct] = useState<ProductName>("power_535");
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load product catalog on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/products");
        const data = await res.json();
        if (cancelled) return;
        const items: ProductInfo[] = data.products ?? [];
        setProducts(items);
        if (items.length) setProduct(items[0].name);
      } catch (e) {
        if (!cancelled) setLoadError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500">
        Lỗi tải cấu hình: {loadError}
      </div>
    );
  }
  if (!products.length) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-500">
        Đang tải cấu hình sản phẩm…
      </div>
    );
  }

  // Re-mount the inner shell when the product changes so that
  // `config` (and any in-flight results) reset cleanly.  No setState-in-effect.
  return <ProductShell key={product} products={products} product={product} onProductChange={setProduct} />;
}

interface ProductShellProps {
  products: ProductInfo[];
  product: ProductName;
  onProductChange: (p: ProductName) => void;
}

function ProductShell({ products, product, onProductChange }: ProductShellProps) {
  const productInfo = useMemo(() => products.find((p) => p.name === product)!, [products, product]);
  const [config, setConfig] = useState<BacktestConfig>(productInfo.defaultConfig);
  const [strategy] = useState<string>("Inverse Hybrid: Cold Numbers → Steiner");
  const [tab, setTab] = useState<"backtest" | "prediction">("prediction");

  const [latestDraw, setLatestDraw] = useState<Draw | null>(null);
  const [latestDrawLoading, setLatestDrawLoading] = useState(true);
  const [latestDrawError, setLatestDrawError] = useState<string | null>(null);

  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [backtest, setBacktest] = useState<BacktestSummary | null>(null);

  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);

  // Load the most recent draw + its prize breakdown on mount and whenever
  // the product changes.  This way the Prediction tab always has something
  // meaningful to show without forcing the user to click "Dự đoán" first.
  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLatestDrawLoading(true);
    setLatestDrawError(null);
    (async () => {
      try {
        const res = await fetch(`/api/draws?product=${product}&limit=1&prizes=1`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error ?? `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (cancelled) return;
        setLatestDraw(data.draws?.[0] ?? null);
      } catch (e) {
        if (!cancelled) setLatestDrawError(String(e));
      } finally {
        if (!cancelled) setLatestDrawLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [product]);

  const runBacktest = async () => {
    setBacktestLoading(true);
    setBacktestError(null);
    try {
      const res = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product, config }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error ?? `HTTP ${res.status}`);
      }
      const data = (await res.json()) as BacktestSummary;
      setBacktest(data);
      setTab("backtest");
    } catch (e) {
      setBacktestError(String(e));
    } finally {
      setBacktestLoading(false);
    }
  };

  const runPredict = async () => {
    setPredictionLoading(true);
    setPredictionError(null);
    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product, config }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error ?? `HTTP ${res.status}`);
      }
      const data = (await res.json()) as PredictionResult;
      setPrediction(data);
    } catch (e) {
      setPredictionError(String(e));
    } finally {
      setPredictionLoading(false);
    }
  };

  return (
    <div className="flex flex-1 min-h-0">
      <Sidebar
        products={products}
        product={product}
        onProductChange={onProductChange}
        strategy={strategy}
        config={config}
        onConfigChange={setConfig}
        onRunBacktest={runBacktest}
        onRunPredict={runPredict}
        backtestLoading={backtestLoading}
        predictionLoading={predictionLoading}
      />
      <main className="flex-1 min-w-0 flex flex-col">
        <TabBar active={tab} onChange={setTab} />
        <div className="flex-1 min-h-0 overflow-y-auto p-6">
          {tab === "backtest" ? (
            <BacktestView
              summary={backtest}
              loading={backtestLoading}
              error={backtestError}
              onRun={runBacktest}
              ticketPrice={10000}
            />
          ) : (
            <PredictionView
              result={prediction}
              loading={predictionLoading}
              error={predictionError}
              onRun={runPredict}
              product={productInfo}
              latestDraw={latestDraw}
              latestDrawLoading={latestDrawLoading}
              latestDrawError={latestDrawError}
            />
          )}
        </div>
      </main>
    </div>
  );
}
