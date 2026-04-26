# TradeNodeX AI Automated Trading

**Version:** `v0.2.1-alpha.1`  
**Status:** release-candidate alpha for self-hosted dry-run, Binance Futures Testnet validation, and single-account fast-copy architecture preview.  
**Mainnet:** blocked by default. Do not use with real funds until you complete your own testnet and minimum-size mainnet verification.

TradeNodeX AI Automated Trading is a self-hosted digital-asset robot trading control center. It is the automated-bot sibling of `TradeNodeX-AI-Copy-Trading`, using the same black/white terminal control-plane standard while adding robot orchestration and a single-account fast-copy signal path.

## What is included

Robot templates:

1. Funding-rate monitor / funding leg executor
2. Neutral contract grid
3. DCA / average-cost investing
4. Conservative spot-style grid
5. Bounded martingale

Single-account fast-copy path:

- WebSocket signal channel: `ws://host/ws/signals?token=<operator-token>`
- HTTP signal ingress: `POST /v1/copy/signals`
- In-process signal queue
- Background copy execution worker
- Primary account resolver
- Account-level risk budget
- Account-level token-bucket rate limit
- Account-level failure circuit breaker
- Signal multiplier and notional mapping
- Execution event latency tracking
- Copy metrics: `GET /v1/copy/metrics`

Exchange compatibility targets:

- Binance Futures — **Testnet live adapter implemented**
- Bybit Linear — adapter placeholder, live path blocked
- OKX Swap — adapter placeholder, live path blocked
- Kraken Futures — adapter placeholder, live path blocked
- BitMEX — adapter placeholder, live path blocked
- Gate.io Futures — adapter placeholder, live path blocked
- Coinbase Advanced — adapter placeholder, live path blocked

## Safety posture

- Dry-run is enabled by default.
- Write APIs require `Authorization: Bearer <TRADENODEX_AAT_OPERATOR_TOKEN>` or `X-Operator-Token`.
- WebSocket signal ingestion requires `?token=<TRADENODEX_AAT_OPERATOR_TOKEN>`.
- Global live execution is blocked unless `TRADENODEX_AAT_ENABLE_LIVE_TRADING=true`.
- Mainnet execution is not enabled in this alpha release.
- Withdrawal functionality is not implemented.
- API keys are encrypted before being stored in SQLite.
- Every bot tick and copy signal writes an audit/event trail.
- The worker sends the operator token when calling protected endpoints.
- Binance Testnet adapter performs symbol precision and minimum order checks through CCXT market metadata.
- Every HTTP response includes TradeNodeX project/risk headers.

## Quick start

```bash
cp .env.example .env
# Edit .env and replace TRADENODEX_AAT_OPERATOR_TOKEN and TRADENODEX_AAT_ENCRYPTION_KEY
pip install -e .[dev]
uvicorn tradenodex_aat.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The frontend contains an Operator Token field. Enter your local `TRADENODEX_AAT_OPERATOR_TOKEN` before using write actions.

Run the worker in another process:

```bash
python -m tradenodex_aat.worker
```

## Docker deployment

```bash
cp .env.example .env
# Edit .env first; never use the example token in deployment.
docker compose up -d --build
```

The Docker image runs as a non-root user and exposes `/v1/health` for health checks.

## Protected API contract

Public read endpoints:

- `GET /`
- `GET /v1/health`
- `GET /v1/legal`
- `GET /v1/dashboard`
- `GET /v1/accounts`
- `GET /v1/bots`
- `GET /v1/orders`
- `GET /v1/positions`
- `GET /v1/logs`
- `GET /v1/validation-plan`
- `GET /v1/copy/signals`
- `GET /v1/copy/executions`
- `GET /v1/copy/metrics`

Protected write / execution endpoints:

- `POST /v1/accounts`
- `POST /v1/accounts/{account_id}/risk-budget`
- `POST /v1/bots`
- `PATCH /v1/bots/{bot_id}`
- `POST /v1/bots/{bot_id}/start`
- `POST /v1/bots/{bot_id}/pause`
- `POST /v1/bots/{bot_id}/stop`
- `POST /v1/bots/{bot_id}/tick`
- `POST /v1/copy/signals`
- `POST /v1/reconcile`
- `POST /v1/market-snapshot`

Example:

```bash
curl -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -X POST http://127.0.0.1:8000/v1/reconcile
```

## Single-account fast-copy usage

HTTP signal:

```bash
curl -X POST http://127.0.0.1:8000/v1/copy/signals \
  -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","order_type":"MARKET","notional_usdt":5,"multiplier":1,"slippage_bps":20}'
```

WebSocket signal:

```text
ws://127.0.0.1:8000/ws/signals?token=<TRADENODEX_AAT_OPERATOR_TOKEN>
```

Message:

```json
{"symbol":"BTCUSDT","side":"BUY","order_type":"MARKET","notional_usdt":5,"multiplier":1,"slippage_bps":20}
```

Account risk budget:

```bash
curl -X POST http://127.0.0.1:8000/v1/accounts/<account_id>/risk-budget \
  -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_order_notional_usdt":50,"max_daily_notional_usdt":500,"max_position_notional_usdt":500,"min_free_balance_usdt":10,"max_slippage_bps":30,"rate_limit_per_minute":30,"failures_before_circuit_break":3,"circuit_break_seconds":300}'
```

## Legal and branding endpoints

- `GET /v1/legal` returns the TradeNodeX copyright, MIT license, risk notice, affiliation notice, and disclaimer payload.
- Response headers include `X-TradeNodeX-Project`, `X-TradeNodeX-Owner`, `X-TradeNodeX-Copyright`, and `X-TradeNodeX-Risk-Notice`.

## Binance Futures Testnet validation

Configure local `.env` only. Never commit real values.

```bash
TRADENODEX_AAT_OPERATOR_TOKEN=replace-with-strong-token
TRADENODEX_AAT_ENCRYPTION_KEY=replace-with-strong-random-key
TRADENODEX_AAT_ENABLE_LIVE_TRADING=false
TRADENODEX_AAT_BINANCE_FUTURES_TESTNET_API_KEY=your-testnet-key
TRADENODEX_AAT_BINANCE_FUTURES_TESTNET_API_SECRET=your-testnet-secret
```

Dry-run closure:

```bash
python scripts/binance_testnet_validation.py --symbol BTCUSDT
```

Generic API smoke test:

```bash
python scripts/smoke_test_api.py --symbol BTCUSDT
```

Minimum-size testnet order path, only after confirming testnet credentials and testnet balance:

```bash
TRADENODEX_AAT_ENABLE_LIVE_TRADING=true python scripts/binance_testnet_validation.py \
  --symbol BTCUSDT \
  --max-position-usdt 20 \
  --risk-per-tick-usdt 5 \
  --place-test-order
```

## Architecture

- **Core Control Plane:** FastAPI, terminal frontend, operator-token protected writes, TradeNodeX branding/risk headers.
- **Single-Account Fast Copy:** WebSocket/HTTP signal ingress, in-process queue, execution worker, latency metrics, failure circuit breaker.
- **Strategy Engine:** executable strategy decisions with normalized order schema.
- **Execution Engine:** pre-trade risk, idempotency key, client order id, remote order lookup before non-dry-run retry, bounded retry.
- **Risk Engine:** exchange compatibility, live gate, max position, global max notional, account-level budgets, slippage bps, rate limit, circuit breaker.
- **Market Data:** Binance Testnet ticker/funding snapshot with credential-free dry-run fallback.
- **Reconciliation:** positions, open orders, and balances.
- **Persistence:** SQLite with WAL, busy timeout, foreign keys, schema metadata, audit logs, signal events, execution events, account budgets.
- **Observability:** audit logs, request id headers, health endpoint, TradeNodeX response headers, copy metrics.
- **CI/CD:** pytest, ruff, bandit, pip-audit, Docker build.

## Test

```bash
pip install -e .[dev]
python -m ruff check src tests scripts
python -m pytest -q
```

Server-level smoke test after starting API:

```bash
python scripts/smoke_test_api.py --api-base http://127.0.0.1:8000 --operator-token "$TRADENODEX_AAT_OPERATOR_TOKEN"
```

## Release limitations

This is an alpha release candidate, not an institutionally certified production trading system. Current scope is dry-run, Binance Testnet validation, and single-account fast-copy architecture preview.

Before any mainnet work, add and validate:

- Each exchange mainnet adapter as a separate reviewed implementation
- Mainnet-specific environment variables and credential scopes
- Leverage and margin-mode verification on each exchange
- Cancel / replace / reduce-only / close-position paths
- Balance and order reconciliation against exchange history
- Kill switch and daily drawdown enforcement
- Full WebSocket market-data and user-data streams
- Redis Streams/NATS for queue durability
- PostgreSQL option for multi-process or higher-write deployments

## Copyright and legal notice

Copyright (c) 2026 TradeNodeX. Released under the MIT License.

Exchange names are used only to describe exchange connectivity targets. This project is not affiliated with, endorsed by, or sponsored by Binance, Bybit, OKX, Coinbase, Kraken, BitMEX, Gate.io, or any other exchange. This software is not financial advice, does not custody funds, and does not guarantee trading performance.
