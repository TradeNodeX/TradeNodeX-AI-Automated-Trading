# TradeNodeX AI Automated Trading

TradeNodeX AI Automated Trading is a self-hosted digital-asset robot trading control center. It is designed as the automated-bot sibling of `TradeNodeX-AI-Copy-Trading`, keeping the same black/white terminal control-plane style while replacing copy-routing workflows with robot strategy orchestration.

## First-version scope

Supported robot templates:

1. Funding-rate arbitrage
2. Neutral contract grid
3. DCA / average-cost investing
4. Conservative spot grid
5. Bounded martingale

Exchange compatibility targets:

- Binance Futures
- Bybit Linear
- OKX Swap
- Kraken Futures
- BitMEX
- Gate.io Futures
- Coinbase Advanced

## Safety posture

- Dry-run is enabled by default.
- Global live execution is blocked unless `TRADENODEX_AAT_ENABLE_LIVE_TRADING=true`.
- Withdrawal functionality is not implemented.
- Operator writes are protected by `TRADENODEX_AAT_OPERATOR_TOKEN`.
- Every bot tick writes an audit log.

## Quick start

```bash
cp .env.example .env
pip install -e .[dev]
uvicorn tradenodex_aat.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Run the 24h worker in another process:

```bash
python -m tradenodex_aat.worker
```

## Docker cloud deployment

```bash
cp .env.example .env
docker compose up -d --build
```

API:

- `GET /v1/health`
- `GET /v1/dashboard`
- `GET /v1/accounts`
- `POST /v1/accounts`
- `GET /v1/bots`
- `POST /v1/bots`
- `PATCH /v1/bots/{bot_id}`
- `POST /v1/bots/{bot_id}/start`
- `POST /v1/bots/{bot_id}/pause`
- `POST /v1/bots/{bot_id}/stop`
- `POST /v1/bots/{bot_id}/tick`
- `GET /v1/logs`

## Frontend

The FastAPI app ships a static terminal-style control-plane preview at `/`, aligned with the existing TradeNodeX black/white frontend standard.

## Legal notice

Exchange names are used only to describe compatibility targets. This project is not affiliated with those exchanges. This software is not financial advice, does not custody funds, and does not guarantee trading performance.
