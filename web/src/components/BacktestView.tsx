"use client";

import { useState } from "react";
import type { BacktestSummary, BacktestTicketRow } from "@/lib/types";
import { TicketNumbers } from "./NumberBall";

interface BacktestViewProps {
  summary: BacktestSummary | null;
  loading: boolean;
  error: string | null;
  onRun: () => void;
  ticketPrice: number;
}

const fmtVnd = (n: number) => `${n.toLocaleString("vi-VN")} ₫`;

export function BacktestView({ summary, loading, error, onRun }: BacktestViewProps) {
  const [showAll, setShowAll] = useState(false);

  if (loading) {
    return <LoadingPanel message="Đang chạy backtest…" />;
  }
  if (error) {
    return <ErrorPanel message={error} onRetry={onRun} />;
  }
  if (!summary) {
    return <EmptyPanel onRun={onRun} />;
  }

  const distEntries = Object.entries(summary.matchDistribution)
    .map(([k, v]) => [Number(k), v] as [number, number])
    .sort((a, b) => b[0] - a[0]);
  const maxDist = Math.max(1, ...distEntries.map(([, v]) => v));
  const visibleRows = showAll ? summary.allRows : summary.allRows.slice(0, 200);
  const totalRows = summary.allRows.length;

  return (
    <div className="space-y-6">
      <Header summary={summary} onRerun={onRun} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Total cost" value={fmtVnd(summary.totalCost)} tone="muted" />
        <Stat label="Total gain" value={fmtVnd(summary.totalGain)} tone="good" />
        <Stat
          label="Net profit"
          value={fmtVnd(summary.netProfit)}
          tone={summary.netProfit >= 0 ? "good" : "bad"}
        />
        <Stat
          label="ROI"
          value={`${summary.roi.toFixed(2)}%`}
          tone={summary.roi >= 0 ? "good" : "bad"}
        />
        <Stat label="Draws evaluated" value={summary.totalDraws.toLocaleString("vi-VN")} />
        <Stat label="Total predictions" value={summary.totalPredictions.toLocaleString("vi-VN")} />
        <Stat label="Special hits" value={summary.specialHits.toLocaleString("vi-VN")} />
        <Stat label="Best threshold" value={`${summary.bestThreshold}+ matches`} />
      </div>

      <Panel title="Phân bố số trúng (main numbers)">
        <div className="space-y-1.5">
          {distEntries.map(([k, v]) => {
            const pct = (v / maxDist) * 100;
            return (
              <div key={k} className="flex items-center gap-3 text-sm">
                <span className="w-16 text-zinc-400 text-right font-mono">{k} trúng</span>
                <div className="flex-1 bg-zinc-900 rounded h-5 relative overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-amber-600 to-amber-400"
                    style={{ width: `${pct}%` }}
                  />
                  <span className="absolute inset-0 flex items-center pl-2 text-xs text-zinc-200 font-mono">
                    {v.toLocaleString("vi-VN")}
                  </span>
                </div>
                <span className="w-20 text-right text-xs text-zinc-500 font-mono">
                  {((v / summary.totalPredictions) * 100).toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel title="Yearly breakdown">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Year</th>
                <th className="num">Draws</th>
                <th className="num">Predictions</th>
                <th className="num">Cost</th>
                <th className="num">Gain</th>
                <th className="num">Net Profit</th>
                <th className="num">ROI</th>
              </tr>
            </thead>
            <tbody>
              {summary.yearlyBreakdown.map((y) => (
                <tr key={y.year}>
                  <td className="font-mono">{y.year}</td>
                  <td className="num">{y.draws.toLocaleString("vi-VN")}</td>
                  <td className="num">{y.predictions.toLocaleString("vi-VN")}</td>
                  <td className="num">{fmtVnd(y.cost)}</td>
                  <td className="num">{fmtVnd(y.gain)}</td>
                  <td className={`num ${y.profit >= 0 ? "text-green-400" : "text-red-400"}`}>{fmtVnd(y.profit)}</td>
                  <td className={`num ${y.roi >= 0 ? "text-green-400" : "text-red-400"}`}>{y.roi.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title={`Best results (≥ ${summary.bestThreshold} matches)`}
        right={
          <span className="text-xs text-zinc-500">
            {summary.bestResults.length.toLocaleString("vi-VN")} rows
          </span>
        }
      >
        <BestResultsTable rows={summary.bestResults.slice(0, 100)} />
      </Panel>

      <Panel
        title="Tất cả các vé đã mua"
        right={
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">
              {showAll ? totalRows.toLocaleString("vi-VN") : `Hiển thị 200 / ${totalRows.toLocaleString("vi-VN")}`}
            </span>
            {totalRows > 200 && (
              <button type="button" className="btn-ghost text-xs" onClick={() => setShowAll((s) => !s)}>
                {showAll ? "Thu gọn" : "Hiện tất cả"}
              </button>
            )}
          </div>
        }
      >
        <AllRowsTable rows={visibleRows} />
      </Panel>
    </div>
  );
}

function Header({ summary, onRerun }: { summary: BacktestSummary; onRerun: () => void }) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h2 className="text-xl font-bold tracking-tight">Kết quả backtest</h2>
        <p className="text-xs text-zinc-500 mt-1">
          Inverse Hybrid: Cold Numbers → Steiner · {summary.totalDraws.toLocaleString("vi-VN")} draws ·{" "}
          {summary.totalPredictions.toLocaleString("vi-VN")} predictions
        </p>
      </div>
      <button type="button" className="btn-primary" onClick={onRerun}>
        Chạy lại
      </button>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad" | "muted";
}) {
  const color =
    tone === "good" ? "text-green-400" : tone === "bad" ? "text-red-400" : tone === "muted" ? "text-zinc-300" : "text-amber-400";
  return (
    <div className="panel p-3">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className={`text-lg font-bold font-mono mt-1 ${color}`}>{value}</div>
    </div>
  );
}

function Panel({
  title,
  children,
  right,
}: {
  title: string;
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-semibold tracking-tight text-zinc-200">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

function BestResultsTable({ rows }: { rows: BacktestTicketRow[] }) {
  if (!rows.length) {
    return <p className="text-sm text-zinc-500 italic">Chưa có kết quả nào đạt ngưỡng.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Draw ID</th>
            <th>Predicted</th>
            <th>Result</th>
            <th className="num">Main</th>
            <th className="num">Special</th>
            <th className="num">Gain</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const resultMain = r.result.slice(0, 5);
            const resultSp = r.result[5] ?? null;
            return (
              <tr key={`${r.drawId}-${r.predictIdx}-${r.specialIdx}-${i}`}>
                <td className="font-mono whitespace-nowrap">{r.date}</td>
                <td className="font-mono text-zinc-500">#{r.drawId}</td>
                <td>
                  <TicketNumbers
                    main={r.predicted}
                    special={r.predictedSpecial}
                    resultMain={resultMain}
                    resultSpecial={resultSp}
                    size={5}
                    small
                  />
                </td>
                <td>
                  <TicketNumbers main={resultMain} special={resultSp} small />
                </td>
                <td className={`num font-bold ${r.mainMatch >= 5 ? "text-green-400" : r.mainMatch >= 4 ? "text-amber-400" : ""}`}>
                  {r.mainMatch}
                </td>
                <td className={`num ${r.specialMatch ? "text-green-400" : "text-zinc-500"}`}>{r.specialMatch ? "✓" : "—"}</td>
                <td className="num font-mono">{r.gain > 0 ? fmtVnd(r.gain) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AllRowsTable({ rows }: { rows: BacktestTicketRow[] }) {
  if (!rows.length) return <p className="text-sm text-zinc-500 italic">Không có dữ liệu.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Draw ID</th>
            <th>#</th>
            <th>Predicted</th>
            <th>Result</th>
            <th className="num">Main</th>
            <th className="num">Special</th>
            <th className="num">Gain</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const resultMain = r.result.slice(0, 5);
            const resultSp = r.result[5] ?? null;
            return (
              <tr key={`${r.drawId}-${r.predictIdx}-${r.specialIdx}-${i}`}>
                <td className="font-mono whitespace-nowrap">{r.date}</td>
                <td className="font-mono text-zinc-500">#{r.drawId}</td>
                <td className="text-zinc-500 text-xs">p{r.predictIdx}·s{r.specialIdx}</td>
                <td>
                  <TicketNumbers
                    main={r.predicted}
                    special={r.predictedSpecial}
                    resultMain={resultMain}
                    resultSpecial={resultSp}
                    size={5}
                    small
                  />
                </td>
                <td>
                  <TicketNumbers main={resultMain} special={resultSp} small />
                </td>
                <td className={`num ${r.mainMatch >= 4 ? "text-amber-400 font-bold" : "text-zinc-500"}`}>{r.mainMatch}</td>
                <td className={`num ${r.specialMatch ? "text-green-400" : "text-zinc-500"}`}>{r.specialMatch ? "✓" : "—"}</td>
                <td className="num font-mono text-zinc-400">{r.gain > 0 ? fmtVnd(r.gain) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function LoadingPanel({ message }: { message: string }) {
  return (
    <div className="panel p-12 text-center">
      <div className="inline-block w-6 h-6 border-2 border-amber-400 border-r-transparent rounded-full animate-spin" />
      <p className="mt-3 text-sm text-zinc-400">{message}</p>
    </div>
  );
}
function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="panel p-8 border-red-900/50">
      <h3 className="text-red-400 font-semibold">Lỗi backtest</h3>
      <p className="text-sm text-zinc-400 mt-2 font-mono break-all">{message}</p>
      <button type="button" className="btn-primary mt-4" onClick={onRetry}>
        Thử lại
      </button>
    </div>
  );
}
function EmptyPanel({ onRun }: { onRun: () => void }) {
  return (
    <div className="panel p-12 text-center">
      <h2 className="text-lg font-semibold mb-2">Chưa có kết quả backtest</h2>
      <p className="text-sm text-zinc-400 mb-6">Điều chỉnh tham số bên trái rồi nhấn nút bên dưới.</p>
      <button type="button" className="btn-primary" onClick={onRun}>
        Chạy backtest
      </button>
    </div>
  );
}
