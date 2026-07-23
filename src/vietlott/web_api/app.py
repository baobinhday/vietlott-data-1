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
    GenerateRequest,
    GenerateResponse,
)
from vietlott.web_api.service import (
    generate_tickets,
    get_all_products,
    get_product_info,
    get_strategies_metadata,
    run_backtest,
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


# ------------------------------------------------------------------
# Static file mount (SPA) — only if the build directory exists.
# ------------------------------------------------------------------

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"
if (WEB_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
    logger.info("Mounted static SPA from {}", WEB_DIST)
else:
    logger.info("No static SPA found at {}; API-only mode", WEB_DIST)
