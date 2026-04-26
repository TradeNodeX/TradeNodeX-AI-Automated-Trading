# Roadmap

TradeNodeX AI Automated Trading is developed as an open-source trading infrastructure project. The roadmap below describes intended engineering milestones and does not imply investment performance or exchange endorsement.

## v0.2.x — Control Plane Foundation

- FastAPI backend
- Terminal-style frontend
- Operator-token protected write APIs
- Encrypted API key storage
- SQLite WAL persistence
- Audit logs
- Binance Futures Testnet validation path
- Docker and Docker Compose deployment

## v0.3.x — Single-Account Fast Copy

- WebSocket signal ingress
- HTTP signal ingress
- In-process signal queue
- Copy execution worker
- Account-level risk budget
- Account-level token-bucket rate limit
- Account-level failure circuit breaker
- Signal multiplier and notional mapping
- Execution latency metrics

## v0.4.x — Exchange Validation Framework

- Exchange validation issue template
- Adapter validation checklist
- Exchange-specific symbol mapping reports
- Historical order/fill reconciliation templates
- Error-code mapping tables
- Sandbox/testnet validation playbooks where available

## v0.5.x — Operational Hardening

- Redis Streams or NATS queue option
- PostgreSQL persistence option
- Dedicated execution worker process
- Queue durability
- Structured metrics export
- Deployment guide for cloud VPS
- Backup and recovery guide

## v0.6.x — Private Streams and Reconciliation

- Exchange user-data/private stream framework
- Order status event stream
- Fill event stream
- Balance update stream
- Reconciliation mismatch detector
- Account-level kill switch

## v1.0 Candidate

A production-grade self-hosted release candidate requires:

- exchange-specific adapter validation
- documented mainnet validation reports
- private-stream confirmation paths
- cancel / replace / reduce-only / close-position verification
- durable queue option
- PostgreSQL option
- high-quality operational documentation
- security review

## Out of Scope

- profit guarantees
- custodial fund management
- financial advice
- exchange affiliation claims
- default one-click real-money execution
