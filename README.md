# TradeNodeX AI Automated Trading

<p align="center">
  <strong>Open-source crypto bot control plane for WebSocket signals, account-level risk controls, Binance Futures Testnet validation, and controlled opt-in exchange adapters.</strong>
</p>

<p align="center">
  <a href="./LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-white.svg"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-blue.svg">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115+-green.svg">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-blue.svg">
  <img alt="Status" src="https://img.shields.io/badge/Status-Alpha-orange.svg">
  <img alt="Exchange Routes" src="https://img.shields.io/badge/Exchange%20Routes-Controlled%20Opt--in-red.svg">
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#single-account-fast-copy">Fast Copy</a> ·
  <a href="#exchange-support-matrix">Exchange Matrix</a> ·
  <a href="./docs/CONTROLLED_OPT_IN_MAINNET_CN.md">Mainnet Route</a> ·
  <a href="./docs/SINGLE_ACCOUNT_FAST_COPY_CN.md">中文文档</a>
</p>

---

## Overview

**TradeNodeX AI Automated Trading** is a self-hosted digital-asset bot control plane designed for developers, quant traders, and operators who want a transparent open-source foundation for:

- WebSocket / HTTP signal ingestion
- single-account fast-copy execution architecture
- account-level risk budgets, rate limits, and failure circuit breakers
- strategy bot templates for DCA, grids, martingale, and funding-rate workflows
- Binance Futures Testnet validation
- controlled opt-in adapter routes for major exchanges
- Docker-based cloud deployment

It follows the black/white terminal control-plane design language of `TradeNodeX-AI-Copy-Trading`, but focuses on automated bot orchestration and signal-to-execution infrastructure.

> Current version: `v0.2.1-alpha.1`. This is an alpha release candidate for infrastructure validation and developer testing.

---

## Why this project

Most open-source trading bots mix strategy logic, exchange execution, secrets, and risk controls into a single fragile script. TradeNodeX AAT separates the system into a clearer control-plane architecture:

```text
Signal Ingress → Queue → Risk Gate → Execution Worker → Adapter → Reconciliation → Audit Trail
```

Core design goals:

- **Operator-controlled execution** — write/execution APIs are protected by an operator token.
- **Signal-native workflow** — WebSocket and HTTP signal inputs are first-class citizens.
- **Account-level controls** — risk budget, rate limit, circuit breaker, and latency metrics are account-scoped.
- **Exchange adapter discipline** — exchange routes are explicit, configurable, and auditable.
- **Self-hosted deployment** — API keys and databases remain under the operator’s control.
- **Open-source extensibility** — MIT licensed, FastAPI-based, Docker-ready, and modular.

---

## Feature highlights

### Bot templates

- Funding-rate monitor / funding leg executor
- Neutral contract grid
- DCA / average-cost investing
- Conservative spot-style grid
- Bounded martingale

### Single-account fast-copy

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
- Copy metrics endpoint: `GET /v1/copy/metrics`

### Execution and risk

- Operator-token protected write APIs
- API key encryption before persistence
- Idempotency key generation
- Client order ID mapping
- Bounded retry flow
- Remote order lookup for non-dry-run paths
- Account-level notional budget
- Slippage bps budget
- Failure circuit breaker
- Audit/event trail

### Deployment and operations

- FastAPI backend
- Terminal-style frontend
- SQLite WAL persistence
- Dockerfile and Docker Compose
- Health endpoint
- Smoke test scripts
- CI with pytest, ruff, bandit, pip-audit, Docker build

---

## Architecture

![TradeNodeX Signal Flow](./docs/assets/tradenodex-signal-flow.svg)

```text
TradingView / External Signal / Manual Signal
        │
        ▼
WebSocket / HTTP Signal Ingress
        │
        ▼
SignalBus Queue
        │
        ▼
Copy Execution Worker
        │
        ▼
Account Risk Budget / Rate Limit / Circuit Breaker
        │
        ▼
Exchange Adapter
        │
        ▼
Orders / Positions / Balances / Audit Logs
```

---

## Exchange support matrix

| Exchange | Dry-run | Testnet / Sandbox | Controlled Opt-in Mainnet Route | Default Mainnet |
|---|---:|---:|---:|---:|
| Binance Futures | Yes | Implemented | Route available | Off |
| Bybit Linear | Yes | Validation required | Route available | Off |
| OKX Swap | Yes | Validation required | Route available | Off |
| Kraken Futures | Yes | Validation required | Route available | Off |
| BitMEX | Yes | Validation required | Route available | Off |
| Gate.io Futures | Yes | Validation required | Route available | Off |
| Coinbase Advanced | Yes | Validation required | Route available | Off |

Controlled opt-in routes require explicit exchange-level flags, account configuration, credentials, operator authentication, account risk budgets, and validation. See [`docs/CONTROLLED_OPT_IN_MAINNET_CN.md`](./docs/CONTROLLED_OPT_IN_MAINNET_CN.md).

---

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

Run the worker in another process:

```bash
python -m tradenodex_aat.worker
```

### Docker

```bash
cp .env.example .env
# Edit .env first.
docker compose up -d --build
```

---

## Single-account fast copy

HTTP signal example:

```bash
curl -X POST http://127.0.0.1:8000/v1/copy/signals \
  -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","order_type":"MARKET","notional_usdt":5,"multiplier":1,"slippage_bps":20}'
```

WebSocket signal endpoint:

```text
ws://127.0.0.1:8000/ws/signals?token=<TRADENODEX_AAT_OPERATOR_TOKEN>
```

WebSocket message:

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

---

## API surface

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

---

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

Minimum-size testnet order path:

```bash
TRADENODEX_AAT_ENABLE_LIVE_TRADING=true python scripts/binance_testnet_validation.py \
  --symbol BTCUSDT \
  --max-position-usdt 20 \
  --risk-per-tick-usdt 5 \
  --place-test-order
```

---

## Documentation

- [Single-account fast-copy architecture CN](./docs/SINGLE_ACCOUNT_FAST_COPY_CN.md)
- [Controlled opt-in mainnet adapter route CN](./docs/CONTROLLED_OPT_IN_MAINNET_CN.md)
- [Binance Futures Testnet live adapter CN](./docs/BINANCE_TESTNET_LIVE_ADAPTER_CN.md)
- [Cloud deployment guide](./docs/DEPLOYMENT.md)
- [FAQ](./docs/FAQ.md)
- [Roadmap](./ROADMAP.md)
- [Changelog](./CHANGELOG.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)

---

## Roadmap snapshot

| Version | Focus |
|---|---|
| `v0.2.x` | Bot control plane, Binance Futures Testnet, protected APIs |
| `v0.3.x` | Single-account fast-copy, signal queue, account risk budgets |
| `v0.4.x` | Exchange validation templates, stronger reconciliation, private streams |
| `v0.5.x` | Redis/NATS queue option, PostgreSQL option, deployment hardening |
| `v1.0` | Production-grade self-hosted release candidate after exchange-specific validation |

---

## Community and validation

Exchange adapters require real-world validation. Contributions are especially welcome for:

- exchange-specific symbol mapping
- sandbox/testnet validation reports
- market metadata edge cases
- order status/error-code mapping
- user-data/private WebSocket streams
- reconciliation test cases
- deployment guides

Use the issue templates to submit bug reports, feature requests, and exchange validation results.

---

## Risk and legal notice

This software is not financial advice, does not custody funds, and does not guarantee trading performance. Automated trading can cause losses. Exchange names are used only to describe connectivity targets. This project is not affiliated with, endorsed by, or sponsored by Binance, Bybit, OKX, Coinbase, Kraken, BitMEX, Gate.io, or any other exchange.

Copyright (c) 2026 TradeNodeX. Released under the MIT License.
