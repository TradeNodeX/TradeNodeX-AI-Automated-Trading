# TradeNodeX AI Automated Trading 中文运行手册

## 1. 本项目是什么

这是一个自托管的数字货币机器人交易控制中心第一版，目标是对齐 `TradeNodeX-AI-Copy-Trading` 的前端控制台风格与交易所兼容方向，但业务对象从跟单路由切换为机器人策略编排。

支持的机器人模板：

1. 资金费率套利
2. 中性合约网格
3. DCA 定投
4. 保守型现货网格
5. 有边界的稳健型马丁格尔

## 2. 本地启动

```bash
cp .env.example .env
pip install -e .[dev]
uvicorn tradenodex_aat.main:app --reload
```

访问：

```text
http://127.0.0.1:8000/
```

## 3. 24 小时 worker

另开一个终端：

```bash
python -m tradenodex_aat.worker
```

worker 会读取 dashboard 中处于 `RUNNING` 状态的机器人，并周期性调用 tick。

## 4. Docker 云服务器部署

```bash
cp .env.example .env
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f tradenodex-aat-api
docker compose logs -f tradenodex-aat-worker
```

停止：

```bash
docker compose down
```

## 5. 安全建议

- 默认只使用 dry-run。
- 不要开启提现权限。
- 交易所 API 建议绑定固定服务器 IP。
- 实盘前必须完成小额 testnet/mainnet 验证。
- 马丁格尔必须设置最大步数、最大亏损和冷却时间。
- 资金费率套利必须扣除手续费、滑点、借贷成本和资金划转成本后再决策。

## 6. 第一版边界

第一版重点是完整项目骨架、UI 预览、API、worker、策略决策计划、测试和部署结构。它不是保证盈利的交易系统，也不是托管资金服务。
