"use client";

import { useState } from "react";

interface SectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: string;
}

export function ConfigSection({ title, defaultOpen = true, children, badge }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-b border-zinc-800 last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left hover:bg-zinc-900/50"
      >
        <span className="text-xs font-semibold tracking-wider text-zinc-400 uppercase">{title}</span>
        <span className="flex items-center gap-2">
          {badge && <span className="text-[10px] font-mono text-amber-400">{badge}</span>}
          <span className="text-zinc-500 text-xs w-3 inline-block text-center">{open ? "▾" : "▸"}</span>
        </span>
      </button>
      {open && <div className="px-4 pb-4 space-y-3">{children}</div>}
    </section>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  disabled?: boolean;
}

export function NumberField({ label, value, onChange, min, max, step = 1, hint, disabled }: NumberFieldProps) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <input
        type="number"
        className="field-input"
        value={value}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) onChange(n);
        }}
      />
      {hint && <p className="text-[10px] text-zinc-500 mt-1">{hint}</p>}
    </div>
  );
}

interface FloatFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  disabled?: boolean;
}

export function FloatField({ label, value, onChange, min, max, step = 0.05, hint, disabled }: FloatFieldProps) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <input
        type="number"
        className="field-input"
        value={value}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onChange={(e) => {
          const n = Number(e.target.value);
          if (Number.isFinite(n)) onChange(n);
        }}
      />
      {hint && <p className="text-[10px] text-zinc-500 mt-1">{hint}</p>}
    </div>
  );
}

interface SelectFieldProps<T extends string> {
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: Array<{ value: T; label: string }>;
  disabled?: boolean;
  hint?: string;
}

export function SelectField<T extends string>({ label, value, onChange, options, disabled, hint }: SelectFieldProps<T>) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <select
        className="field-input"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {hint && <p className="text-[10px] text-zinc-500 mt-1">{hint}</p>}
    </div>
  );
}

interface SwitchFieldProps {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
  hint?: string;
  disabled?: boolean;
}

export function SwitchField({ label, value, onChange, hint, disabled }: SwitchFieldProps) {
  return (
    <div>
      <label className="flex items-center justify-between gap-2 cursor-pointer">
        <span className="field-label !mb-0">{label}</span>
        <span
          role="switch"
          aria-checked={value}
          onClick={() => !disabled && onChange(!value)}
          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
            value ? "bg-amber-500" : "bg-zinc-700"
          } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        >
          <span
            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-zinc-900 transition-transform ${
              value ? "translate-x-5" : "translate-x-1"
            }`}
          />
        </span>
      </label>
      {hint && <p className="text-[10px] text-zinc-500 mt-1">{hint}</p>}
    </div>
  );
}

interface DateFieldProps {
  label: string;
  value: string | null;
  onChange: (v: string | null) => void;
  disabled?: boolean;
}

export function DateField({ label, value, onChange, disabled }: DateFieldProps) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <div className="flex gap-1">
        <input
          type="date"
          className="field-input"
          value={value ?? ""}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value || null)}
        />
        {value && (
          <button
            type="button"
            className="btn-ghost !py-1 !px-2 text-xs"
            onClick={() => onChange(null)}
            title="Xóa"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
