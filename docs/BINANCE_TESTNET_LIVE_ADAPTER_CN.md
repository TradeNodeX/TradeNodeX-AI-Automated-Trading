# Binance Futures Testnet 真实适配器验证手册

## 重要安全说明

不要把 API Key / Secret 写入 GitHub、README、Issue、PR、截图或聊天记录。即使是测试网密钥，也应视为敏感信息。

如果密钥已经公开过，建议立即在 Binance Futures Testnet 后台删除并重新生成。

## 1. 当前支持范围

本项目 `v0.2.1-alpha.1` 已接入 Binance USDT-M Futures Testnet 的 CCXT adapter，支持：

- Testnet market snapshot
- Testnet funding rate snapshot
- Testnet create order path
- Testnet position reconciliation path
- Testnet open-order reconciliation path
- Testnet balance reconciliation path
- client order id / idempotency key
- retry and audit log
- 订单数量 / 价格精度处理
- 最小数量 / 最小名义金额校验
- Testnet 杠杆和保证金模式配置入口

其他交易所仍保留 adapter 扩展位，但 live order path 默认阻断。

## 2. 本地 .env 配置

复制环境文件：

```bash
cp .env.example .env
```

在本地 `.env` 填写，不要提交：

```bash
TRADENODEX_AAT_OPERATOR_TOKEN=replace-with-strong-token
TRADENODEX_AAT_ENCRYPTION_KEY=replace-with-strong-random-key
TRADENODEX_AAT_ENABLE_LIVE_TRADING=false
TRADENODEX_AAT_BINANCE_FUTURES_TESTNET_API_KEY=your-testnet-api-key
TRADENODEX_AAT_BINANCE_FUTURES_TESTNET_API_SECRET=your-testnet-api-secret
TRADENODEX_AAT_BINANCE_TESTNET_DEFAULT_LEVERAGE=1
TRADENODEX_AAT_BINANCE_TESTNET_MARGIN_MODE=ISOLATED
```

首次验证必须保持：

```bash
TRADENODEX_AAT_ENABLE_LIVE_TRADING=false
```

## 3. 启动服务

```bash
pip install -e .[dev]
uvicorn tradenodex_aat.main:app --reload
```

另开终端：

```bash
python -m tradenodex_aat.worker
```

## 4. Dry-run 验证

```bash
python scripts/binance_testnet_validation.py --symbol BTCUSDT
```

脚本会从 `TRADENODEX_AAT_OPERATOR_TOKEN` 读取 operator token，并在调用写接口时发送 `Authorization: Bearer ...`。

成功标准：

- `/v1/health` 返回 ok。
- `/v1/market-snapshot` 能返回行情或 dry-run fallback。
- 能创建 testnet account 记录。
- 能创建 dry-run bot。
- tick 使用 market snapshot 生成订单计划。
- orders / audit_logs 有记录。
- reconciliation 不崩溃。

## 5. 真实 Testnet 最小订单验证

确认 Binance Futures Testnet 账户有测试资金后，修改本地 `.env`：

```bash
TRADENODEX_AAT_ENABLE_LIVE_TRADING=true
```

然后只运行最小测试：

```bash
python scripts/binance_testnet_validation.py \
  --symbol BTCUSDT \
  --max-position-usdt 20 \
  --risk-per-tick-usdt 5 \
  --place-test-order
```

成功标准：

- 交易所后台能看到测试订单。
- 本地 `/v1/orders` 有记录。
- `client_order_id` 不重复。
- 失败时不会盲目重复下单，执行器会先尝试 remote client id 查询。
- `/v1/reconcile` 能同步持仓、未完成订单和余额。

## 6. 小额 Mainnet 前置条件

不要直接把 testnet adapter 改成 mainnet。进入 mainnet 前必须先补：

- Binance mainnet adapter 单独类。
- 单独 mainnet 环境变量。
- 订单最小数量自动校验。
- 价格精度 / 数量精度自动校验。
- 杠杆和保证金模式显式设置。
- reduce-only 和 cancel 路径验证。
- 每账户硬风控预算。
- 每日亏损熔断。
- user data stream 订单回报。
- 交易所历史成交和手续费 reconciliation。

## 7. 当前版本结论

`v0.2.1-alpha.1` 可以作为 Binance Futures Testnet release-candidate alpha 验证版本。它不应直接用于 mainnet。mainnet 必须在 testnet 全流程通过后再单独接入，并从最小订单开始。
