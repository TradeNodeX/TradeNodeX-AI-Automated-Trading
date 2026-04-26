# TradeNodeX AI Automated Trading Architecture

## Product position

TradeNodeX AI Automated Trading is the robot-trading sibling of `TradeNodeX-AI-Copy-Trading`. It keeps the same self-hosted, single-operator, terminal-style control-plane direction while replacing copy-trading routes with bot orchestration.

## Runtime layers

1. **FastAPI control plane**
   - Serves `/` static preview UI.
   - Exposes `/v1/*` bot, account, dashboard and audit endpoints.
   - Keeps v1 state in process for first-version preview and local validation.

2. **Strategy engine**
   - `FUNDING_ARBITRAGE`
   - `NEUTRAL_CONTRACT_GRID`
   - `DCA`
   - `CONSERVATIVE_SPOT_GRID`
   - `MARTINGALE`

3. **Exchange compatibility registry**
   - Binance Futures
   - Bybit Linear
   - OKX Swap
   - Kraken Futures
   - BitMEX
   - Gate.io Futures
   - Coinbase Advanced

4. **24h worker**
   - Polls `/v1/dashboard`.
   - Executes `/v1/bots/{bot_id}/tick` for running bots.
   - Designed to run under Docker Compose, systemd, Supervisor, or any cloud process manager.

5. **Frontend preview**
   - Terminal-style black/white TradeNodeX interface.
   - Multi-language selector.
   - Multi-display-currency selector.
   - Bot fleet, API accounts, audit logs and bot creation views.

## Safety model

- Dry-run is the default execution mode.
- No withdrawal function exists.
- v1 strategy decisions generate order plans, not direct custody operations.
- Live trading must be enabled explicitly through environment and future adapter implementation.
- Every tick creates an audit trail.

## v1 limitations

- State is intentionally lightweight for the first public version.
- Exchange execution adapters are represented by compatibility registry and strategy decision plans.
- Production live trading should add encrypted credential storage, persistent DB, idempotent order executor, reconciliation, retry control, dead-letter queue and exchange-specific sandbox tests.

## Suggested v2 roadmap

- SQLite/PostgreSQL persistence.
- Encrypted API-key vault.
- CCXT adapter execution layer with dry-run/live bifurcation.
- WebSocket market-data ingestion.
- Strategy parameter editor.
- PnL and risk analytics.
- Telegram alerting.
- Backtest and paper-trading replay mode.
