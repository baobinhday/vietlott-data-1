# Helper — Strategy Builder Web App

Hướng dẫn chạy Strategy Builder (FastAPI backend + Vite/JS frontend + Docker).

## Yêu cầu

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Node.js 20+ và npm (chỉ cần khi dev frontend)
- Docker (tùy chọn, cho `docker compose up`)

## 1. Cài đặt lần đầu

```bash
# Clone + vào project
git clone https://github.com/vietvudanh/vietlott-data.git
cd vietlott-data

# Cài Python deps (gồm web + ml)
uv sync --extra web --extra ml

# Cài frontend deps (chỉ cần khi muốn dev với HMR)
cd web
npm install
cd ..
```

## 2. Chạy local — single command (recommended)

FastAPI vừa serve API vừa serve frontend static (từ `web/dist/`).

```bash
# Build frontend 1 lần
make web-build    # tương đương: cd web && npm install && npm run build

# Chạy API (frontend đã được mount tự động nếu web/dist tồn tại)
uv run uvicorn vietlott.web_api.app:app --reload --host 0.0.0.0 --port 8000
```

Mở http://localhost:8000 trong trình duyệt.

## 3. Chạy dev mode (frontend HMR + backend riêng)

Chạy 2 terminal song song:

```bash
# Terminal 1 — backend
uv run uvicorn vietlott.web_api.app:app --reload --port 8000
```

```bash
# Terminal 2 — frontend với hot reload
cd web
npm run dev
```

Mở http://localhost:5173. Vite sẽ proxy mọi request `/api/*` sang `http://localhost:8000`, không cần CORS.

## 4. Chạy bằng Docker

```bash
make docker-up       # build + run (foreground)
# hoặc
docker compose up --build -d   # chạy nền
```

App chạy ở http://localhost:8000. Thư mục `data/` được mount read-only vào container.

Dừng:

```bash
make docker-down
```

## 5. API endpoints

Base URL: `http://localhost:8000` (hoặc `http://localhost:5173` khi dev với Vite proxy).

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/products` | Danh sách product keys |
| GET | `/api/products/{name}` | Chi tiết 1 product (min, max, size_output, ticket_price, …) |
| GET | `/api/strategies` | Metadata của tất cả strategy (kèm param schema cho UI) |
| POST | `/api/generate` | Sinh vé cho kỳ tiếp theo từ JSON pipeline |
| POST | `/api/backtest` | Backtest pipeline trên khoảng ngày, trả về ROI + per-draw chart |

### Ví dụ: generate 3 vé Steiner+Frequency cho power_655

```bash
curl -sS -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline": {
      "product": "power_655",
      "groups": [
        {"name": "Steiner pool", "strategy": "steiner", "params": {"lookback_days": 365}, "pool_size": 15, "pick_count": 5},
        {"name": "Freq fillers", "strategy": "frequency", "params": {"lookback_days": 90, "strategy_type": "hot"}, "pool_size": 10, "pick_count": 1}
      ],
      "combiner": {"method": "concatenate"},
      "post_filters": {"min_sum": null, "max_sum": null, "min_even": null, "max_even": null, "min_odd": null, "max_odd": null},
      "ticket_count": 3
    }
  }' | python -m json.tool
```

Response mẫu:

```json
{
  "product": "power_655",
  "target_date": "2026-07-23",
  "tickets": [[5,10,11,13,14,28], [1,3,5,7,13,28], [2,4,7,8,9,41]],
  "total_cost_vnd": 30000,
  "pool_summary": [
    {"name": "Steiner pool", "strategy": "steiner", "picked_from_pool": 15},
    {"name": "Freq fillers", "strategy": "frequency", "picked_from_pool": 10}
  ]
}
```

### Ví dụ: backtest 30 ngày gần nhất

```bash
curl -sS -X POST http://localhost:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline": {
      "product": "power_655",
      "groups": [
        {"name": "G1", "strategy": "steiner", "params": {"lookback_days": 180}, "pool_size": 15, "pick_count": 6}
      ],
      "combiner": {"method": "concatenate"},
      "post_filters": {},
      "ticket_count": 1
    },
    "date_from": "2025-06-01",
    "date_to": "2025-07-01",
    "ticket_count": 1
  }' | python -m json.tool
```

## 6. Test + lint

```bash
make test                                  # full pytest
make lint                                  # ruff check --select I + format
make build                                 # lint + test (CI gate)

# Chạy test cụ thể
uv run pytest src/vietlott/tests/test_pipeline.py -v
uv run pytest src/vietlott/tests/test_web_api.py -v
```

## 7. Cấu trúc file đã thêm

```
src/machine_learning/strategies/
├── pipeline.py                            # PipelineStrategy (group-based ticket assembly)
└── registry.py                            # StrategyRegistry + metadata cho UI

src/vietlott/web_api/
├── __init__.py
├── data_loader.py                         # load_product_dataframe(name) -> pd.DataFrame
├── schemas.py                             # Pydantic v2 request/response models
├── service.py                             # business logic (no FastAPI)
└── app.py                                 # FastAPI app + routes + static mount

src/vietlott/tests/
├── test_pipeline.py                       # 24 tests
├── test_registry.py                       # 31 tests
├── test_web_api.py                        # 15 tests (TestClient)
└── test_web_service.py                    # 17 tests (service layer)

web/                                       # Vite + TypeScript SPA
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.ts                            # entry, 3-column layout
    ├── api.ts                             # fetch wrappers
    ├── state.ts                           # pub-sub state
    ├── chart.ts                           # SVG bar/line charts
    ├── ui.ts                              # tiny DOM helpers
    ├── types.ts                           # TS interfaces khớp API
    ├── styles.css                         # design system (dark mode default)
    └── ui/                                # group-editor, estimator, backtest, ...

Dockerfile                                 # multi-stage: node build → python runtime
docker-compose.yml                         # 1 service, mount ./data read-only
.dockerignore                              # loại trừ .git, .venv, node_modules, data/, …
```

## 8. Troubleshooting

**`uvicorn` không tìm thấy `vietlott.web_api.app`?**
→ Chạy `uv sync --extra web` trước, hoặc `make requirements-dev`.

**`ModuleNotFoundError: No module named 'pandas'`?**
→ Đã fix trong `pyproject.toml` (`web` extra bao gồm `pandas`). Nếu self-build từ trước, chạy `uv sync --extra web --reinstall`.

**Frontend mount không hoạt động (chỉ thấy JSON API)?**
→ Build frontend trước: `cd web && npm run build`. Nếu thiếu `web/dist/index.html`, FastAPI sẽ không mount static — chỉ phục vụ API.

**CORS error khi dev với Vite?**
→ Vite đã cấu hình proxy `/api` → `:8000` trong `vite.config.ts`. Đảm bảo backend đang chạy ở port 8000, hoặc sửa `proxy` trong `vite.config.ts`.

**Docker build chậm?**
→ Stage 1 (npm) chạy lại mỗi lần `web/package.json` đổi. Có thể tạo `web/package-lock.json` (`cd web && npm install`) để chuyển sang `npm ci` nhanh hơn.

## 9. Known limitations (v1)

- Bảng giải thưởng chưa custom theo từng product (đang dùng default của base class `PredictModel.prices`). TODO trong `src/vietlott/web_api/service.py`.
- 3 product được optimize UX là `power_655`, `power_645`, `power_535`; các product khác vẫn list trong dropdown nhưng prize table có thể không chính xác.
- Backtest 1 vé / kỳ; muốn nhiều vé / kỳ thì tăng `ticket_count` trong request.
