# 单账户快速跟单架构说明

## 当前目标

本版本先实现单账户快速跟单，不做多账户广播。未来可以在同一套接口和队列表结构上扩展到多账户并发。

当前链路：

```text
WebSocket / HTTP signal
→ SignalBus 内存队列
→ Copy Execution Worker
→ 主执行账户解析
→ 账户级风控 / 限频 / 熔断
→ Adapter 下单或 dry-run
→ execution_events / orders / audit_logs
→ WebSocket 广播执行结果
```

## 已实现模块

### 1. WebSocket 信号通道

入口：

```text
/ws/signals?token=<TRADENODEX_AAT_OPERATOR_TOKEN>
```

消息格式：

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "order_type": "MARKET",
  "notional_usdt": 5,
  "multiplier": 1,
  "slippage_bps": 20
}
```

### 2. HTTP 信号入口

```bash
curl -X POST http://127.0.0.1:8000/v1/copy/signals \
  -H "Authorization: Bearer $TRADENODEX_AAT_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","order_type":"MARKET","notional_usdt":5,"multiplier":1,"slippage_bps":20}'
```

### 3. 订单广播队列

当前使用进程内 `asyncio.Queue`：

- 默认队列上限：`TRADENODEX_AAT_COPY_MAX_SIGNAL_QUEUE_SIZE=5000`
- 默认并发执行数：`TRADENODEX_AAT_COPY_MAX_CONCURRENT_EXECUTIONS=4`

生产多实例部署时建议替换为 Redis Streams / NATS / Kafka。

### 4. 单账户执行

主账户解析顺序：

1. 信号中指定 `target_account_id`
2. `.env` 中指定 `TRADENODEX_AAT_COPY_PRIMARY_ACCOUNT_ID`
3. 第一个 `BINANCE_FUTURES` account
4. 第一个 account

### 5. 账户级风控预算

接口：

```text
POST /v1/accounts/{account_id}/risk-budget
```

字段：

```json
{
  "max_order_notional_usdt": 50,
  "max_daily_notional_usdt": 500,
  "max_position_notional_usdt": 500,
  "min_free_balance_usdt": 10,
  "max_slippage_bps": 30,
  "rate_limit_per_minute": 30,
  "failures_before_circuit_break": 3,
  "circuit_break_seconds": 300
}
```

### 6. 账户级限频

采用内存 token bucket。当前适合单进程部署；多实例部署时应改为 Redis 原子限频。

### 7. 账户级失败熔断

同一账户在短时间内连续失败达到阈值后，会打开 circuit breaker，在配置时间内拒绝继续执行。

### 8. 延迟监控

每个执行事件会记录 `latency_ms` 到 `execution_events` 和 `account_runtime_metrics`。

### 9. 跟单倍率与风险映射

最终名义金额：

```text
signal.notional_usdt × signal.multiplier × TRADENODEX_AAT_COPY_DEFAULT_MULTIPLIER
```

然后再经过账户级：

- 单笔最大名义金额
- 当日最大名义金额
- 滑点 bps 限制
- rate limit
- failure circuit breaker

## 状态查询

```text
GET /v1/copy/signals
GET /v1/copy/executions
GET /v1/copy/metrics
```

## Mainnet 说明

本仓库保持安全优先原则：

- 单账户快速跟单架构已实现。
- dry-run 和 Binance Testnet 路径可验证。
- 多交易所 Mainnet adapter 必须逐交易所单独接入、单独测试、单独发布。
- 不建议在开源默认版本中提供一键真钱下单路径。

原因：不同交易所的合约符号、精度、保证金模式、杠杆、订单回报、限频、错误码和 API 权限差异很大，不能用统一模板直接保证真实资金安全。

## 云端部署建议

单机 Alpha：

```text
FastAPI + in-process SignalBus + SQLite WAL
```

生产 Beta：

```text
FastAPI + Redis Streams/NATS + PostgreSQL + separate execution worker + exchange user-data streams
```

