export interface StrategyParam {
  name: string;
  type: string;
  default: unknown;
  min?: number;
  max?: number;
  options?: string[];
  description: string;
}

export interface StrategyMetadata {
  key: string;
  label: string;
  description: string;
  params: StrategyParam[];
}

export interface ProductInfo {
  name: string;
  min: number;
  max: number;
  size_output: number;
  has_special: boolean;
  special_min?: number;
  special_max?: number;
  special_count?: number;
  ticket_price: number;
  display_name?: string;
}

export interface StrategyStep {
  strategy: string;
  params: Record<string, unknown>;
  pool_size: number | null;
}

export interface GroupSpec {
  name: string;
  strategies: StrategyStep[];
  pick_count: number;
}

export interface CombinerSpec {
  method: string;
}

export interface PostFilterSpec {
  min_sum: number | null;
  max_sum: number | null;
  min_even: number | null;
  max_even: number | null;
  min_odd: number | null;
  max_odd: number | null;
}

export interface PipelineSpec {
  product: string;
  groups: GroupSpec[];
  combiner: CombinerSpec;
  post_filters: PostFilterSpec;
  ticket_count: number;
}

export interface GenerateRequest {
  pipeline: PipelineSpec;
  target_date?: string;
}

export interface PerDraw {
  date: string;
  ticket: number[];
  tickets: number[][];
  actual: number[];
  matches: number;
  prize_vnd: number;
  cumulative_profit_vnd: number;
}

export interface GenerateResult {
  product: string;
  target_date: string;
  tickets: number[][];
  total_cost_vnd: number;
  pool_summary: Record<string, unknown>[];
}

export interface BacktestRequest {
  pipeline: PipelineSpec;
  date_from: string;
  date_to: string;
  ticket_count: number;
}

export interface BacktestResult {
  product: string;
  date_from: string;
  date_to: string;
  draws: number;
  tickets_per_draw: number;
  total_cost_vnd: number;
  total_revenue_vnd: number;
  net_profit_vnd: number;
  roi: number;
  matches_distribution: Record<string, number>;
  best_match: number;
  avg_match: number;
  per_draw: PerDraw[];
}

export interface ApiHealth {
  status: string;
}
