# 受控 Opt-in Mainnet Adapter 路线

## 当前结论

本项目已经加入 7 个交易所的受控 opt-in mainnet adapter 路线：

- Binance Futures
- Bybit Linear
- OKX Swap
- Kraken Futures
- BitMEX
- Gate.io Futures
- Coinbase Advanced

默认状态仍然不会真钱下单。用户必须逐层显式开启，才可能进入 mainnet adapter。

## 受控开关条件

进入 mainnet live adapter 必须同时满足：

```text
TRADENODEX_AAT_ENABLE_LIVE_TRADING=true
TRADENODEX_AAT_ENABLE_<EXCHANGE>_MAINNET=true
account.environment=MAINNET
account.dry_run=false
account has encrypted API key or env API key
account risk budget exists
operator token passed
```

任意条件不满足，系统会返回 blocked adapter，不会触发真实交易所下单。

## 交易所开关

```bash
TRADENODEX_AAT_ENABLE_BINANCE_FUTURES_MAINNET=false
TRADENODEX_AAT_ENABLE_BYBIT_LINEAR_MAINNET=false
TRADENODEX_AAT_ENABLE_OKX_SWAP_MAINNET=false
TRADENODEX_AAT_ENABLE_KRAKEN_FUTURES_MAINNET=false
TRADENODEX_AAT_ENABLE_BITMEX_MAINNET=false
TRADENODEX_AAT_ENABLE_GATEIO_FUTURES_MAINNET=false
TRADENODEX_AAT_ENABLE_COINBASE_ADVANCED_MAINNET=false
```

## 主网 API Key 占位

```bash
TRADENODEX_AAT_BINANCE_FUTURES_MAINNET_API_KEY=
TRADENODEX_AAT_BINANCE_FUTURES_MAINNET_API_SECRET=
TRADENODEX_AAT_BYBIT_LINEAR_MAINNET_API_KEY=
TRADENODEX_AAT_BYBIT_LINEAR_MAINNET_API_SECRET=
TRADENODEX_AAT_OKX_SWAP_MAINNET_API_KEY=
TRADENODEX_AAT_OKX_SWAP_MAINNET_API_SECRET=
TRADENODEX_AAT_OKX_SWAP_MAINNET_API_PASSPHRASE=
TRADENODEX_AAT_KRAKEN_FUTURES_MAINNET_API_KEY=
TRADENODEX_AAT_KRAKEN_FUTURES_MAINNET_API_SECRET=
TRADENODEX_AAT_BITMEX_MAINNET_API_KEY=
TRADENODEX_AAT_BITMEX_MAINNET_API_SECRET=
TRADENODEX_AAT_GATEIO_FUTURES_MAINNET_API_KEY=
TRADENODEX_AAT_GATEIO_FUTURES_MAINNET_API_SECRET=
TRADENODEX_AAT_COINBASE_ADVANCED_MAINNET_API_KEY=
TRADENODEX_AAT_COINBASE_ADVANCED_MAINNET_API_SECRET=
TRADENODEX_AAT_COINBASE_ADVANCED_MAINNET_API_PASSPHRASE=
```

不要把真实 API Key 写入 GitHub、Issue、PR、README、截图、聊天窗口或日志。

## 已实现的 adapter 能力

`ControlledMainnetCcxtAdapter` 覆盖：

- CCXT exchange id 注册
- 符号格式 normalization
- 合约/市场类型 defaultType
- market metadata 加载
- 数量精度 amount_to_precision
- 价格精度 price_to_precision
- 最小数量检查
- 最小名义金额检查
- client order id 映射
- reduce-only 参数
- post-only 参数
- 远端 client order 查询
- open orders 查询
- positions 查询
- balance 查询
- ticker / funding snapshot 查询

## 仍需逐交易所验证的部分

虽然代码层已经有统一 adapter 路线，但真实主网每个交易所必须单独验证：

- 真实符号格式
- USDT 永续 / USD 合约 / 现货差异
- 杠杆设置是否生效
- 保证金模式是否生效
- 单向 / 双向持仓模式
- reduce-only 行为
- close-position 行为
- 错误码映射
- API 权限范围
- 历史订单 / 历史成交 reconciliation
- user-data stream 订单回报
- 限频与退避策略

## 推荐验证顺序

1. Dry-run。
2. Testnet / sandbox，如果交易所支持。
3. Mainnet 只读：balance、positions、open orders。
4. Mainnet 最小限额 limit order，远离盘口。
5. 立即 cancel。
6. reduce-only / close-position 单独验证。
7. user-data stream 回报验证。
8. 最小 market order。
9. 低频、单账户、单 symbol 运行。

## 为什么不是默认开放？

开源用户下载代码后可能直接填入主网 API。默认真钱下单会造成不可接受的资金风险。受控 opt-in 的目标是：

```text
代码具备真实 adapter 接入路径
默认仍然安全
用户必须显式解锁
每个交易所必须单独验证
所有实盘行为留痕并经过账户级风控
```

## 当前发布口径

可以写：

```text
7 个交易所已加入受控 opt-in mainnet adapter 路线，默认关闭，需要逐交易所显式开关和账户级风控。
```

不要写：

```text
默认支持 7 个交易所主网真钱下单。
```
