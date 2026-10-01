# Proposal: Web frontend → dùng chung backend Python (FastAPI)

- **Ngày:** 2026-10-01
- **Trạng thái:** Draft
- **Bối cảnh:** `web/` (Next.js) hiện có **2 lớp logic dự đoán song song** chạy cùng lúc trong repo: Python (`src/machine_learning` + `src/vietlott/web_api`) và TypeScript (`web/src/lib/{backtest,predict,config,data,ev}`). Hai lớp này tính cùng một loại kết quả nhưng cấu hình ≠ nhau, mặc định ≠ nhau, và chỉ giữ đồng bộ bằng tay → drift nhất định xảy ra.

## Vấn đề

1. `web/src/lib/*` là **bản tái hiện logic ML bằng TS** (backtest, steiner, inverse-hybrid, markov…). Sửa python phải sửa lại TS (và ngược lại); gần nhất cả hai đã lệch nhau (TS gen-local không biết InverseHybridTrioStrategy mới của Python phải thêm tay).
2. Test chỉ phủ Python; TS không có test → backtest/predict на FE có thể sai lặng lẽ.
3. Chỉ dùng `power_645` → output của backend ;
4. Lịch trình/Cron/vercel có ‑thêm logic riêng không song song chính với python.

## Đích

Frontend **tự đặt các tính toán bằng Python**, TS chỉ còn:
- `web/src/lib/types.ts` — typed contract (TS types mô tả JSON contract).
- `web/src/lib/api.ts` — client duy nhất gọi backend (`API_URL` bên ngoài).
- **Xóa toàn bộ** tạo logic trong `config.ts, backtest.ts, predict.ts, ev.ts, data.ts, prizes.ts, strategies/`.

## Thiết kế

- Backend giữ nguyên các endpoint hiện có:
  - `GET /api/products`, `GET /api/products/{name}` — product metadata (giữ như hiện tại).
  - `GET /api/strategies` — strategy metadata (tính nội dung từ Python).
  - `POST /api/generate`, `POST /api/backtest` — pipeline-based (đã có).
- **Thêm 2 endpoint mới để UI không phải tự ghép dữ liệu** (thay `@/lib/predict.ts` + `@/lib/ev.ts`):
  1. `POST /api/predict` — input `{product, strategy, params, tpd, target_date?, dd*, specials}`; output được tính bằng Python, trả đúng shape UI cần (`productDisplay, strategy, targetDate, tickets, 每个 ticket có thể render, target date được tính qua `compute_next_draw_date` nếu không truyền).
  2. `POST /api/ev` — input `{product}`; output `ev_per_ticket` + breakdown, dùng `prizes.py` (discount-free).
- **CORS thêm origin của Next (http://localhost:3456)** hiện đã có 5173 — thêm 3456, hoặc chạy prod dùng `rewrites`/route-handler proxy để không cần CORS.
- UI form chỉ còn đổi `strategy/params/tpd/dates`; config object được gửi thẳng lên backend (validate phía Python).

## sai khác cần fix khi migrate (medium risk)

- **Strategy names** khác: TS dùng nhãn hiển thị ("Inverse Hybrid: Cold Numbers → Steiner") khớp với key.
- `BacktestConfig` có `tpd` và các sub-config (cold/steiner/inverse/specials/ddFilter) — cần map sang `GroupSpec/StrategyStep` của `PipelineSpec`, hoặc mở rộng backend để nhận flat-config cho các UI.
- Backtest đủ detail từng ticket (per_draw) — được cover SUCCESS.

## Phases

1. **Backend:** thêm `/api/predict` + `/api/ev` (service.py trỏ sang ML render logic hoặc strategies trực tiếp), thêm origin 3456 vào CORS.
2. **TS:** personnages mới `lib/api.ts` + `lib/types.ts`; đổi 5 route handler truyền match các endpoint của Python.
3. **TS:** `Sidebar/BacktestView/PredictionView` giữ nguyên (chỉ types), xóa autoregressive code trong lib cũ.
4. **Xóa:** `web/src/lib/{backtest,predict,config,data,ev,prizes}.ts` + `strategies/` (khoảng 2000+ dòng đầu).
5. **Test:** pytest web_api đã có; sang thêm test cặp adapter; `make dev-web` + `make run-dev` mọi tab phải render đúng Power 6/45.

## Ước lượng

| Phase | Công |
|---|---|
| 1. cadastr novo endpoints | 0.5–1 ngày |
| 2. adapter + API client | 0.5 ngày |
| 3–4. chuyển đổ UI + xóa lib cũ | 0.5 ngày |
| 5. test + tĩnh lại | 0.5 ngày |

## rủi ro và không làm

- Không deploy InverseHybridTry ở TS (Python đã có) — bỏ double-maintenance.
- Không tự thêm trường `dd*` nếu UI không cần — đã có trên backend.
- Không chỉnh UI/UX trong PR này (tách PR).
