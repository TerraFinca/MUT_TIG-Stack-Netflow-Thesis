# Top-N Rollup System

Python script + systemd timer สำหรับ pre-compute Top 200 destinations / conversations ทุก 5 นาที

## Why?

InfluxDB 1.x Continuous Query ไม่รองรับ `TOP()` ร่วมกับ `GROUP BY tag` — ดังนั้นต้องเขียน Python script ทำเองแทน

ดู thesis §3.3.6 สำหรับ rationale และ §3.4.5 สำหรับ engineering journey (linear search 114% CPU → binary search 5-10%)

## Files

| File | Purpose |
|------|---------|
| `topn_rollup.py` | Main script (~169 lines) — query InfluxDB, compute Top 200, write back |
| `topn-rollup.service` | systemd service unit |
| `topn-rollup.timer` | systemd timer (OnCalendar=*:0/5 — every 5 min) |

## How it works

ทุก 5 นาที script จะ:
1. Query `raw_24h.netflow` ใน 5-min window (filter src ∈ MIIX subnets, dst ∉ MIIX)
2. รัน 2 functions:
   - `rollback_destinations()` — `GROUP BY dst, app` → Top 200 → write to `topn_destinations`
   - `rollback_conversations()` — `GROUP BY src, dst, app` → Top 200 → write to `topn_conversations`
3. ใช้ Library `requests` เรียก InfluxDB HTTP API ตรง (ไม่ใช้ influxdb-client)

## Installation

```bash
sudo mkdir -p /opt/topn_rollup
sudo cp topn_rollup.py /opt/topn_rollup/
sudo cp topn-rollup.service /etc/systemd/system/
sudo cp topn-rollup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now topn-rollup.timer
```

## Verification

```bash
systemctl status topn-rollup.timer    # Active running
systemctl list-timers topn-rollup     # Next/last run
journalctl -u topn-rollup.service -n 50    # Recent execution log
tail -f /var/log/topn_rollup.log
```

## Configuration

แก้ใน `topn_rollup.py`:
- `TOP_N = 200` — จำนวน records ต่อรอบ
- `WINDOW = 300` — window size เป็นวินาที (5 min)
- InfluxDB URL/credentials — อ่านจาก environment หรือ hard-coded
