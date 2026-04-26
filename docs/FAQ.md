# FAQ

## What is TradeNodeX AI Automated Trading?

TradeNodeX AI Automated Trading is a self-hosted open-source crypto bot control plane for signal ingestion, bot orchestration, account-level risk controls, exchange adapter research, and deployment validation.

## Is it a copy-trading platform?

It includes a single-account fast-copy architecture with WebSocket and HTTP signal ingestion. It is not a full multi-account production copy-trading network yet.

## Which exchange has a implemented testnet path?

Binance Futures Testnet is the current implemented testnet execution path.

## What does controlled opt-in mainnet route mean?

It means exchange adapter routes exist behind explicit configuration gates. A route requires operator authentication, account configuration, credentials, account risk budget, and exchange-specific validation before real execution should be attempted.

## Does it guarantee profit?

No. It is infrastructure software, not financial advice, and it does not guarantee trading performance.

## Does it custody funds?

No. It is self-hosted. Users control their own exchange accounts and API keys.

## Should exchange API keys include withdrawal permission?

No. Use trading-only permissions where possible, separate testnet/mainnet keys, and IP allowlists when the exchange supports them.

## Can I deploy it on a cloud VPS?

Yes. See `docs/DEPLOYMENT.md` for a cloud deployment outline.

## Why SQLite?

SQLite WAL is simple for alpha single-node deployments. For higher write volume, multi-worker operation, or production-like deployment, PostgreSQL is recommended in the roadmap.

## Why is Redis or NATS recommended later?

The current signal queue is in-process. Redis Streams, NATS, or Kafka are better for durable queues, multi-process workers, and crash recovery.

## How do I contribute exchange validation?

Use the exchange validation issue template and include symbol, market type, precision, minimum order size, order status, error codes, and reconciliation observations.
