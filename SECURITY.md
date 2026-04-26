# Security Policy

## Supported version

The current public version is `0.1.x`.

## Secret handling

Do not commit exchange API keys, API secrets, passphrases, JWT tokens, database passwords, SSH private keys or cloud credentials.

Recommended exchange API permissions:

- trading permission only when live trading is intentionally enabled
- no withdrawal permission
- IP allowlist where supported
- separate API keys per exchange account and environment

## Live trading gate

The project is dry-run first. Live execution must remain blocked unless the operator intentionally enables a future live adapter and sets explicit environment controls.

## Reporting vulnerabilities

Open a GitHub issue without including exploitable secrets or private credentials. For sensitive reports, contact the repository owner privately through GitHub profile channels.

## Operational safety

- Start with testnet where supported.
- Use minimum order sizes for first mainnet verification.
- Run one bot and one symbol before scaling.
- Keep audit logs.
- Set hard max position, hard max loss and cooldown rules.
