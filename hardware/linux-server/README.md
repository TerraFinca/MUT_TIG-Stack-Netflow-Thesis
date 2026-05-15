# Linux Server — TIG Stack Host

Single host ทำหน้าที่ทั้ง NetFlow collector + InfluxDB + Grafana

## Specifications

| Spec | Value |
|------|-------|
| OS | RHEL 9.6 |
| RAM | 12 GB |
| CPU | (specs not captured) |
| Interface | enp2s0 — xxx.xxx.xxx.xx/30 (point-to-point กับ ASR) |
| Overlay | ZeroTier — xxx.xxx.xxx.xx (สำหรับ remote admin) |

## Software Installed

| Package | Version |
|---------|---------|
| Docker Engine | 29.4.1 |
| Docker Compose | v5.1.3 |
| Python | 3.x (system) |
| systemd | (system) |

## Production Directory

`/root/TIG_PRODUCTION/`
- `docker-compose.yml` — TIG Stack orchestration
- `telegraf.conf` — Telegraf config (mounted into container)
- `app_classify.star` — Auto-generated ASN classifier (mounted into Telegraf)
- `grafana_templates/` — Patched email template (mounted into Grafana)
- `grafana_data/` — Grafana volume (dashboards, users)
- `influxdb_data/` — InfluxDB volume (data + WAL)

## systemd Units

| Unit | Location | Schedule |
|------|----------|----------|
| `topn-rollup.timer` | `/etc/systemd/system/` | `*:0/5` (every 5 min) |
| `auto-classify.timer` | `/etc/systemd/system/` | daily 03:00 |

## Deployment from scratch

1. Install Docker Engine + Compose
2. Install ZeroTier (optional, for remote admin)
3. Clone this repo to `/root/TIG_PRODUCTION/`
4. Copy `.env.example` → `.env`, fill in secrets
5. `docker compose up -d`
6. Setup systemd timers (see `software/topn-rollup/` and `software/asn-classifier/`)
