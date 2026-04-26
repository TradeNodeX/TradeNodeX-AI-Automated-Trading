# Security Policy

## Supported version

The current release-candidate alpha is `v0.2.1-alpha.1`.

## Security posture

TradeNodeX AI Automated Trading is dry-run first. Binance Futures Testnet is the only live adapter path included in this alpha release. Mainnet execution remains blocked until a separate mainnet adapter, dedicated environment variables, and minimum-size verification process are implemented.

## Operator authentication

Write and execution endpoints require an operator token via one of the following headers:

```text
Authorization: Bearer <TRADENODEX_AAT_OPERATOR_TOKEN>
X-Operator-Token: <TRADENODEX_AAT_OPERATOR_TOKEN>
```

Do not deploy with the example token.

## Secret handling

Do not commit exchange API keys, API secrets, passphrases, JWT tokens, database passwords, SSH private keys, cloud credentials, `.env` files, or SQLite runtime databases.

Recommended exchange API permissions:

- trading permission only when live testnet trading is intentionally enabled
- no withdrawal permission
- IP allowlist where supported
- separate API keys per exchange account and environment
- separate testnet and mainnet keys

## Credential storage

Exchange credentials submitted through the API are encrypted before being stored in SQLite. Operators may alternatively provide testnet credentials through local environment variables.

## Live trading gate

`TRADENODEX_AAT_ENABLE_LIVE_TRADING=false` is the default. Keep it disabled until dry-run and testnet validation are complete. Mainnet is not enabled in this alpha release.

## Reporting vulnerabilities

Open a GitHub issue without including exploitable secrets or private credentials. For sensitive reports, contact the repository owner privately through GitHub profile channels.

## Operational safety

- Start with dry-run.
- Continue with Binance Futures Testnet only.
- Use minimum order sizes for first testnet verification.
- Run one bot and one symbol before scaling.
- Keep audit logs.
- Set hard max position, hard max loss, and cooldown rules.
- Rotate any API key that was pasted into chats, screenshots, issues, logs, or documents.
