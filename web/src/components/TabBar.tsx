"use client";

interface TabBarProps {
  active: "backtest" | "prediction";
  onChange: (tab: "backtest" | "prediction") => void;
}

const TABS: Array<{ key: "backtest" | "prediction"; label: string }> = [
  { key: "prediction", label: "Dự đoán" },
  { key: "backtest", label: "Backtest" },
];

export function TabBar({ active, onChange }: TabBarProps) {
  return (
    <div className="flex items-center border-b border-zinc-800 px-4 gap-2">
      {TABS.map((t) => (
        <button
          key={t.key}
          type="button"
          className="tab-button"
          data-active={active === t.key}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
