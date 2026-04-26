# TradeNodeX AI Automated Trading

**Version:** `v0.2.1-alpha.1`  
**Status:** release-candidate alpha for self-hosted dry-run and Binance Futures Testnet validation.  
**Mainnet:** blocked by default. Do not use with real funds until you complete your own testnet and minimum-size mainnet verification.

TradeNodeX AI Automated Trading is a self-hosted digital-asset robot trading control center. It is the automated-bot sibling of `TradeNodeX-AI-Copy-Trading`, using the same black/white terminal control-plane standard while replacing copy-routing workflows with robot strategy orchestration.

## What is included

Robot templates:

1. Funding-rate monitor / funding leg executor
2. Neutral contract grid
3. DCA / average-cost investing
4. Conservative spot-style grid
5. Bounded martingale

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
- Global live execution is blocked unless `TRADENODEX_AAT_ENABLE_LIVE_TRADING=true`.
- Mainnet execution is not enabled in this alpha release.
- Withdrawal functionality is not implemented.
- API keys are encrypted before being stored in SQLite.
- Every bot tick writes an audit log.
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

Protected write / execution endpoints:

- `POST /v1/accounts`
- `POST /v1/bots`
- `PATCH /v1/bots/{bot_id}`
- `POST /v1/bots/{bot_id}/start`
- `POST /v1/bots/{bot_id}/pause`
- `POST /v1/bots/{bot_id}/stop`
- `POST /v1/bots/{bot_id}/tick`
- `POST /v1/reconcile`
- `POST /v1/market-snapshot`

Example:

```bash
curl -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -X POST http://127.0.0.1:8000/v1/reconcile
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
- **Strategy Engine:** executable strategy decisions with normalized order schema.
- **Execution Engine:** pre-trade risk, idempotency key, client order id, remote order lookup before non-dry-run retry, bounded retry.
- **Risk Engine:** exchange compatibility, live gate, max position, global max notional, side/type validation.
- **Market Data:** Binance Testnet ticker/funding snapshot with credential-free dry-run fallback.
- **Reconciliation:** positions, open orders, and balances.
- **Persistence:** SQLite with WAL, busy timeout, foreign keys, schema metadata, audit logs.
- **Observability:** audit logs, request id headers, health endpoint, TradeNodeX response headers.
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

This is an alpha release candidate, not an institutionally certified production trading system. Before any mainnet work, add and validate:

- Binance mainnet adapter as a separate class
- mainnet-specific environment variables
- leverage and margin-mode verification on mainnet
- cancel / reduce-only / order update path
- balance and order reconciliation against exchange history
- kill switch and daily drawdown enforcement
- full WebSocket market-data and user-data streams
- PostgreSQL option for multi-process or higher-write deployments

## Copyright and legal notice

Copyright (c) 2026 TradeNodeX. Released under the MIT License.

Exchange names are used only to describe exchange connectivity targets. This project is not affiliated with, endorsed by, or sponsored by Binance, Bybit, OKX, Coinbase, Kraken, BitMEX, Gate.io, or any other exchange. This software is not financial advice, does not custody funds, and does not guarantee trading performance.
