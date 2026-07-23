import type { BacktestResult, GenerateResult, GroupSpec, PipelineSpec, ProductInfo, StrategyMetadata, StrategyStep } from './types.js';

export interface AppState {
  products: ProductInfo[];
  strategies: StrategyMetadata[];
  pipeline: PipelineSpec;
  backtestTicketCount: number;
  generateResult: GenerateResult | null;
  backtestResult: BacktestResult | null;
  loading: { generate: boolean; backtest: boolean };
  error: string | null;
  theme: 'dark' | 'light';
}

const defaultFilters: AppState['pipeline']['post_filters'] = {
  min_sum: null,
  max_sum: null,
  min_even: null,
  max_even: null,
  min_odd: null,
  max_odd: null,
};

export function createDefaultPipeline(): PipelineSpec {
  return {
    product: 'power_655',
    groups: [],
    combiner: { method: 'concatenate' },
    post_filters: defaultFilters,
    ticket_count: 1,
  };
}

function createDefaultStep(strategyKey: string, strategies: StrategyMetadata[]): StrategyStep {
  const strategy = strategies.find((s) => s.key === strategyKey) || strategies[0];
  const params: Record<string, unknown> = {};
  for (const p of strategy?.params || []) {
    params[p.name] = p.default ?? null;
  }
  return {
    strategy: strategy?.key || strategyKey,
    params,
    pool_size: 10,
  };
}

const PIPELINE_KEY = 'vietlott.pipeline.v2';
const BACKTEST_TICKET_COUNT_KEY = 'vietlott.backtest_ticket_count';

interface LegacyGroupSpec {
  name: string;
  strategy: string;
  params: Record<string, unknown>;
  pool_size: number;
  pick_count: number;
}

function migrateGroup(group: LegacyGroupSpec | GroupSpec): GroupSpec {
  if ('strategies' in group && Array.isArray(group.strategies)) {
    return group as GroupSpec;
  }
  const legacy = group as LegacyGroupSpec;
  return {
    name: legacy.name,
    strategies: [
      {
        strategy: legacy.strategy,
        params: legacy.params,
        pool_size: legacy.pool_size,
      },
    ],
    pick_count: legacy.pick_count,
  };
}

function loadSavedPipeline(): PipelineSpec | null {
  try {
    const raw = localStorage.getItem(PIPELINE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PipelineSpec> & { groups?: (GroupSpec | LegacyGroupSpec)[] };
    if (!parsed || typeof parsed !== 'object') return null;
    return {
      ...createDefaultPipeline(),
      ...parsed,
      groups: Array.isArray(parsed.groups) ? parsed.groups.map(migrateGroup) : [],
      combiner: { method: 'concatenate' },
      post_filters: { ...defaultFilters, ...(parsed.post_filters || {}) },
    };
  } catch {
    return null;
  }
}

function loadSavedBacktestTicketCount(): number {
  try {
    const raw = localStorage.getItem(BACKTEST_TICKET_COUNT_KEY);
    if (!raw) return 1;
    const n = parseInt(raw, 10);
    return Number.isNaN(n) ? 1 : Math.max(1, Math.min(50, n));
  } catch {
    return 1;
  }
}

function savePipeline(pipeline: PipelineSpec): void {
  try {
    localStorage.setItem(PIPELINE_KEY, JSON.stringify(pipeline));
  } catch {
    // ignore storage errors
  }
}

const savedTheme = localStorage.getItem('theme') as AppState['theme'] | null;

const state: AppState = {
  products: [],
  strategies: [],
  pipeline: loadSavedPipeline() || createDefaultPipeline(),
  backtestTicketCount: loadSavedBacktestTicketCount(),
  generateResult: null,
  backtestResult: null,
  loading: { generate: false, backtest: false },
  error: null,
  theme: savedTheme === 'light' ? 'light' : 'dark',
};

const listeners: Set<() => void> = new Set();

export function getState(): Readonly<AppState> {
  return state;
}

export function setState(partial: Partial<AppState>): void {
  let changed = false;
  for (const key of Object.keys(partial) as (keyof AppState)[]) {
    if (state[key] !== partial[key]) {
      (state as AppState)[key] = partial[key] as never;
      changed = true;
    }
  }
  if (changed) {
    if ('pipeline' in partial) {
      savePipeline(state.pipeline);
    }
    for (const fn of listeners) fn();
  }
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function setPipeline(partial: Partial<PipelineSpec>): void {
  setState({
    pipeline: { ...state.pipeline, ...partial },
  });
}

export function setBacktestTicketCount(count: number): void {
  const n = Math.max(1, Math.min(50, count));
  try {
    localStorage.setItem(BACKTEST_TICKET_COUNT_KEY, String(n));
  } catch {
    // ignore
  }
  setState({ backtestTicketCount: n });
}

export function setGroup(index: number, group: GroupSpec): void {
  const groups = state.pipeline.groups.map((g, i) => (i === index ? group : g));
  setPipeline({ groups });
}

export function addGroup(): void {
  if (state.pipeline.groups.length >= 5) return;
  const strategies = state.strategies;
  setPipeline({
    groups: [
      ...state.pipeline.groups,
      {
        name: `Group ${state.pipeline.groups.length + 1}`,
        strategies: [createDefaultStep('frequency', strategies)],
        pick_count: 1,
      },
    ],
  });
}

export function removeGroup(index: number): void {
  if (state.pipeline.groups.length <= 1) return;
  const groups = state.pipeline.groups.filter((_, i) => i !== index);
  setPipeline({ groups });
}

export function moveGroup(from: number, to: number): void {
  const groups = [...state.pipeline.groups];
  const [moved] = groups.splice(from, 1);
  groups.splice(to, 0, moved);
  setPipeline({ groups });
}

export function addStepToGroup(groupIndex: number): void {
  const group = state.pipeline.groups[groupIndex];
  if (!group) return;
  const strategies = state.strategies;
  const lastStep = group.strategies[group.strategies.length - 1];
  const newStep = createDefaultStep(lastStep?.strategy || 'frequency', strategies);
  const updated: GroupSpec = {
    ...group,
    strategies: [...group.strategies, { ...newStep, pool_size: null }],
  };
  setGroup(groupIndex, updated);
}

export function removeStepFromGroup(groupIndex: number, stepIndex: number): void {
  const group = state.pipeline.groups[groupIndex];
  if (!group || group.strategies.length <= 1) return;
  const strategies = group.strategies.filter((_, i) => i !== stepIndex);
  setGroup(groupIndex, { ...group, strategies });
}

export function reorderStepsInGroup(groupIndex: number, fromIndex: number, toIndex: number): void {
  const group = state.pipeline.groups[groupIndex];
  if (!group) return;
  const strategies = [...group.strategies];
  const [moved] = strategies.splice(fromIndex, 1);
  strategies.splice(toIndex, 0, moved);
  setGroup(groupIndex, { ...group, strategies });
}

export function updateStep(
  groupIndex: number,
  stepIndex: number,
  partial: Partial<StrategyStep>
): void {
  const group = state.pipeline.groups[groupIndex];
  if (!group) return;
  const strategies = group.strategies.map((s, i) => (i === stepIndex ? { ...s, ...partial } : s));
  setGroup(groupIndex, { ...group, strategies });
}

export function updateStepParam(
  groupIndex: number,
  stepIndex: number,
  paramName: string,
  value: unknown
): void {
  const group = state.pipeline.groups[groupIndex];
  if (!group) return;
  const strategies = group.strategies.map((s, i) => {
    if (i !== stepIndex) return s;
    return { ...s, params: { ...s.params, [paramName]: value } };
  });
  setGroup(groupIndex, { ...group, strategies });
}

export function toggleTheme(): void {
  const next = state.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', next);
  setState({ theme: next });
  document.documentElement.setAttribute('data-theme', next);
}

export function initTheme(): void {
  document.documentElement.setAttribute('data-theme', state.theme);
}

export function setError(error: string | null): void {
  setState({ error });
}

export function setLoading(key: keyof AppState['loading'], value: boolean): void {
  setState({ loading: { ...state.loading, [key]: value } });
}

export interface PresetConfig {
  name: string;
  description: string;
  groups: GroupSpec[];
}

export const PIPELINE_PRESETS: PresetConfig[] = [
  {
    name: 'Steiner top numbers',
    description: 'Pick 6 numbers from the top 15 candidates chosen by the Steiner strategy.',
    groups: [
      {
        name: 'Pool Steiner',
        strategies: [{ strategy: 'steiner', params: { lookback_days: 365 }, pool_size: 15 }],
        pick_count: 6,
      },
    ],
  },
  {
    name: 'Pool hỗn hợp',
    description: 'Steiner đề xuất 3 số, Frequency lọc trong pool đó. Random đề xuất 3 số, Steiner lọc trong pool đó.',
    groups: [
      {
        name: 'Steiner → Frequency',
        strategies: [
          { strategy: 'steiner', params: { lookback_days: 365 }, pool_size: 15 },
          { strategy: 'frequency', params: { lookback_days: 90, strategy_type: 'hot' }, pool_size: null },
        ],
        pick_count: 3,
      },
      {
        name: 'Random → Steiner',
        strategies: [
          { strategy: 'random', params: {}, pool_size: 15 },
          { strategy: 'steiner', params: { lookback_days: 365 }, pool_size: null },
        ],
        pick_count: 3,
      },
    ],
  },
  {
    name: 'Tần suất nóng + Markov',
    description: 'Số hay về gần đây kết hợp với chuỗi Markov.',
    groups: [
      {
        name: 'Tần suất nóng',
        strategies: [{ strategy: 'frequency', params: { lookback_days: 90, strategy_type: 'hot' }, pool_size: 15 }],
        pick_count: 4,
      },
      {
        name: 'Markov',
        strategies: [{ strategy: 'markov_chain', params: { lookback_days: 30 }, pool_size: 15 }],
        pick_count: 2,
      },
    ],
  },
  {
    name: 'Thiên hướng số vắng lâu',
    description: 'Ưu tiên các số đã lâu không xuất hiện.',
    groups: [
      {
        name: 'Pool số vắng lâu',
        strategies: [{ strategy: 'long_absence', params: { lookback_days: 180, top_n: 15 }, pool_size: 15 }],
        pick_count: 6,
      },
    ],
  },
];

function findStrategyOrFallback(
  key: string,
  strategies: StrategyMetadata[]
): StrategyMetadata | undefined {
  return strategies.find((s) => s.key === key) || strategies[0];
}

function sanitizeParams(
  strategy: StrategyMetadata | undefined,
  desired: Record<string, unknown>
): Record<string, unknown> {
  if (!strategy) return desired;
  const result: Record<string, unknown> = {};
  for (const p of strategy.params) {
    result[p.name] = desired[p.name] ?? p.default ?? null;
  }
  return result;
}

function sanitizeStep(step: StrategyStep, strategies: StrategyMetadata[]): StrategyStep {
  const strategy = findStrategyOrFallback(step.strategy, strategies);
  return {
    strategy: strategy?.key || step.strategy,
    params: sanitizeParams(strategy, step.params),
    pool_size: step.pool_size ?? null,
  };
}

export function applyPreset(index: number): void {
  const preset = PIPELINE_PRESETS[index];
  if (!preset) return;
  const strategies = state.strategies;
  const groups: GroupSpec[] = preset.groups.map((g) => ({
    ...g,
    strategies: g.strategies.map((s) => sanitizeStep(s, strategies)),
  }));
  setPipeline({ groups, combiner: { method: 'concatenate' } });
}

export function resetPipeline(): void {
  try {
    localStorage.removeItem(PIPELINE_KEY);
  } catch {
    // ignore
  }
  setState({
    pipeline: createDefaultPipeline(),
    generateResult: null,
    backtestResult: null,
  });
}
