# Contributing to TradeNodeX AI Automated Trading

Thank you for your interest in contributing. This project welcomes contributions from developers, quant researchers, operators, and exchange-adapter testers.

## Contribution areas

High-value contributions include:

- exchange adapter validation
- sandbox/testnet validation reports
- symbol mapping fixes
- order status and error-code mapping
- reconciliation improvements
- WebSocket/private stream integrations
- deployment guides
- test coverage
- documentation improvements
- UI/UX refinements

## Ground rules

- Do not submit real API keys, secrets, passphrases, private keys, database dumps, or screenshots containing credentials.
- Do not claim exchange affiliation unless you can prove official authorization.
- Do not add profit guarantees, financial advice, or performance claims.
- Keep examples small, reproducible, and dry-run/testnet oriented whenever possible.
- Mainnet-related pull requests must include validation notes and risk controls.

## Development setup

```bash
cp .env.example .env
pip install -e .[dev]
python -m ruff check src tests scripts
python -m pytest -q
```

## Pull request checklist

Before opening a PR:

- [ ] The change is scoped and easy to review.
- [ ] Tests were added or updated.
- [ ] `python -m pytest -q` passes.
- [ ] `python -m ruff check src tests scripts` passes.
- [ ] No secrets or runtime database files are included.
- [ ] Documentation is updated where relevant.
- [ ] Mainnet changes are guarded by explicit opt-in checks.

## Exchange adapter validation

When contributing an exchange adapter or validation report, include:

- exchange name
- account mode: dry-run, sandbox/testnet, or mainnet read-only/min-size
- symbol tested
- market type
- precision findings
- min quantity / min notional findings
- order type tested
- reduce-only / close-position behavior if relevant
- reconciliation observations
- error codes encountered

## Security reports

Do not disclose exploitable vulnerabilities publicly. Follow `SECURITY.md`.
