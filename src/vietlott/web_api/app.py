"""FastAPI application for the Vietlott Strategy Builder Web API."""

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from vietlott.web_api.schemas import (
    BacktestRequest,
    BacktestResponse,
    EvRequest,
    EvResponse,
    GenerateRequest,
    GenerateResponse,
    PredictRequest,
    PredictResponse,
    StrategyBacktestRequest,
    StrategyBacktestResponse,
)
from vietlott.web_api.service import (
    compute_ev,
    generate_tickets,
    get_all_products,
    get_draws,
    get_product_info,
    get_strategies_metadata,
    predict_tickets,
    run_backtest,
    run_strategy_backtest,
)

app = FastAPI(title="Vietlott Strategy Builder API", version="0.1.0")

# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://localhost:3456",
        "http://127.0.0.1:3456",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    """Simple health-check endpoint."""
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[str]:
    """Return the list of registered product names."""
    return get_all_products()


@app.get("/api/products/{name}")
def product_info(name: str) -> dict:
    """Return product configuration for a given product name."""
    try:
        return get_product_info(name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown product: '{name}'")


@app.get("/api/strategies")
def strategies_list() -> list[dict]:
    """Return all registered strategy metadata."""
    return get_strategies_metadata()


@app.post("/api/generate")
def generate(body: GenerateRequest) -> dict:
    """Generate tickets for a pipeline specification.

    Returns a ``GenerateResponse``-shaped dict.
    """
    pipeline_dict = body.pipeline.model_dump()
    target_date: date | None = body.target_date

    try:
        result = generate_tickets(pipeline_dict, target_date=target_date)
        return GenerateResponse(**result).model_dump()
    except ValueError as exc:
        logger.warning("Generate failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Generate failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/backtest")
def backtest(body: BacktestRequest) -> dict:
    """Run a full backtest for a pipeline specification.

    Returns a ``BacktestResponse``-shaped dict.
    """
    pipeline_dict = body.pipeline.model_dump()
    date_from: date | None = body.date_from
    date_to: date | None = body.date_to

    # Validate date range.
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must not be after date_to",
        )

    try:
        result = run_backtest(
            pipeline_dict,
            date_from=date_from,
            date_to=date_to,
            ticket_count=body.ticket_count,
        )
        return BacktestResponse(**result).model_dump()
    except ValueError as exc:
        logger.warning("Backtest failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Backtest failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/predict")
def predict(body: PredictRequest) -> dict:
    """Generate next-draw prediction tickets for a product.

    Mirrors the Phase-1 migration contract: accepts the TS route handler's
    request shape (``{product, strategy?, config?, target_date?}``), uses
    data strictly before ``target_date`` (next draw when omitted) and
    returns a ``PredictionResult``-shaped payload (camelCase keys).
    """
    config_dict = body.config.model_dump() if body.config is not None else None
    if body.strategy:
        if config_dict is None:
            config_dict = {}
        config_dict["strategy"] = body.strategy

    try:
        result = predict_tickets(body.product, config=config_dict, target_date=body.target_date)
        return PredictResponse(**result).model_dump(mode="json", by_alias=True)
    except ValueError as exc:
        logger.warning("Predict failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Predict failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/ev")
def ev(body: EvRequest) -> dict:
    """Estimate per-ticket EV from crawl prize data (mirrors TS ``/api/ev``).

    Returns an ``EvResponse``-shaped payload (camelCase keys).
    """
    try:
        result = compute_ev(
            body.product,
            num_tickets=body.num_tickets,
            jackpot_base=body.jackpot_base,
            history_limit=body.history_limit,
            history_end_id=body.history_end_id,
            tier_mode=body.tier_mode,
        )
        return EvResponse(**result).model_dump(mode="json", by_alias=True)
    except ValueError as exc:
        logger.warning("EV estimation failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("EV estimation failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/draws")
def draws(product: str = "power_535", limit: int = 20, prizes: str = "0") -> dict:
    """Return draw history (newest-first), optionally with prize tiers.

    Mirrors the TS ``/api/draws`` handler shape:
    ``{product, display, total, draws: [{date, id, result, process_time?, prizes?}]}``.
    """
    include_prizes = prizes == "1"
    try:
        result = get_draws(product, limit=limit, include_prizes=include_prizes)
        from vietlott.web_api.schemas import DrawsResponse

        return DrawsResponse(**result).model_dump(mode="json", by_alias=True)
    except ValueError as exc:
        logger.warning("Draws fetch failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Draws fetch failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/backtest/strategy")
def backtest_strategy(body: StrategyBacktestRequest) -> dict:
    """Backtest the flat UI config (Inverse-Hybrid chain).

    Mirrors the TS ``/api/backtest`` handler output shape
    (``BacktestSummary`` — camelCase keys).
    """
    config_dict = body.config.model_dump() if body.config is not None else None
    try:
        result = run_strategy_backtest(body.product, config=config_dict)
        return StrategyBacktestResponse(**result).model_dump(mode="json", by_alias=True)
    except ValueError as exc:
        logger.warning("Flat backtest failed: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        logger.warning("Flat backtest failed (data missing): {}", exc)
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------
# Static file mount (SPA) — only if the build directory exists.
# ------------------------------------------------------------------

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"
if (WEB_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
    logger.info("Mounted static SPA from {}", WEB_DIST)
else:
    logger.info("No static SPA found at {}; API-only mode", WEB_DIST)
