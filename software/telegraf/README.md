# Telegraf Configuration

Telegraf 1.38.1 — NetFlow collector + processor

## Purpose

1. รับ NetFlow v9 จาก ASR1001-X บน UDP port 2055
2. ทำ application classification ผ่าน `processors.starlark` (ใช้ไฟล์ `app_classify.star`)
3. กรอง cardinality ผ่าน `tagpass` filter ก่อนเขียนลง InfluxDB

## Key Sections in telegraf.conf

| Section | Purpose |
|---------|---------|
| `[[inputs.netflow]]` | Listen on UDP 2055 for NetFlow v9 |
| `[[processors.starlark]]` | Run `app_classify.star` to add `app` tag from dst IP |
| `[[outputs.influxdb]]` with `tagpass` | Filter src to MIIX subnets (192.168.52-54.x) before writing |

> ⚠️ **Anonymization note:** The `tagpass` filter uses placeholder subnets `192.168.52/53/54.x` (RFC 1918 private range). Replace these with your actual user subnet CIDR(s) before deployment.

## Cardinality Control

ระบบใช้กลไกหลายชั้นเพื่อควบคุม cardinality ของ InfluxDB:

1. **Tag/Field decision** — `src`, `dst`, `protocol` เป็น Tag; `in_bytes`, `in_packets`, ports เป็น Field
2. **tagpass filter** — กรอง src ใน 192.168.52-54.x ก่อนเขียนลง InfluxDB
3. **`processors.starlark`** — เพิ่ม `app` tag (cardinality ต่ำ ~30 หมวด)

ดู thesis §3.3.3 + §3.4.2 สำหรับ engineering journey ของ cardinality crisis (2.4M → 63K series)

## Mounted into container via docker-compose.yml

```yaml
volumes:
  - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
  - ./app_classify.star:/etc/telegraf/app_classify.star:ro
```

## Testing

```bash
docker exec telegraf telegraf --config /etc/telegraf/telegraf.conf --test
docker logs telegraf --tail 50
```
