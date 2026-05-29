# Deployment Guide

คู่มือการ deploy ระบบ MIIX NetFlow Monitoring ตั้งแต่ bare server

## Prerequisites

### Hardware
- Linux server (แนะนำ RHEL 9.x หรือ Ubuntu 22.04+) อย่างน้อย 8 GB RAM, 50 GB disk
- เครือข่ายที่ ASR1001-X สามารถส่ง UDP 2055 มาที่ Linux server ได้
- เข้าถึง CLI ของ Cisco ASR1001-X (console หรือ SSH)

### Software
- Docker Engine 24+
- Docker Compose v2+
- Python 3.8+
- systemd

### Accounts/Tokens
- Gmail account + App Password (สำหรับ SMTP) — สร้างที่ https://myaccount.google.com/apppasswords
- Telegram Bot — talk to @BotFather, ได้ Bot Token + เพิ่มเข้ากลุ่ม + หา Chat ID

---

## Step 1: Setup Linux Server

```bash
# Install Docker (RHEL 9)
sudo dnf install -y dnf-plugins-core
sudo dnf-3 config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker

# Verify
docker --version
docker compose version
```

## Step 2: Clone Repository

```bash
sudo mkdir -p /root/TIG_PRODUCTION
cd /root/TIG_PRODUCTION
git clone https://github.com/YOUR-USERNAME/miix-netflow-monitoring.git .
```

## Step 3: Configure Secrets

```bash
cp .env.example .env
nano .env
```

ใส่ค่า:
```
GF_SMTP_USER=your-email@gmail.com
GF_SMTP_PASSWORD=your-gmail-app-password
GF_SMTP_FROM_ADDRESS=your-email@gmail.com
TELEGRAM_BOT_TOKEN=123456789:ABCxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=your-chat-id
ALERT_EMAIL=recipient@example.com
```

## Step 4: Configure ASR1001-X FlexNetFlow

SSH เข้า ASR1001-X แล้ว apply config จาก `hardware/asr1001x/flexnetflow-config.txt`:

```
configure terminal

! แก้ destination IP ให้เป็น IP ของ Linux server ก่อน
flow exporter NECS-EXPORT
 destination <your-linux-server-ip>
 ...

! Apply ทุก section จากไฟล์
! (flow record, flow exporter, flow monitor, interface bindings)

end
write memory
```

ตรวจสอบ:
```
show flow exporter NECS-EXPORT statistics
show flow monitor MIIX-MONITOR statistics
show flow interface
```

## Step 5: Deploy TIG Stack

```bash
cd /root/TIG_PRODUCTION
docker compose up -d

# ตรวจสอบ 3 containers running
docker compose ps
```

## Step 6: Initialize InfluxDB Schema

```bash
# สร้าง database + retention policies
docker exec -i influxdb influx < software/influxdb/retention-policies.sql

# สร้าง continuous queries
docker exec -i influxdb influx -database netflow_db < software/influxdb/continuous-queries.sql

# ตรวจสอบ
docker exec influxdb influx -execute "SHOW RETENTION POLICIES ON netflow_db"
docker exec influxdb influx -execute "SHOW CONTINUOUS QUERIES"
```

## Step 7: Install Python Services

### Top-N Rollup
```bash
sudo mkdir -p /opt/topn_rollup
sudo cp software/topn-rollup/topn_rollup.py /opt/topn_rollup/
sudo cp software/topn-rollup/topn-rollup.{service,timer} /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now topn-rollup.timer
sudo systemctl status topn-rollup.timer
```

### ASN Classifier
```bash
sudo cp software/asn-classifier/generate_app_classify.py /opt/topn_rollup/
sudo cp software/asn-classifier/auto-classify.{service,timer} /etc/systemd/system/

# Run once to generate initial app_classify.star
sudo python3 /opt/topn_rollup/generate_app_classify.py

sudo systemctl daemon-reload
sudo systemctl enable --now auto-classify.timer
sudo systemctl status auto-classify.timer

# Telegraf reload to pick up new app_classify.star
docker compose restart telegraf
```

## Step 8: Import Grafana Configs

### Dashboard
```bash
# Login Grafana ที่ http://<server-ip>:3000 (admin/admin → set new password)
# Dashboards → Import → Upload JSON → เลือก software/grafana/dashboards/miix-network-monitor-production.json
```

### Alert Rules + Contact Points
Grafana 12.4.1 รองรับ provisioning ผ่านไฟล์ YAML — copy JSON ใน `software/grafana/alerting/` ไปไว้ที่ `/etc/grafana/provisioning/alerting/` (ใน container) หรือ import ผ่าน UI:

```
Alerting → Contact points → Import (paste JSON content)
Alerting → Mute timings → Import
Alerting → Notification policies → Edit + paste
Alerting → Alert rules → Import
```

## Step 9: Verification

ตรวจสอบครบทุก subsystem:

```bash
# 1. FlexNetFlow ส่งข้อมูล
sudo tcpdump -i any udp port 2055 -c 5

# 2. Telegraf รับและ parse
docker logs telegraf --tail 20

# 3. InfluxDB เก็บข้อมูล
docker exec influxdb influx -database netflow_db -execute "SELECT COUNT(*) FROM netflow WHERE time > now() - 5m"

# 4. App tag enrichment
docker exec influxdb influx -database netflow_db -execute "SHOW TAG VALUES FROM netflow WITH KEY = app"

# 5. Top-N pre-computed
docker exec influxdb influx -database netflow_db -execute "SELECT COUNT(*) FROM topn_180d.topn_destinations WHERE time > now() - 10m"

# 6. systemd timers
systemctl list-timers topn-rollup.timer auto-classify.timer

# 7. Cardinality (should be < 100,000)
docker exec influxdb influx -database netflow_db -execute "SHOW SERIES CARDINALITY"

# 8. Grafana health
curl -s http://localhost:3000/api/health
```

## Step 10: Test Alert Notifications

```
Grafana UI → Alerting → Contact points → Email-MIIX → Test
→ ตรวจสอบ Email + Telegram ได้รับ
```

## Troubleshooting

ดู [troubleshooting.md](troubleshooting.md) สำหรับปัญหาที่พบบ่อย
