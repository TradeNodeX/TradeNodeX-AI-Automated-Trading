# Deployment Guide

This guide describes a basic self-hosted deployment for TradeNodeX AI Automated Trading.

## 1. Server requirements

Recommended minimum for alpha testing:

- Ubuntu 22.04 or newer
- 2 vCPU
- 2 GB RAM
- 20 GB disk
- Docker and Docker Compose
- Firewall allowing only required ports

## 2. Clone repository

```bash
git clone https://github.com/TradeNodeX/TradeNodeX-AI-Automated-Trading.git
cd TradeNodeX-AI-Automated-Trading
```

## 3. Configure environment

```bash
cp .env.example .env
nano .env
```

At minimum, change:

```bash
TRADENODEX_AAT_OPERATOR_TOKEN=replace-with-a-strong-token
TRADENODEX_AAT_ENCRYPTION_KEY=replace-with-a-strong-random-key
```

Never commit `.env`.

## 4. Docker deployment

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
curl http://127.0.0.1:8000/v1/health
```

## 5. Open frontend

```text
http://your-server-ip:8000/
```

Enter your operator token in the frontend before using write actions.

## 6. Run smoke test

```bash
python scripts/smoke_test_api.py \
  --api-base http://127.0.0.1:8000 \
  --operator-token "$TRADENODEX_AAT_OPERATOR_TOKEN"
```

## 7. Recommended production hardening

- Place the API behind Nginx or Caddy with TLS.
- Restrict access by firewall or VPN.
- Use a strong operator token.
- Use IP allowlists for exchange API keys where supported.
- Do not enable withdrawal permissions on exchange API keys.
- Back up the `data/` directory.
- Monitor logs and disk usage.
- Keep Docker images and dependencies updated.

## 8. Suggested Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 9. Upgrade process

```bash
git pull
docker compose down
docker compose up -d --build
```

Back up data before upgrades:

```bash
cp -r data data.backup.$(date +%Y%m%d%H%M%S)
```
