"use client";

import { useEffect, useState } from "react";
import type { BacktestConfig, Draw, PredictionResult, ProductName } from "@/lib/types";
import { NumberBall, TicketNumbers } from "./NumberBall";

interface PredictionViewProps {
  result: PredictionResult | null;
  loading: boolean;
  error: string | null;
  onRun: () => void;
  product: {
    name: ProductName;
    display: string;
    minValue: number;
    maxValue: number;
    sizeOutput: number;
    hasSpecial: boolean;
    specialMin: number;
    specialMax: number;
  };
  latestDraw: Draw | null;
  latestDrawLoading: boolean;
  latestDrawError: string | null;
}

interface EvResponse {
  product: string;
  display: string;
  numTickets: number;
  ticketPrice: number;
  jackpotBase: number;
  historySampleSize: number;
  evPerTicket: number;
  totalEv: number;
  projection: {
    expectedNextJackpot: number;
    expectedRevenue: number;
    expectedTickets: number;
    avgTicketsLastN: number;
    sampleSize: number;
    confidence: "low" | "medium" | "high";
    avgJackpotWinnersLastN: number;
    expectedWinners: {
      jackpot: number;
      nhat: number;
      nhi: number;
      ba: number;
      tu: number;
      nam: number;
      khuyen_khich: number;
    };
    splitMode: boolean;
  };
  breakdown: Array<{
    tier: string;
    displayName: string;
    probability: number;
    expectedPayout: number;
    ev: number;
    splitAdjusted: boolean;
    expectedOtherWinners: number;
  }>;
}

const fmtVnd = (n: number) => `${n.toLocaleString("vi-VN")} ₫`;

export function PredictionView({
  result,
  loading,
  error,
  onRun,
  product,
  latestDraw,
  latestDrawLoading,
  latestDrawError,
}: PredictionViewProps) {
  const [ev, setEv] = useState<EvResponse | null>(null);
  const [evLoading, setEvLoading] = useState(false);
  const [evError, setEvError] = useState<string | null>(null);

  // Fetch EV whenever a new prediction is available.
  useEffect(() => {
    if (!result) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEv(null);
      setEvError(null);
      return;
    }
    setEvLoading(true);
    let cancelled = false;
    setEvLoading(true);
    setEvError(null);
    (async () => {
      try {
        const res = await fetch("/api/ev", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            product: product.name,
            numTickets: result.tickets.length,
            historyLimit: 10,
          }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error ?? `HTTP ${res.status}`);
        }
        const data = (await res.json()) as EvResponse;
        if (cancelled) return;
        setEv(data);
      } catch (e) {
        if (!cancelled) setEvError(String(e));
      } finally {
        if (!cancelled) setEvLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [result, product.name]);
  if (loading) {
    return (
      <div className="panel p-12 text-center">
        <div className="inline-block w-6 h-6 border-2 border-amber-400 border-r-transparent rounded-full animate-spin" />
        <p className="mt-3 text-sm text-zinc-400">Đang sinh vé dự đoán…</p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="panel p-8 border-red-900/50">
        <h3 className="text-red-400 font-semibold">Lỗi dự đoán</h3>
        <p className="text-sm text-zinc-400 mt-2 font-mono break-all">{error}</p>
        <button type="button" className="btn-primary mt-4" onClick={onRun}>
          Thử lại
        </button>
      </div>
    );
  }
  if (!result) {
    return (
      <div className="space-y-6">
        <Header
          title={`Kết quả kỳ quay gần nhất — ${product.display}`}
          subtitle="Dữ liệu được tải tự động. Ấn Dự đoán để sinh vé cho kỳ tiếp theo."
          onAction={onRun}
          actionLabel="Dự đoán kỳ tiếp theo"
        />
        <LatestDrawPanel
          draw={latestDraw}
          loading={latestDrawLoading}
          error={latestDrawError}
          hasSpecial={product.hasSpecial}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Dự đoán {result.productDisplay}</h2>
          <p className="text-xs text-zinc-500 mt-1">
            {result.strategy} · {result.tickets.length} vé ·{" "}
            <span className="text-amber-400 font-mono">≈ {fmtVnd(result.tickets.length * 10000)}</span> · sinh lúc{" "}
            {new Date(result.generatedAt).toLocaleString("vi-VN")}
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={onRun}>
          Dự đoán lại
        </button>
      </div>

      <LatestDrawPanel
        draw={latestDraw}
        loading={latestDrawLoading}
        error={latestDrawError}
        hasSpecial={product.hasSpecial}
        compact
      />

      <EvPanel
        ev={ev}
        loading={evLoading}
        error={evError}
        numTickets={result.tickets.length}
      />

      <section className="panel p-4">
        <h3 className="text-sm font-semibold tracking-tight mb-3">Vé dự đoán cho kỳ tiếp theo</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {result.tickets.map((t, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-zinc-900 border border-zinc-800"
            >
              <span className="w-6 h-6 rounded-full bg-amber-500/20 text-amber-300 text-xs font-mono flex items-center justify-center">
                {idx + 1}
              </span>
              <TicketNumbers
                main={t.predicted}
                special={t.predictedSpecial}
                size={product.sizeOutput}
              />
            </div>
          ))}
        </div>
      </section>

      <ConfigSummary config={result.config} />
    </div>
  );
}

function Header({
  title,
  subtitle,
  onAction,
  actionLabel,
}: {
  title: string;
  subtitle: string;
  onAction: () => void;
  actionLabel: string;
}) {
  return (
    <div className="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h2 className="text-xl font-bold tracking-tight">{title}</h2>
        <p className="text-xs text-zinc-500 mt-1">{subtitle}</p>
      </div>
      <button type="button" className="btn-primary" onClick={onAction}>
        {actionLabel}
      </button>
    </div>
  );
}

function LatestDrawPanel({
  draw,
  loading,
  error,
  hasSpecial,
  compact = false,
}: {
  draw: Draw | null;
  loading: boolean;
  error: string | null;
  hasSpecial: boolean;
  compact?: boolean;
}) {
  return (
    <section className="panel p-4">
      <h3 className="text-sm font-semibold tracking-tight mb-3">Kỳ quay gần nhất</h3>
      {loading ? (
        <div className="text-sm text-zinc-500 italic">Đang tải…</div>
      ) : error ? (
        <div className="text-sm text-red-400">Lỗi tải: {error}</div>
      ) : !draw ? (
        <div className="text-sm text-zinc-500 italic">Chưa có dữ liệu kỳ quay.</div>
      ) : (
        <div className={compact ? "space-y-3" : "space-y-4"}>
          <DrawHeader draw={draw} hasSpecial={hasSpecial} />
          {draw.prizes && draw.prizes.length > 0 ? (
            <PrizeTable prizes={draw.prizes} hasSpecial={hasSpecial} />
          ) : (
            <p className="text-xs text-zinc-500 italic">Không có dữ liệu giải cho kỳ này.</p>
          )}
        </div>
      )}
    </section>
  );
}

function DrawHeader({ draw, hasSpecial }: { draw: Draw; hasSpecial: boolean }) {
  const main = hasSpecial ? draw.result.slice(0, 5) : draw.result;
  const special = hasSpecial ? draw.result[5] ?? null : null;
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="flex flex-col">
        <span className="text-xs text-zinc-500 font-mono">{draw.date}</span>
        <span className="text-[10px] text-zinc-600 font-mono">#{draw.id}</span>
      </div>
      <div className="flex items-center gap-2">
        <NumberRowLarge numbers={main} />
        {special != null && (
          <span className="inline-flex items-center gap-1.5">
            <span className="text-zinc-600">+</span>
            <NumberBall value={special} variant="special" />
          </span>
        )}
      </div>
    </div>
  );
}

function NumberRowLarge({ numbers }: { numbers: number[] }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {numbers.map((n, idx) => (
        <NumberBall key={`${idx}-${n}`} value={n} />
      ))}
    </span>
  );
}

const TIER_ORDER = [
  "Giải Độc Đắc",
  "Giải Nhất",
  "Giải Nhì",
  "Giải Ba",
  "Giải Tư",
  "Giải Năm",
  "Giải Khuyến Khích",
  "Giải Khuyến khích",
  "Khuyến Khích",
  "Khuyến khích",
];

function parseVnd(value: unknown): number {
  if (typeof value === "number") return Math.trunc(value);
  if (typeof value === "string") {
    const cleaned = value.replace(/[.,\s]/g, "");
    if (!cleaned) return 0;
    const n = Number(cleaned);
    return Number.isFinite(n) ? Math.trunc(n) : 0;
  }
  return 0;
}

function PrizeTable({ prizes, hasSpecial }: { prizes: { prize_name: string; prize_value: string; winners_count: string }[]; hasSpecial: boolean }) {
  // Order by canonical tier order; preserve only first-seen for aliases.
  const seen = new Set<string>();
  const ordered = [...prizes]
    .map((p) => ({ ...p, key: p.prize_name?.trim() ?? "" }))
    .filter((p) => {
      if (!p.key) return false;
      if (seen.has(p.key)) return false;
      seen.add(p.key);
      return true;
    })
    .sort((a, b) => {
      const ai = TIER_ORDER.indexOf(a.key);
      const bi = TIER_ORDER.indexOf(b.key);
      if (ai === -1 && bi === -1) return 0;
      if (ai === -1) return 1;
      if (bi === -1) return -1;
      return ai - bi;
    });

  // Compute totals.
  let totalWinners = 0;
  let totalPayout = 0;
  let ddValue = 0;
  for (const p of ordered) {
    const w = Number(String(p.winners_count).replace(/[.,\s]/g, "")) || 0;
    const v = parseVnd(p.prize_value);
    totalWinners += w;
    if (p.key === "Giải Độc Đắc") ddValue = v;
    else totalPayout += w * v;
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        <SummaryStat label="Tổng người trúng" value={totalWinners.toLocaleString("vi-VN")} />
        <SummaryStat label="Tổng tiền trả (không tính Độc Đắc)" value={fmtVnd(totalPayout)} />
        {hasSpecial && (
          <SummaryStat
            label="Giải Độc Đắc (jackpot)"
            value={ddValue > 0 ? fmtVnd(ddValue) : "—"}
            tone={ddValue >= 15_000_000_000 ? "amber" : "muted"}
            hint={ddValue >= 15_000_000_000 ? "Vượt ngưỡng 15B → kích hoạt split rule" : undefined}
          />
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Giải</th>
              <th className="num">Số người trúng</th>
              <th className="num">Giá trị / người</th>
              <th className="num">Tổng chi</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((p) => {
              const w = Number(String(p.winners_count).replace(/[.,\s]/g, "")) || 0;
              const v = parseVnd(p.prize_value);
              const total = w * v;
              const isDD = p.key === "Giải Độc Đắc";
              return (
                <tr key={p.key} className={isDD ? "bg-amber-500/5" : ""}>
                  <td className={isDD ? "text-amber-300 font-semibold" : ""}>{p.key}</td>
                  <td className="num">{w.toLocaleString("vi-VN")}</td>
                  <td className="num font-mono">{v > 0 ? fmtVnd(v) : "—"}</td>
                  <td className="num font-mono text-zinc-400">{total > 0 ? fmtVnd(total) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryStat({
  label,
  value,
  tone = "muted",
  hint,
}: {
  label: string;
  value: string;
  tone?: "muted" | "amber";
  hint?: string;
}) {
  const color = tone === "amber" ? "text-amber-300" : "text-zinc-200";
  return (
    <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-2.5">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className={`text-sm font-bold font-mono mt-0.5 ${color}`}>{value}</div>
      {hint && <div className="text-[10px] text-amber-400/80 mt-0.5">{hint}</div>}
    </div>
  );
}

function ConfigSummary({ config }: { config: BacktestConfig }) {
  return (
    <section className="panel p-4">
      <h3 className="text-sm font-semibold tracking-tight mb-3">Cấu hình đã dùng</h3>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1 text-xs font-mono">
        <Row k="TPD" v={String(config.tpd)} />
        <Row k="Cold.lookback" v={`${config.cold.lookbackDays} ngày`} />
        <Row k="Cold.weight" v={config.cold.selectionWeight.toFixed(2)} />
        <Row k="Steiner.lookback" v={`${config.steiner.lookbackDays} ngày`} />
        <Row
          k="Steiner.filters"
          v={`consec=${config.steiner.filterConsecutive ? "Y" : "N"} · decade=${config.steiner.filterSameDecade ? "Y" : "N"}`}
        />
        <Row k="Steiner S(t,k,v)" v={`(${config.steiner.t}, ${config.steiner.k}, ${config.steiner.v})`} />
        <Row k="Inverse.topK" v={String(config.inverse.topK)} />
        <Row k="Specials.topN" v={String(config.specials.topN)} />
        <Row k="Specials.mode" v={config.specials.mode} />
        <Row k="Specials.lookback" v={`${config.specials.lookbackDraws} kỳ`} />
        <Row k="Specials.offset" v={`${config.specials.offsetDraws} kỳ`} />
        <Row k="DD filter" v={config.ddFilter.enabled ? "BẬT" : "TẮT"} />
        <Row k="DD threshold" v={fmtVnd(config.ddFilter.threshold)} />
        <Row k="date_from" v={config.dateFrom ?? "(tất cả)"} />
        <Row k="date_to" v={config.dateTo ?? "(tất cả)"} />
      </div>
    </section>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <>
      <span className="text-zinc-500">{k}</span>
      <span className="text-zinc-200 col-span-1 md:col-span-2">{v}</span>
    </>
  );
}

// ---------- EV panel ----------

function EvPanel({
  ev,
  loading,
  error,
  numTickets,
}: {
  ev: EvResponse | null;
  loading: boolean;
  error: string | null;
  numTickets: number;
}) {
  if (loading) {
    return (
      <section className="panel p-4">
        <h3 className="text-sm font-semibold tracking-tight mb-3">Ước lượng EV kỳ tới</h3>
        <div className="text-sm text-zinc-500 italic">Đang tính toán dựa trên {numTickets} vé…</div>
      </section>
    );
  }
  if (error) {
    return (
      <section className="panel p-4">
        <h3 className="text-sm font-semibold tracking-tight mb-3">Ước lượng EV kỳ tới</h3>
        <div className="text-sm text-red-400">Lỗi: {error}</div>
      </section>
    );
  }
  if (!ev) return null;

  const isPositive = ev.totalEv > 0;

  // Recommendation thresholds (in VND per ticket, "gross" terms).
  //   EV > 0          → strongly positive (split mode, J > 12B & no winner)
  //   −5,000 < EV ≤ 0 → wait, getting close (J > 12B, but split may be partial)
  //   EV ≤ −5,000     → no (no-split mode, Jackpot too small)
  // Chosen to align with: no-split break-even is J ≈ 33.6B, and split-mode
  // activation gives EV > +30K/vé.
  const recommendation =
    ev.evPerTicket > 0
      ? { label: "NÊN MUA", tone: "good" as const, reason: "EV dương, có thể là split mode" }
      : ev.evPerTicket > -5_000
        ? {
            label: "CHỜ THÊM",
            tone: "amber" as const,
            reason: "EV gần 0, Jackpot chưa đủ lớn để split",
          }
        : {
            label: "KHÔNG MUA",
            tone: "bad" as const,
            reason: "EV âm nặng, Jackpot quá nhỏ (cần J > 12B + split)",
          };

  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between gap-4 flex-wrap mb-3">
        <h3 className="text-sm font-semibold tracking-tight">Ước lượng EV kỳ tới</h3>
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border font-semibold ${
              recommendation.tone === "good"
                ? "border-good/60 text-good bg-good/5"
                : recommendation.tone === "amber"
                  ? "border-amber-500/60 text-amber-300 bg-amber-500/5"
                  : "border-bad/60 text-bad bg-bad/5"
            }`}
            title={recommendation.reason}
          >
            {recommendation.label}
          </span>
          {ev.projection.splitMode && (
            <span
              className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-amber-500/60 text-amber-300 bg-amber-500/5"
              title="Jackpot dự kiến vượt 12B và không có người trúng → áp dụng split rule (1/3 Nhất, 1/6 mỗi Nhì/Ba/Tư/Năm)"
            >
              split mode
            </span>
          )}
          <span
            className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border ${
              ev.projection.confidence === "high"
                ? "border-good/40 text-good"
                : ev.projection.confidence === "medium"
                  ? "border-amber-500/40 text-amber-300"
                  : "border-zinc-700 text-zinc-500"
            }`}
          >
            độ tin cậy: {ev.projection.confidence}
          </span>
        </div>
      </div>

      <p className="text-[11px] text-zinc-500 mb-3">
        Jackpot dự kiến = J_cuối + 0.55 × E[doanh_thu]. E[doanh thu] = trung bình {ev.projection.sampleSize} kỳ gần nhất.
        P(win) cố định theo tổ hợp 5/35 × 12 = 3.895.584 vé.
        {ev.projection.splitMode && (
          <>
            {" "}
            <span className="text-amber-300">
              Split rule áp dụng: giải Nhất→Năm nhận thêm 1/6 (Nhất: 1/3) Jackpot chia đều; payout các tier này tăng mạnh.
            </span>
          </>
        )}
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <Stat
          label="Jackpot dự kiến"
          value={fmtVnd(ev.projection.expectedNextJackpot)}
          tone="amber"
        />
        <Stat
          label="Vé bán ước lượng"
          value={ev.projection.expectedTickets.toLocaleString("vi-VN")}
        />
        <Stat
          label="EV / vé"
          value={`${ev.evPerTicket >= 0 ? "+" : ""}${fmtVnd(Math.round(ev.evPerTicket))}`}
          tone={isPositive ? "good" : "bad"}
        />
        <Stat
          label={`Tổng EV (${ev.numTickets} vé)`}
          value={`${ev.totalEv >= 0 ? "+" : ""}${fmtVnd(Math.round(ev.totalEv))}`}
          tone={isPositive ? "good" : "bad"}
        />
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Tier</th>
              <th className="num">P(win)</th>
              <th className="num">E[w khác]</th>
              <th className="num">E[payout]</th>
              <th className="num">EV / vé</th>
            </tr>
          </thead>
          <tbody>
            {ev.breakdown.map((b) => (
              <tr key={b.tier} className={b.splitAdjusted ? "bg-amber-500/5" : ""}>
                <td>
                  {b.displayName}
                  {b.splitAdjusted && (
                    <span className="ml-1.5 text-[9px] uppercase tracking-wider text-amber-400">
                      split
                    </span>
                  )}
                </td>
                <td className="num font-mono">{b.probability.toExponential(2)}</td>
                <td className="num font-mono text-zinc-500">
                  {b.expectedOtherWinners.toLocaleString("vi-VN")}
                </td>
                <td className="num font-mono">{fmtVnd(b.expectedPayout)}</td>
                <td
                  className={`num font-mono ${b.ev >= 0 ? "text-good" : "text-bad"}`}
                >
                  {b.ev >= 0 ? "+" : ""}
                  {fmtVnd(Math.round(b.ev * 100) / 100)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[10px] text-zinc-600 mt-2">
        {ev.projection.splitMode
          ? "Split mode: E[payout] tier Nhất→Năm đã cộng thêm 1/6 (hoặc 1/3 cho Nhất) × Jackpot dự kiến, chia cho số người trúng trung bình +1 (gồm ta)."
          : "Chế độ thường: payout tier Nhất→Năm theo bảng cố định (10M/5M/500K/100K/30K)."}
        {ev.projection.avgJackpotWinnersLastN > 0
          ? ` Trung bình ${ev.projection.avgJackpotWinnersLastN} người trúng Jackpot / kỳ (gần đây).`
          : " Chưa có kỳ nào gần đây có người trúng Jackpot → payout Jackpot ước lượng có thể rất lớn."}
      </p>
    </section>
  );
}

function Stat({
  label,
  value,
  tone = "muted",
}: {
  label: string;
  value: string;
  tone?: "muted" | "amber" | "good" | "bad";
}) {
  const color =
    tone === "amber"
      ? "text-amber-300"
      : tone === "good"
        ? "text-good"
        : tone === "bad"
          ? "text-bad"
          : "text-zinc-200";
  return (
    <div className="rounded-lg bg-zinc-900 border border-zinc-800 p-2.5">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className={`text-sm font-bold font-mono mt-0.5 ${color}`}>{value}</div>
    </div>
  );
}
