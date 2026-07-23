/// <reference types="vite/client" />
import type {
  ApiHealth,
  BacktestRequest,
  BacktestResult,
  GenerateRequest,
  GenerateResult,
  PipelineSpec,
  ProductInfo,
  StrategyMetadata,
} from './types.js';

const API_BASE = import.meta.env.VITE_API_BASE || '';

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return (await res.json()) as T;
}

export type {
  ApiHealth,
  BacktestRequest,
  BacktestResult,
  GenerateRequest,
  GenerateResult,
  GroupSpec,
  PipelineSpec,
  PostFilterSpec,
  ProductInfo,
  StrategyMetadata,
} from './types.js';

export const apiClient = {
  health: () => api<{ status: string }>('/api/health'),
  products: () => api<string[]>('/api/products'),
  product: (name: string) => api<ProductInfo>(`/api/products/${name}`),
  strategies: () => api<StrategyMetadata[]>('/api/strategies'),
  generate: (pipeline: PipelineSpec, target_date?: string) =>
    api<GenerateResult>('/api/generate', {
      method: 'POST',
      body: JSON.stringify({ pipeline, target_date } satisfies GenerateRequest),
    }),
  backtest: (pipeline: PipelineSpec, date_from: string, date_to: string, ticket_count: number) =>
    api<BacktestResult>('/api/backtest', {
      method: 'POST',
      body: JSON.stringify({ pipeline, date_from, date_to, ticket_count } satisfies BacktestRequest),
    }),
};

export function formatCurrency(n: number): string {
  return `${n.toLocaleString('en-US')} đ`;
}

export function formatNumber(n: number, digits = 2): string {
  return n.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatPercent(n: number): string {
  return `${(n * 100).toLocaleString('en-US', { maximumFractionDigits: 2 })}%`;
}
