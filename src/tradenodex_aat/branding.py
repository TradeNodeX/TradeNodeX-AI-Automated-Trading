from .version import __version__

PROJECT_NAME = 'TradeNodeX AI Automated Trading'
PROJECT_SHORT_NAME = 'TradeNodeX AAT'
OWNER = 'TradeNodeX'
COPYRIGHT = 'Copyright (c) 2026 TradeNodeX. Released under the MIT License.'
LICENSE = 'MIT'

DISCLAIMER = (
    'TradeNodeX AI Automated Trading is open-source software for self-hosted dry-run and testnet validation. '
    'It is not financial advice, does not custody funds, does not provide investment recommendations, and does not guarantee trading performance. '
    'Exchange names are used only to describe connectivity targets. This project is not affiliated with Binance, Bybit, OKX, Coinbase, Kraken, BitMEX, Gate.io, or any other exchange.'
)

RISK_NOTICE = (
    'Automated trading can lose money quickly. Keep live trading disabled until dry-run and testnet validation are complete. '
    'Never enable withdrawal permission on exchange API keys. Mainnet execution is not enabled in this alpha release.'
)


def legal_payload() -> dict:
    return {
        'project': PROJECT_NAME,
        'short_name': PROJECT_SHORT_NAME,
        'owner': OWNER,
        'version': __version__,
        'license': LICENSE,
        'copyright': COPYRIGHT,
        'disclaimer': DISCLAIMER,
        'risk_notice': RISK_NOTICE,
        'affiliation_notice': 'Independent open-source project. No exchange affiliation or endorsement is implied.',
        'release_status': 'alpha-testnet-preview',
    }
