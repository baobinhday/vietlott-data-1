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
