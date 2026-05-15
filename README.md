# MIIX NetFlow Monitoring

ระบบเฝ้าระวังและวิเคราะห์จราจรเครือข่ายสำหรับอาคาร MIIX มหาวิทยาลัยเทคโนโลยีมหานคร (MUT) โดยใช้ FlexNetFlow บน Cisco ASR1001-X ส่งข้อมูลแบบ NetFlow v9 ไปยัง TIG Stack (Telegraf + InfluxDB + Grafana) สำหรับ visualization และ alerting

โครงงานนี้เป็นส่วนหนึ่งของวิชาโครงงานวิศวกรรม สาขา NECS คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีมหานคร

## Architecture

```
┌──────────────────────────┐
│  Cisco ASR1001-X (Edge)  │  ← FlexNetFlow บน hardware QFP
│  - FlexNetFlow Engine    │  ← NECS-RECORD / NECS-EXPORT / MIIX-MONITOR
│  - 14 VLAN (1311-1341)   │
└────────────┬─────────────┘
             │ NetFlow v9 / UDP 2055
             ▼
┌──────────────────────────┐
│   Linux Server (RHEL 9)  │  ← Single host, Docker Compose
│  ┌────────────────────┐  │
│  │ Telegraf 1.38.1    │  │  ← inputs.netflow + processors.starlark
│  │  + tagpass filter  │  │  ← Cardinality control
│  └─────────┬──────────┘  │
│            ▼              │
│  ┌────────────────────┐  │
│  │ InfluxDB 1.8 (tsi1)│  │  ← 4 RP + 5 measurements + 2 CQ
│  └─────────┬──────────┘  │
│            │              │
│  ┌─────────┴──────────┐  │
│  │ Python (Top-N)     │  │  ← topn-rollup.timer (5 min)
│  │ Python (ASN class) │  │  ← auto-classify.timer (daily 03:00)
│  └─────────┬──────────┘  │
│            ▼              │
│  ┌────────────────────┐  │
│  │ Grafana 12.4.1     │  │  ← Dashboard 6 sections + 2 Alert Rules
│  └────────────────────┘  │
└────────────┬─────────────┘
             │
             ▼
    Email + Telegram notifications
```

## Features

- 📡 **Passive Flow Monitoring** ผ่าน FlexNetFlow บน Cisco ASR1001-X (ไม่ต้อง port mirror)
- 📊 **Real-time Dashboard** 6 sections + 2 intro rows ครอบคลุม Top Conversations, Top Talkers, Top Destinations, Protocol, Application, Per-Room
- 🏷️ **ASN-based Application Classification** จากฐานข้อมูล iptoasn.com — ทนทานต่อ HTTPS/TLS encryption
- 📈 **Multi-tier Storage** (4 Retention Policies + 2 Continuous Queries + Top-N Rollup) สำหรับเก็บข้อมูลทั้ง raw 24 ชม., aggregate 7 วัน และ aggregate 180 วัน
- 🔔 **Alert System** 2 มิติ (Infrastructure Health + Time-based Security) ส่งทั้ง Email และ Telegram

## Tech Stack

| Component | Version |
|-----------|---------|
| Cisco ASR1001-X | IOS XE 17.9.08 |
| RHEL Linux Server | 9.6 |
| Docker Engine | 29.4.1 |
| Docker Compose | v5.1.3 |
| Telegraf | 1.38.1 |
| InfluxDB | 1.8 (with tsi1 index) |
| Grafana | 12.4.1 |
| Python | 3.x (system) |

## Quick Start

### 1. Prerequisites

- Linux server (RHEL 9.x recommended) with Docker + Docker Compose
- Cisco ASR1001-X (or compatible) with FlexNetFlow support
- Network reachability from ASR to Linux Server (UDP 2055)

### 2. Configure secrets

```bash
cp .env.example .env
# Edit .env and fill in your real values
nano .env
```

### 3. Deploy TIG Stack

```bash
docker compose up -d
docker compose ps  # verify all 3 containers running
```

### 4. Setup InfluxDB schema

```bash
docker exec -it influxdb influx
> CREATE DATABASE netflow_db;
> # then run continuous-queries.sql contents
```

หรือใช้ไฟล์โดยตรง:
```bash
docker exec -i influxdb influx -database netflow_db < software/influxdb/retention-policies.sql
docker exec -i influxdb influx -database netflow_db < software/influxdb/continuous-queries.sql
```

### 5. Install Python supplementary services

```bash
# Top-N Rollup
sudo cp software/topn-rollup/topn-rollup.{service,timer} /etc/systemd/system/
sudo cp software/topn-rollup/topn_rollup.py /opt/topn_rollup/
sudo systemctl daemon-reload
sudo systemctl enable --now topn-rollup.timer

# ASN Classifier
sudo cp software/asn-classifier/auto-classify.{service,timer} /etc/systemd/system/
sudo cp software/asn-classifier/generate_app_classify.py /opt/topn_rollup/
sudo systemctl enable --now auto-classify.timer
```

### 6. Configure ASR1001-X

ดูใน `hardware/asr1001x/README.md` สำหรับการตั้งค่า FlexNetFlow

> ⚠️ **Note on anonymized values:** This repo uses placeholder IPs for security:
> - Host IPs shown as `xxx.xxx.xxx.xx` — replace with your real ASR/collector/uplink IPs before deploying
> - User subnet patterns shown as `192.168.52/53/54.x` (RFC 1918 private) — replace with your actual user subnet range
> - Credentials, tokens, and email addresses shown as `${VAR_NAME}` — set in `.env`

## Repository Structure

```
.
├── docker-compose.yml          # TIG Stack orchestration
├── .env.example                # Template for secrets
│
├── hardware/                   # → ภาคผนวก ก
│   ├── asr1001x/               # Cisco ASR1001-X FlexNetFlow config
│   ├── hp-switches/            # HP A5500 / 7506 VLAN reference
│   └── linux-server/           # RHEL 9 server specs
│
├── software/                   # → ภาคผนวก ข
│   ├── telegraf/               # ข.1 Telegraf config
│   ├── influxdb/               # ข.2 InfluxDB schema (RP + CQ)
│   ├── grafana/                # ข.3 Grafana dashboards + alerts + templates
│   ├── topn-rollup/            # ข.4 Python Top-N Rollup
│   └── asn-classifier/         # ข.5 Python ASN Classifier
│
└── docs/                       # Documentation
```

## License

MIT — see `LICENSE` for details

## Author

NECS Senior Project — Mahanakorn University of Technology (MUT)
