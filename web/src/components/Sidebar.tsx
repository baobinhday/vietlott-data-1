"use client";

import { ConfigSection, DateField, FloatField, NumberField, SelectField, SwitchField } from "./FormFields";
import type { BacktestConfig, ProductName, SpecialsMode } from "@/lib/types";

interface ProductInfo {
  name: ProductName;
  display: string;
  minValue: number;
  maxValue: number;
  sizeOutput: number;
  hasSpecial: boolean;
  specialMin: number;
  specialMax: number;
}

interface SidebarProps {
  products: ProductInfo[];
  product: ProductName;
  onProductChange: (p: ProductName) => void;
  strategy: string;
  config: BacktestConfig;
  onConfigChange: (cfg: BacktestConfig) => void;
  onRunBacktest: () => void;
  onRunPredict: () => void;
  backtestLoading: boolean;
  predictionLoading: boolean;
}

const SPECIALS_MODE_OPTIONS: Array<{ value: SpecialsMode; label: string }> = [
  { value: "hot", label: "hot — tần suất cao" },
  { value: "cold", label: "cold — tần suất thấp" },
  { value: "long_absence", label: "long_absence — lâu chưa về" },
  { value: "markov_steiner", label: "markov_steiner — Markov + Steiner" },
  { value: "intersection_la_mc", label: "intersection_la_mc — giao LongAbsence × Markov" },
];

export function Sidebar({
  products,
  product,
  onProductChange,
  strategy,
  config,
  onConfigChange,
  onRunBacktest,
  onRunPredict,
  backtestLoading,
  predictionLoading,
}: SidebarProps) {
  const update = (key: keyof BacktestConfig, value: BacktestConfig[keyof BacktestConfig]) => {
    onConfigChange({ ...config, [key]: value });
  };
  type ObjectSectionKey = {
    [K in keyof BacktestConfig]: BacktestConfig[K] extends Record<string, unknown> ? K : never;
  }[keyof BacktestConfig];
  const updateNested = <S extends ObjectSectionKey>(
    section: S,
    field: keyof BacktestConfig[S] & string,
    value: BacktestConfig[S][keyof BacktestConfig[S] & string],
  ) => {
    const next: BacktestConfig = {
      ...config,
      [section]: {
        ...(config[section] as Record<string, unknown>),
        [field]: value,
      } as BacktestConfig[S],
    } as BacktestConfig;
    onConfigChange(next);
  };

  return (
    <aside className="w-80 shrink-0 border-r border-zinc-800 bg-zinc-950 flex flex-col min-h-0">
      <header className="p-4 border-b border-zinc-800">
        <h1 className="text-base font-bold tracking-tight text-amber-400">Vietlott Lab</h1>
        <p className="text-[11px] text-zinc-500 mt-1">Backtest & dự đoán với Inverse Hybrid: Cold → Steiner</p>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <ConfigSection title="Sản phẩm" defaultOpen>
          <div>
            <label className="field-label">Loại Vietlott</label>
            <select
              className="field-input"
              value={product}
              onChange={(e) => onProductChange(e.target.value as ProductName)}
            >
              {products.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.display}
                </option>
              ))}
            </select>
          </div>
        </ConfigSection>

        <ConfigSection title="Chiến thuật" defaultOpen badge="1/1">
          <div>
            <label className="field-label">Chiến thuật</label>
            <input className="field-input bg-zinc-900 cursor-not-allowed" value={strategy} readOnly />
            <p className="text-[10px] text-zinc-500 mt-1">Hiện tại chỉ hỗ trợ 1 chiến thuật.</p>
          </div>
          <NumberField
            label="TPD (tickets / draw)"
            value={config.tpd}
            onChange={(v) => update("tpd", v)}
            min={1}
            max={50}
            hint="Số vé sinh ra mỗi kỳ quay (Python: render_prediction_535.TPD)."
          />
        </ConfigSection>

        <ConfigSection title="Cold Numbers" badge="voter">
          <NumberField
            label="lookback_days"
            value={config.cold.lookbackDays}
            onChange={(v) => updateNested("cold", "lookbackDays", v)}
            min={30}
            max={3650}
            hint="Số ngày nhìn lại để tính tần suất."
          />
          <FloatField
            label="selection_weight"
            value={config.cold.selectionWeight}
            onChange={(v) => updateNested("cold", "selectionWeight", v)}
            min={0}
            max={1}
            step={0.05}
            hint="0 = random, 1 = chọn theo tần suất thuần."
          />
        </ConfigSection>

        <ConfigSection title="Steiner" badge="picker">
          <NumberField
            label="lookback_days"
            value={config.steiner.lookbackDays}
            onChange={(v) => updateNested("steiner", "lookbackDays", v)}
            min={30}
            max={3650}
          />
          <SwitchField
            label="filter_consecutive"
            value={config.steiner.filterConsecutive}
            onChange={(v) => updateNested("steiner", "filterConsecutive", v)}
            hint="Loại bỏ block có 2 số liên tiếp."
          />
          <SwitchField
            label="filter_same_decade"
            value={config.steiner.filterSameDecade}
            onChange={(v) => updateNested("steiner", "filterSameDecade", v)}
            hint="Loại bỏ block cả 3 số cùng hàng chục."
          />
          <div className="grid grid-cols-3 gap-2">
            <NumberField
              label="t (strength)"
              value={config.steiner.t}
              onChange={(v) => updateNested("steiner", "t", v)}
              min={2}
              max={2}
            />
            <NumberField
              label="k (block)"
              value={config.steiner.k}
              onChange={(v) => updateNested("steiner", "k", v)}
              min={2}
              max={5}
            />
            <NumberField
              label="v (points)"
              value={config.steiner.v}
              onChange={(v) => updateNested("steiner", "v", v)}
              min={5}
              max={55}
            />
          </div>
        </ConfigSection>

        <ConfigSection title="Inverse Hybrid">
          <NumberField
            label="top_k (pool size)"
            value={config.inverse.topK}
            onChange={(v) => updateNested("inverse", "topK", v)}
            min={5}
            max={50}
            hint="Cold Numbers đề xuất top_k số, Steiner chọn numberPredict từ pool. coverage = TPD (hard-coded trong Python)."
          />
        </ConfigSection>

        <ConfigSection title="Specials (số đặc biệt)" badge="5/35">
          <SwitchField
            label="Bật bộ lọc đặc biệt"
            value={config.specials.topN > 0}
            onChange={(v) => updateNested("specials", "topN", v ? Math.max(1, config.specials.topN) : 0)}
            hint="Bật để chọn số đặc biệt theo mode bên dưới (chỉ áp dụng khi sản phẩm yêu cầu)."
          />
          <NumberField
            label="top_n"
            value={config.specials.topN}
            onChange={(v) => updateNested("specials", "topN", v)}
            min={0}
            max={20}
          />
          <SelectField
            label="mode"
            value={config.specials.mode}
            onChange={(v) => updateNested("specials", "mode", v)}
            options={SPECIALS_MODE_OPTIONS}
          />
          <NumberField
            label="lookback_draws"
            value={config.specials.lookbackDraws}
            onChange={(v) => updateNested("specials", "lookbackDraws", v)}
            min={1}
            max={500}
          />
          <NumberField
            label="offset_draws"
            value={config.specials.offsetDraws}
            onChange={(v) => updateNested("specials", "offsetDraws", v)}
            min={0}
            max={500}
            hint="Số kỳ lùi lại trước target_date."
          />
        </ConfigSection>

        <ConfigSection title="Độc Đắc filter (5/35)" badge="DD">
          <SwitchField
            label="dd_filter_enabled"
            value={config.ddFilter.enabled}
            onChange={(v) => updateNested("ddFilter", "enabled", v)}
            hint="Chỉ mua vé ở các kỳ có Giải Độc Đắc > threshold."
          />
          <NumberField
            label="dd_threshold (VND)"
            value={config.ddFilter.threshold}
            onChange={(v) => updateNested("ddFilter", "threshold", v)}
            min={0}
            step={1_000_000_000}
            hint="Mặc định 15B (15.000.000.000)."
          />
        </ConfigSection>

        <ConfigSection title="Cửa sổ backtest" defaultOpen>
          <DateField
            label="date_from"
            value={config.dateFrom}
            onChange={(v) => update("dateFrom", v)}
          />
          <DateField label="date_to" value={config.dateTo} onChange={(v) => update("dateTo", v)} />
        </ConfigSection>
      </div>

      <footer className="border-t border-zinc-800 p-4 flex flex-col gap-2 bg-zinc-950">
        <button
          type="button"
          className="btn-primary w-full"
          onClick={onRunPredict}
          disabled={predictionLoading}
        >
          {predictionLoading ? "Đang dự đoán…" : "Dự đoán kỳ tiếp theo"}
        </button>
        <button
          type="button"
          className="btn-ghost w-full"
          onClick={onRunBacktest}
          disabled={backtestLoading}
        >
          {backtestLoading ? "Đang chạy backtest…" : "Chạy backtest"}
        </button>
      </footer>
    </aside>
  );
}
