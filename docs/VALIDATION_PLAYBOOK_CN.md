# 真实 Testnet / 小额 Mainnet 验证流程

## 0. 基本原则

本项目默认是 dry-run first。任何实盘能力上线前，都必须完成以下验证流程。

禁止事项：

- 禁止给 API Key 开启提现权限。
- 禁止在未完成 testnet 验证前开启 mainnet。
- 禁止多个机器人、多币种、多交易所同时首次实盘。
- 禁止马丁格尔在未设置最大步数、最大亏损、冷却时间前运行。

## 1. 环境变量准备

`.env` 必须至少配置：

```bash
TRADENODEX_AAT_DB_PATH=./data/tradenodex_aat.sqlite3
TRADENODEX_AAT_OPERATOR_TOKEN=replace-with-strong-token
TRADENODEX_AAT_ENCRYPTION_KEY=replace-with-strong-random-key
TRADENODEX_AAT_ENABLE_LIVE_TRADING=false
TRADENODEX_AAT_DEFAULT_DRY_RUN=true
TRADENODEX_AAT_MAX_RETRY_ATTEMPTS=3
```

生产环境必须替换 `OPERATOR_TOKEN` 和 `ENCRYPTION_KEY`。

## 2. API Key 创建

交易所 API Key 权限要求：

1. 只开启交易权限。
2. 关闭提现权限。
3. 能绑定固定服务器 IP 的交易所必须绑定 IP。
4. testnet 与 mainnet 使用不同 API Key。
5. 每个子账户单独 API Key，不混用。

## 3. Dry-run 验证

启动服务：

```bash
uvicorn tradenodex_aat.main:app --reload
```

启动 worker：

```bash
python -m tradenodex_aat.worker
```

验证项目：

- `/v1/dashboard` 能返回 bots、accounts、orders、positions。
- 创建 5 类机器人后，状态可切换 RUNNING / PAUSED / STOPPED。
- 每次 tick 都写入 audit log。
- orders 表中不存在重复 idempotency key。
- worker 连续运行 24 个 tick 不崩溃。

## 4. Testnet 验证

顺序：

1. 只选择一个交易所。
2. 只选择一个机器人。
3. 只选择一个交易对，例如 BTCUSDT。
4. 使用最小订单金额。
5. 开启 testnet adapter。
6. 提交最小订单。
7. 验证订单出现在交易所后台。
8. 调用 `/v1/reconcile`。
9. 验证本地 positions 与交易所一致。
10. 测试 cancel、reduce-only、异常重试。

成功标准：

- 下单、撤单、reconciliation、日志全部闭环。
- 失败重试不会重复下单。
- 任何异常都会写入 audit log。
- 告警渠道能收到失败和执行通知。

## 5. 小额 Mainnet 验证

前置条件：

- Testnet 已通过。
- 已人工检查所有风控参数。
- 已确认交易所最小下单单位与手续费。
- 已确认资金费率、滑点、价差和杠杆设置。

步骤：

1. 保持 `TRADENODEX_AAT_ENABLE_LIVE_TRADING=false`，先跑 dry-run。
2. 只开一个机器人、一个交易对、一个账户。
3. 把最大仓位设置到极小金额。
4. 开启告警。
5. 手动确认风控无误后，才允许短时间开启 live gate。
6. 第一笔 mainnet 订单必须是交易所允许的最小订单。
7. 订单完成后立即暂停机器人。
8. 运行 `/v1/reconcile`。
9. 对比交易所后台、本地 orders、本地 positions、audit logs。

成功标准：

- 无重复订单。
- 无孤儿订单。
- 无未识别持仓。
- PnL 与交易所后台可解释。
- 告警、日志和 reconciliation 完整。

## 6. 放大规模前的硬性条件

扩大到多机器人、多币种、多交易所之前，必须补齐：

- 交易所真实 WebSocket 行情适配。
- 交易所原生订单回报流。
- 数据库迁移工具。
- API 鉴权中间件。
- 每账户风控预算。
- 每策略熔断器。
- 每交易所速率限制器。
- 死信队列或失败任务表。
- 全量回放测试。

## 7. 结论

v2 是可运行、可验证、可扩展的自动交易控制中心架构，但不应绕过 testnet 与小额 mainnet 验证流程直接实盘运行。
