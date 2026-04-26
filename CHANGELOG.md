# Changelog

All notable changes to TradeNodeX AI Automated Trading will be documented in this file.

## [0.2.1-alpha.1] - 2026-04

### Added

- FastAPI control plane
- Terminal-style frontend
- Operator-token protected write APIs
- Encrypted API key storage
- SQLite WAL persistence
- Dockerfile and Docker Compose deployment
- Binance Futures Testnet adapter path
- Strategy templates: DCA, neutral grid, spot-style grid, bounded martingale, funding workflow
- Single-account fast-copy architecture
- WebSocket signal channel
- HTTP signal ingress
- In-process signal queue
- Background copy execution worker
- Account-level risk budget
- Account-level token-bucket rate limit
- Account-level failure circuit breaker
- Signal multiplier and notional mapping
- Execution latency tracking
- Controlled opt-in exchange adapter routes
- TradeNodeX legal endpoint and response headers
- Smoke test scripts
- CI workflow with pytest, ruff, bandit, pip-audit, and Docker build

### Changed

- Reworked README into a public open-source project overview.
- Added exchange support matrix and documentation index.
- Added controlled opt-in mainnet documentation.

### Security

- Added operator token requirement for write/execution APIs.
- Added `.gitignore` and `.dockerignore` for runtime secrets and databases.
- Added SECURITY.md with secret-handling guidance.

### Notes

This release is an alpha release candidate for infrastructure validation and developer testing. It is not financial advice and does not guarantee trading performance.
