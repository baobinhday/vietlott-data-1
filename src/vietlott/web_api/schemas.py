"""Pydantic v2 models for the Vietlott Strategy Builder Web API."""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyParamSpec(BaseModel):
    """Metadata for a single strategy parameter."""

    name: str
    type: str
    default: Any
    min: float | None = None
    max: float | None = None
    description: str = ""


class StrategyMetadata(BaseModel):
    """Metadata for a registered strategy."""

    key: str
    label: str
    description: str
    params: list[StrategyParamSpec]


class StrategyStep(BaseModel):
    """A single step in a strategy chain.

    ``pool_size`` controls the output pool size at *this* step:
    - When set (int ≥ 1): the step's output is capped or topped-up to
      exactly that many numbers.
    - When ``None`` / absent: the step runs in "auto" mode, using the
      strategy's natural output size.
    """

    model_config = ConfigDict(extra="forbid")

    strategy: str
    params: dict[str, Any] = Field(default_factory=dict)
    pool_size: int | None = None


class GroupSpec(BaseModel):
    """A single group in a pipeline spec.

    Supports both the **new** format (``strategies`` list) and the **old**
    backward-compatible format (``strategy`` + ``params`` + ``pool_size``).

    Use ``.normalized()`` to obtain a dict in the new format regardless of
    which format was provided.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = "Group"

    # NEW preferred format:
    strategies: list[StrategyStep] | None = None
    pick_count: int = 1

    # BACKWARD-COMPAT fields (old format):
    strategy: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    pool_size: int = 10

    def normalized(self) -> dict:
        """Return the new-format dict. Accepts both old and new formats."""
        if self.strategies:
            steps = [s.model_dump(exclude_none=True) for s in self.strategies]
        elif self.strategy:
            step: dict[str, Any] = {
                "strategy": self.strategy,
                "params": self.params,
                "pool_size": self.pool_size,
            }
            steps = [step]
        else:
            raise ValueError(f"Group '{self.name}' must have either 'strategies' or 'strategy'")
        return {"name": self.name, "strategies": steps, "pick_count": self.pick_count}


class CombinerSpec(BaseModel):
    """How groups are combined."""

    model_config = ConfigDict(extra="forbid")

    method: str = "concatenate"


class PostFilterSpec(BaseModel):
    """Optional constraints on the final ticket."""

    model_config = ConfigDict(extra="forbid")

    min_sum: int | None = None
    max_sum: int | None = None
    min_even: int | None = None
    max_even: int | None = None
    min_odd: int | None = None
    max_odd: int | None = None


class PipelineSpec(BaseModel):
    """Complete pipeline specification for ticket generation / backtest."""

    model_config = ConfigDict(extra="forbid")

    product: str
    groups: list[GroupSpec] = Field(..., min_length=1)
    combiner: CombinerSpec = Field(default_factory=CombinerSpec)
    post_filters: PostFilterSpec = Field(default_factory=PostFilterSpec)
    ticket_count: int = 1


class GenerateRequest(BaseModel):
    """Request body for ``POST /api/generate``."""

    model_config = ConfigDict(extra="forbid")

    pipeline: PipelineSpec
    target_date: date | None = None


class GenerateResponse(BaseModel):
    """Response body for ``POST /api/generate``."""

    product: str
    target_date: date
    tickets: list[list[int]]
    total_cost_vnd: int
    pool_summary: list[dict]


class BacktestRequest(BaseModel):
    """Request body for ``POST /api/backtest``.

    When ``ticket_count`` is ``None`` (default), the pipeline's own
    ``ticket_count`` is used.  When set explicitly, it overrides the
    pipeline value.
    """

    model_config = ConfigDict(extra="forbid")

    pipeline: PipelineSpec
    date_from: date | None = None
    date_to: date | None = None
    ticket_count: int | None = None  # None → use pipeline.ticket_count


# ---------------------------------------------------------------------------
# GET /api/draws + POST /api/backtest/strategy (Phase 2)
# NOTE: request/response field names use camelCase aliases to match the
# TypeScript ``BacktestConfig`` / ``PredictionResult`` contract in
# ``web/src/lib/types.ts``.  snake_case is accepted on input.
# ---------------------------------------------------------------------------


def _to_camel(snake: str) -> str:
    """Convert a snake_case identifier to camelCase (``date_from`` → ``dateFrom``)."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    """Base model accepting AND emitting camelCase field names.

    snake_case population is enabled (``populate_by_name``) so both
    ``lookbackDays`` and ``lookback_days`` are accepted; responses are
    always serialized with ``model_dump(by_alias=True)``.
    """

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class ColdStrategyConfig(CamelModel):
    """ColdNumbersStrategy tuning (mirrors ``BacktestConfig.cold``)."""

    lookback_days: int = 365
    selection_weight: float = 0.7


class SteinerStrategyConfig(CamelModel):
    """SteinerStrategy tuning (mirrors ``BacktestConfig.steiner``)."""

    lookback_days: int = 365
    filter_consecutive: bool = True
    filter_same_decade: bool = True
    t: int = 2
    k: int = 3
    v: int | None = None


class InverseStrategyConfig(CamelModel):
    """InverseHybridStrategy tuning (mirrors ``BacktestConfig.inverse``)."""

    top_k: int = 15


class SpecialsStrategyConfig(CamelModel):
    """Frequency specials picker tuning (mirrors ``BacktestConfig.specials``)."""

    top_n: int = 4
    mode: str = "markov_steiner"
    lookback_draws: int = 60
    offset_draws: int = 30


class DdFilterConfig(CamelModel):
    """Độc Đắc filter tuning (mirrors ``BacktestConfig.ddFilter``)."""

    enabled: bool = True
    threshold: int = 15_000_000_000


class PredictConfig(CamelModel):
    """Full flat prediction config (mirrors the TS ``BacktestConfig``)."""

    strategy: str | None = None
    tpd: int = 2
    cold: ColdStrategyConfig = Field(default_factory=ColdStrategyConfig)
    steiner: SteinerStrategyConfig = Field(default_factory=SteinerStrategyConfig)
    inverse: InverseStrategyConfig = Field(default_factory=InverseStrategyConfig)
    specials: SpecialsStrategyConfig = Field(default_factory=SpecialsStrategyConfig)
    dd_filter: DdFilterConfig = Field(default_factory=DdFilterConfig)
    date_from: str | None = None
    date_to: str | None = None


class PredictTicket(CamelModel):
    """A single predicted ticket (mirrors the TS ``PredictionTicket``)."""

    predicted: list[int]
    predicted_special: int | None = None
    coverage: int


class DrawInfo(CamelModel):
    """Minimal draw info (mirrors the TS ``Draw`` fields the UI consumes)."""

    date: str
    id: str
    result: list[int]


class PredictRequest(CamelModel):
    """Request body for ``POST /api/predict``.

    Mirrors the current TS route handler: ``{product, strategy?, config?}``
    plus ``target_date``.  When ``target_date`` is omitted the next draw
    date is computed via :func:`compute_next_draw_date`.
    """

    product: str = "power_535"
    strategy: str | None = None
    config: PredictConfig | None = None
    target_date: date | None = None


class PredictResponse(CamelModel):
    """Response body for ``POST /api/predict`` (mirrors TS ``PredictionResult``)."""

    product: str
    product_display: str
    strategy: str
    config: PredictConfig
    previous_draw: DrawInfo | None = None
    tickets: list[PredictTicket]
    generated_at: str


class DrawPrizeTierModel(BaseModel):
    """A single prize tier as consumed by the FE ``PrizeTable`` (snake keys)."""

    prize_name: str
    prize_value: int
    winners_count: int


class DrawRecord(CamelModel):
    """A single draw (mirrors the TS ``Draw``)."""

    date: str
    id: str
    # Power-family draws: plain int list; 3D-style products keep their
    # raw {prize_name: [codes]} mapping (the Power UI never renders them).
    result: list[int] | dict[str, list[str]]
    # TS contract keeps the raw snake_case ``process_time`` field.
    process_time: str | None = Field(default=None, alias="process_time")
    prizes: list[DrawPrizeTierModel] | None = None


class DrawsResponse(CamelModel):
    """Response body for ``GET /api/draws`` (mirrors the TS route handler)."""

    product: str
    display: str
    total: int
    draws: list[DrawRecord]


class DrawsRequestParams(CamelModel):
    """Query params for ``GET /api/draws`` (validated in the endpoint)."""

    product: str = "power_535"
    limit: int = 20
    prizes: bool = False


class BacktestTicketRowModel(CamelModel):
    """Per-ticket backtest row (mirrors the TS ``BacktestTicketRow``)."""

    date: str
    draw_id: str
    predicted: list[int]
    predicted_special: int | None = None
    result: list[int]
    main_match: int
    special_match: int
    gain: int
    is_correct: bool
    predict_idx: int
    special_idx: int


class YearlyRowModel(CamelModel):
    """Yearly aggregate row (mirrors the TS ``YearlyRow``)."""

    year: int
    draws: int
    predictions: int
    cost: int
    gain: int
    profit: int
    roi: float


class StrategyBacktestResponse(CamelModel):
    """Response body for ``POST /api/backtest/strategy``.

    Mirrors the TS ``BacktestSummary`` field-for-field (camelCase).
    """

    total_cost: int
    total_gain: int
    net_profit: int
    roi: float
    total_draws: int
    total_predictions: int
    match_distribution: dict[int, int]
    special_hits: int
    best_threshold: int
    eligible_draws: int
    best_results: list[BacktestTicketRowModel]
    yearly_breakdown: list[YearlyRowModel]
    all_rows: list[BacktestTicketRowModel]


class StrategyBacktestRequest(CamelModel):
    """Request body for ``POST /api/backtest/strategy`` (TS ``BacktestConfig`` flat)."""

    product: str = "power_535"
    config: PredictConfig | None = None


class EvRequest(CamelModel):
    """Request body for ``POST /api/ev`` (mirrors the TS route handler body)."""

    product: str = "power_535"
    num_tickets: int = 8
    jackpot_base: int = 6_000_000_000
    history_limit: int = 10
    history_end_id: str | None = None
    tier_mode: str = "fixed"


class TierWinnerExpectationsModel(CamelModel):
    """Mean winners per tier across the recent draws."""

    jackpot: float
    nhat: float
    nhi: float
    ba: float
    tu: float
    nam: float
    khuyen_khich: float = Field(default=0, alias="khuyen_khich")


class DrawRevenueEstimateModel(CamelModel):
    """Back-calculated revenue estimate for one observed draw."""

    jackpot_value: int
    jackpot_winners: int
    has_jackpot_winner: bool
    carryover: int
    fresh_contribution: int
    revenue: int
    tickets: int


class NextDrawProjectionModel(CamelModel):
    """Projection of the next draw's Jackpot & ticket volume (mirrors TS)."""

    expected_next_jackpot: int
    expected_revenue: int
    expected_tickets: int
    avg_tickets_last_n: int
    sample_size: int
    confidence: str
    avg_jackpot_winners_last_n: float
    expected_winners: TierWinnerExpectationsModel
    split_mode: bool


class TierEvRowModel(CamelModel):
    """Per-tier EV row (mirrors the TS ``TierEvRow``)."""

    tier: str
    display_name: str
    probability: float
    expected_payout: int
    ev: float
    split_adjusted: bool
    expected_other_winners: float


class EvResponse(CamelModel):
    """Response body for ``POST /api/ev`` (mirrors the TS route handler output)."""

    product: str
    display: str
    ticket_price: int
    jackpot_base: int
    history_sample_size: int
    history_end_id: str | None = None
    tier_mode: str
    ev_per_ticket: float
    total_ev: float
    num_tickets: int
    breakdown: list[TierEvRowModel]
    projection: NextDrawProjectionModel


class BacktestResponse(BaseModel):
    """Response body for ``POST /api/backtest``."""

    product: str
    date_from: date
    date_to: date
    draws: int
    tickets_per_draw: int
    total_tickets: int
    total_cost_vnd: int
    total_revenue_vnd: int
    net_profit_vnd: int
    roi: float
    matches_distribution: dict[int, int]
    best_match: int
    avg_match: float
    per_draw: list[dict]
