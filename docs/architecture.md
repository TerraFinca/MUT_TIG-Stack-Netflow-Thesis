# Architecture

เอกสารนี้สรุปสถาปัตยกรรมโดยรวมและเหตุผลของการเลือกออกแบบในแต่ละชั้นของระบบ

## System Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                       CISCO ASR1001-X (Edge Router)                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FlexNetFlow (Hardware QFP)                                  │  │
│  │  • flow record NECS-RECORD (7 match keys / 5 collect)        │  │
│  │  • flow exporter NECS-EXPORT (UDP 2055, NetFlow v9)          │  │
│  │  • flow monitor MIIX-MONITOR (cache 60s / 15s, 200K entries) │  │
│  └────────┬─────────────────────────────────────────────────────┘  │
│           │ bound to Te0/0/0 (Internet uplink) + Te0/0/1 (Campus)  │
│           │ both input AND output direction                        │
└───────────┼────────────────────────────────────────────────────────┘
            │
            │ NetFlow v9 / UDP 2055
            ▼
┌────────────────────────────────────────────────────────────────────┐
│                  LINUX SERVER (RHEL 9.6, 12 GB RAM)                │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Telegraf 1.38.1                                             │  │
│  │  • inputs.netflow (UDP 2055)                                 │  │
│  │  • processors.starlark (app_classify.star) → tag "app"       │  │
│  │  • tagpass filter (src ∈ MIIX subnets) → cardinality control │  │
│  └────────┬─────────────────────────────────────────────────────┘  │
│           ▼                                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  InfluxDB 1.8 (tsi1 index)                                   │  │
│  │  • Database: netflow_db                                      │  │
│  │  • Retention Policies (4 tiers):                             │  │
│  │     - raw_24h     : netflow                  (24 hours)      │  │
│  │     - agg_5m_7d   : netflow_5m               (7 days)        │  │
│  │     - agg_1h_180d : netflow_1h               (180 days)      │  │
│  │     - topn_180d   : topn_destinations,                       │  │
│  │                     topn_conversations       (180 days)      │  │
│  │  • Continuous Queries: cq_5m, cq_1h (stepladder aggregation) │  │
│  └────────┬──────────────────────────────────────────┬──────────┘  │
│           │                                          │             │
│  ┌────────┴──────────┐              ┌────────────────┴──────────┐  │
│  │ Python (systemd)  │              │  Python (systemd)         │  │
│  │ topn-rollup.timer │              │  auto-classify.timer      │  │
│  │ every 5 min       │              │  daily 03:00              │  │
│  │ → topn_180d.*     │              │  → app_classify.star      │  │
│  └───────────────────┘              └───────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Grafana 12.4.1                                              │  │
│  │  • Dashboard 6 sections + 2 intro rows                       │  │
│  │  • Unified Alerting 2 rules (Infra Health + After-Hours)     │  │
│  │  • Contact Points: Email-MIIX, Telegram-MIIX                 │  │
│  └────────┬─────────────────────────────────────────────────────┘  │
└───────────┼────────────────────────────────────────────────────────┘
            │
            ▼
   Email + Telegram notifications → ผู้ดูแลระบบ
```

## Data Flow (Step-by-step)

1. **Capture** — ASR1001-X capture flow records ใน hardware QFP จาก traffic ที่ผ่าน Te0/0/0 และ Te0/0/1 ทั้ง input และ output direction (จับครบ 2 ทิศทาง)
2. **Export** — แปลงเป็น NetFlow v9 packets ส่งผ่าน UDP 2055 ไปยัง Linux Server (xxx.xxx.xxx.xx)
3. **Ingest** — Telegraf inputs.netflow รับ และ parse เป็น metric
4. **Enrich** — processors.starlark โหลด `app_classify.star` → binary search หา ASN จาก dst IP → tag `app`
5. **Filter** — tagpass filter ใน outputs.influxdb กรองเฉพาะ src ∈ 192.168.52-54.x (อาคาร MIIX) เพื่อควบคุม cardinality
6. **Store** — เขียนลง `raw_24h.netflow` (default RP, 24 ชั่วโมง)
7. **Aggregate** — Continuous Queries รวมเป็น 5-min (cq_5m → `agg_5m_7d.netflow_5m`) และ 1-hour (cq_1h → `agg_1h_180d.netflow_1h`)
8. **Top-N Pre-compute** — Python script `topn_rollup.py` รันทุก 5 นาที เขียน Top 200 destinations และ Top 200 conversations ลง `topn_180d`
9. **Visualize** — Grafana Dashboard query ตาม resolution dropdown ($resolution variable)
10. **Alert** — Grafana Unified Alerting ตรวจ 2 rules → ส่ง Email + Telegram

## Key Design Decisions

### 1. ทำไมใช้ FlexNetFlow บน ASR1001-X (ไม่ใช่ Port Mirroring)

| Approach | Pros | Cons |
|----------|------|------|
| FlexNetFlow บน ASR | ทำงานใน hardware QFP, ไม่ใช้ CPU control plane, ไม่ต้อง hardware เพิ่ม, จับ flow 2 ทิศทางในจุดเดียว | ต้องการ ASR (อยู่แล้ว) |
| Port Mirroring | สามารถจับ raw packet ได้ | ต้อง switch port เพิ่ม + collector dedicated + bandwidth duplicate |

→ **เลือก FlexNetFlow** เพราะใช้ resource ที่มีอยู่และ scope ของ thesis คือ flow-level monitoring (ไม่ต้องการ raw packet)

### 2. ทำไมใช้ ASN-based Classification (ไม่ใช่ DPI)

ในยุค HTTPS/TLS 1.3 + Encrypted ClientHello (ECH ที่กำลังแพร่หลายในปี 2568-2569):
- **DPI ที่อาศัย payload** → ไม่ทำงาน เพราะ payload เข้ารหัส
- **DPI ที่อาศัย SNI** → ใช้ได้ในระยะสั้น แต่ ECH จะปิด SNI ในอนาคต
- **ASN-based** → ทนทานเพราะใช้ network-layer signal (destination IP → ASN) ไม่ขึ้นกับการเข้ารหัส

Trade-off: coverage จำกัดตามรายการ ASN ที่ curate (ปัจจุบันจำแนกได้ ~40% ของ bytes)

### 3. ทำไมใช้ Stepladder CQ + Top-N Python (ไม่ใช่ raw query)

**Cardinality Control Strategy** — ดู [troubleshooting.md](troubleshooting.md#cardinality-explosion) สำหรับ engineering journey

- **raw_24h** ใช้ tag `src` + `dst` + `app` → cardinality สูง (เก็บได้แค่ 24 ชม.)
- **agg_5m_7d / agg_1h_180d** ใช้ GROUP BY src, app, protocol (ไม่มี dst) → cardinality ต่ำ → เก็บได้นาน
- **topn_180d** ใช้ Python pre-compute Top 200 (CQ ไม่รองรับ TOP() + GROUP BY tag) → ได้ Top destinations พร้อม dst tag

### 4. ทำไมใช้ Single-host Docker Compose (ไม่ใช่ K8s / Cluster)

Scope ของ thesis คือ 1 อาคาร (MIIX) — load ที่ ~63K series, RAM 12% ของ 12 GB — เกินคุ้ม

สำหรับ scale ไป multi-building ในอนาคต ดู [§4.3.2 ใน thesis] หรือ ClickHouse migration plan

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **ASR1001-X** | Capture + export flow records (hardware-based) |
| **Telegraf** | Ingest NetFlow + enrich `app` tag + filter cardinality |
| **InfluxDB** | Time-series storage + automatic downsampling |
| **Top-N Rollup script** | Pre-compute Top destinations/conversations (CQ workaround) |
| **ASN Classifier script** | Maintain `app_classify.star` (regenerate daily) |
| **Grafana** | Dashboard visualization + alerting + notification routing |

## References

- Thesis §3.3 (Engineering details per phase)
- Thesis §3.4 (Test results + Engineering Journey)
- Thesis §4.2 (Lessons learned + remaining limitations)
- Thesis §4.3 (Future Work recommendations)
