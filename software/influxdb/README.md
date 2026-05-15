# InfluxDB Schema

InfluxDB 1.8 with TSI (Time Series Index) — Time-series storage

## Database

`netflow_db` — single database for all NetFlow data

## Retention Policies (4 tiers)

| RP | Measurement | Duration | Resolution |
|----|-------------|:--------:|------------|
| `raw_24h` (default) | `netflow` | 24h | Per-flow raw |
| `agg_5m_7d` | `netflow_5m` | 7 days | 5-minute aggregate |
| `agg_1h_180d` | `netflow_1h` | 180 days | 1-hour aggregate |
| `topn_180d` | `topn_destinations`, `topn_conversations` | 180 days | Top 200 per 5 min |

## Continuous Queries (2)

- `cq_5m` — `raw_24h.netflow` → `agg_5m_7d.netflow_5m` (GROUP BY time(5m), src, app, protocol)
- `cq_1h` — `agg_5m_7d.netflow_5m` → `agg_1h_180d.netflow_1h` (GROUP BY time(1h), src, app, protocol)

หมายเหตุ: `topn_destinations` และ `topn_conversations` ไม่ได้สร้างผ่าน CQ เพราะ InfluxQL 1.x ไม่รองรับ `TOP()` ร่วมกับ `GROUP BY tag` — ใช้ Python script แทน ดู `../topn-rollup/`

## Environment Variables (set ใน docker-compose.yml)

```
INFLUXDB_DB=netflow_db
INFLUXDB_DATA_INDEX_VERSION=tsi1
INFLUXDB_DATA_MAX_SERIES_PER_DATABASE=0
INFLUXDB_DATA_MAX_VALUES_PER_TAG=0
```

> `tsi1` เก็บ index ใน file system แทน RAM — รองรับ cardinality สูงโดยไม่ระเบิด memory
> ดู thesis §3.4.2 สำหรับ engineering journey

## Files

- `retention-policies.sql` — CREATE DATABASE + 4 RP definitions
- `continuous-queries.sql` — 2 CQ definitions

## Initial Setup

```bash
docker exec -i influxdb influx -database netflow_db < retention-policies.sql
docker exec -i influxdb influx -database netflow_db < continuous-queries.sql
```

## Verification

```bash
docker exec influxdb influx -execute "SHOW RETENTION POLICIES ON netflow_db"
docker exec influxdb influx -execute "SHOW CONTINUOUS QUERIES"
docker exec influxdb influx -database netflow_db -execute "SHOW SERIES CARDINALITY"
```

Expected baseline (1 building, 14 VLAN): ~63,000 series, RAM ~12% of 12 GB
