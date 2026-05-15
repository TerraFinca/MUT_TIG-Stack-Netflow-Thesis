# Grafana Dashboard & Alerting

Grafana 12.4.1 — Visualization + Unified Alerting

## Contents

- `dashboards/` — Exported dashboard JSON
- `alerting/` — Alert rules, contact points, mute timings, notification policies
- `templates/` — Custom email template with MUT logo

## Dashboard Structure

| Layer | Section |
|-------|---------|
| **Intro Row 1** | Network Traffic Overview (Stacked Timeseries Bandwidth per VLAN) |
| **Intro Row 2** | Live Summary (Stat Cards 4 ตัว: Total Traffic / Flows / Active Users / Unique Sites) |
| **Section 1** | Top 10 Conversations |
| **Section 2** | Top 10 Talkers (+ IP-to-Room mapping) |
| **Section 3** | Top 10 External Destinations |
| **Section 4** | Protocol Distribution |
| **Section 5** | Application Detection (ASN-based) |
| **Section 6** | Per-Room Usage (VLAN dropdown filter) |

Template Variables:
- `$resolution` — Last 24h / 7 days / 180 days (maps to raw_24h / agg_5m_7d / agg_1h_180d)
- `$vlan` — 14 VLAN ของอาคาร MIIX

## Alert Rules (2 dimensions)

1. **MIIX-NetFlow-Collector-Health** (Infrastructure)
   - Query: `count(in_bytes) FROM raw_24h.netflow WHERE time > now() - 10m`
   - Fire if = 0 for 5 minutes
   - Severity: critical
   - Mute: none (24/7)

2. **MIIX-After-Hours-Activity** (Time-based Security)
   - Query: `SUM(in_bytes) FROM agg_5m_7d.netflow_5m WHERE time > now() - 30m` (MIIX subnets)
   - Fire if > 50 MB for 30 minutes
   - Severity: warning
   - Mute: daytime-mute (06:00-22:00) → fires only 22:00-06:00

## Contact Points

- `Email-MIIX` — Gmail SMTP → ${ALERT_EMAIL}
- `Telegram-MIIX` — Bot → ${TELEGRAM_BOT_TOKEN} / ${TELEGRAM_CHAT_ID}

## Mute Timings

- `daytime-mute` — 06:00-22:00 ทุกวัน (สำหรับ After-Hours)
- `outside-business-hours` — Sat/Sun + Mon-Fri 18:00-08:00 (reserved)
- `office-hours` — Mon-Fri 08:00-18:00 (reserved)

## Custom Email Template

`templates/ng_alert_notification.html` — แก้ Grafana logo เป็น MUT logo (reference SVG URL ตรงจาก `https://mut.ac.th/wp-content/uploads/2025/10/MAHANAKORN-UNIVERSITY-OF-TECHNOLOGY-Logo.svg`)

Mount via docker-compose.yml:
```yaml
volumes:
  - ./grafana_templates/ng_alert_notification.html:/usr/share/grafana/public/emails/ng_alert_notification.html:ro
```

> ⚠️ **Anonymization note:** Dashboard and alert rule queries use placeholder subnets `192.168.52/53/54.x`. After import you must edit the InfluxQL queries (search/replace `192\.168\.5[2-4]\.` → your actual subnet regex) for the panels and alerts to match real traffic.

## Import / Restore

```bash
# Dashboard
curl -X POST -H "Content-Type: application/json" -u admin:admin \
  -d @dashboards/miix-production-final.json \
  http://localhost:3000/api/dashboards/db

# Alert rules (use provisioning file or API)
# See https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/
```
