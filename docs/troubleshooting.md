# Troubleshooting Guide

ปัญหาที่พบบ่อยและวิธีแก้ — เรียงตามที่เจอจริงในระหว่างพัฒนาโครงงาน

---

## Cardinality Explosion

### Symptom
- RAM ของ Linux server พุ่งสูง (>80%)
- InfluxDB container ถูก OOM Killer หยุดทำงาน → restart loop
- Grafana panels แสดง "No data" หรือ query timeout
- `docker stats` แสดง InfluxDB ใช้ RAM ~10+ GB

### Diagnose
```bash
docker exec influxdb influx -database netflow_db \
  -execute "SHOW SERIES CARDINALITY"
# ถ้า > 500,000 series → cardinality crisis

docker logs influxdb --tail 100 | grep -i "memory\|oom\|cardinal"
free -m
```

### Root Cause
มักจะเป็นการ deploy ด้วย default config (`inmem` index + `dst` IP เป็น tag) → unique destination IP ระเบิดเป็นล้าน series ใน 24 ชั่วโมง

### Fix (3-step optimization)
1. **Switch index engine** เป็น `tsi1` (file-based) — ใน `docker-compose.yml`:
   ```yaml
   environment:
     - INFLUXDB_DATA_INDEX_VERSION=tsi1
     - INFLUXDB_DATA_MAX_SERIES_PER_DATABASE=0
     - INFLUXDB_DATA_MAX_VALUES_PER_TAG=0
   ```

2. **เพิ่ม tagpass filter** ใน `telegraf.conf`:
   ```toml
   [[outputs.influxdb]]
   tagpass = { src = ["192.168.52.*", "192.168.53.*", "192.168.54.*"] }
   ```

3. **Move dst เก็บแยกใน topn_180d** ผ่าน Top-N Rollup script (ไม่เก็บ dst ใน aggregate RPs)

### Expected after fix
- ~63,000 series (จากเดิม 2,400,000 = ลด 38 เท่า)
- RAM ใช้ ~12% (1.3 GB จาก 12 GB)

อ้างอิงเพิ่มเติม: thesis §3.4.2

---

## NetFlow Packets ไม่ถึง Server

### Symptom
- `SELECT COUNT(*) FROM netflow` ไม่เพิ่มขึ้น
- `docker logs telegraf` ไม่มี debug log แสดง flow received

### Diagnose
```bash
# Step 1: ตรวจที่ ASR ว่า export มีจริง
# (บน ASR CLI)
show flow exporter NECS-EXPORT statistics
# ดูว่า "Sent" counter เพิ่มไหม

# Step 2: ตรวจที่ Linux ว่า packet มาถึง
sudo tcpdump -i any udp port 2055 -c 10
# ถ้าเห็น packet → network OK, ปัญหาอยู่ที่ Telegraf
# ถ้าไม่เห็น → ปัญหา network/routing/firewall

# Step 3: Telegraf input config
docker exec telegraf cat /etc/telegraf/telegraf.conf | grep -A 5 "netflow"
```

### Common Causes
- Firewall บน Linux block UDP 2055 → `sudo firewall-cmd --add-port=2055/udp --permanent && sudo firewall-cmd --reload`
- ASR exporter `source` interface ผิด → traffic ออกจาก source IP ที่ unreachable
- Routing ระหว่าง ASR และ Linux server ไม่ตรง → `ping` ตรวจสอบ
- Telegraf ไม่ได้ bind port 2055 → ตรวจ `docker-compose.yml` port mapping

---

## App Classification ไม่ทำงาน (ทุก flow tag = "Other")

### Symptom
- `SHOW TAG VALUES FROM netflow WITH KEY = app` → ทุก value = "Other"
- Section 5 Application Detection ใน Dashboard แสดงแต่ "Other"

### Diagnose
```bash
# 1. ตรวจว่า app_classify.star มีอยู่
docker exec telegraf ls -la /etc/telegraf/app_classify.star

# 2. ตรวจขนาดไฟล์ (ควร ~500 KB)
docker exec telegraf wc -c /etc/telegraf/app_classify.star

# 3. ตรวจ Starlark processor error
docker logs telegraf | grep -i "starlark\|app_classify"

# 4. ตรวจ Telegraf reload หลัง generate script ใหม่
docker compose restart telegraf
```

### Common Causes
- ไฟล์ `app_classify.star` ยังไม่ถูก generate → รัน `sudo python3 /opt/topn_rollup/generate_app_classify.py`
- Volume mount ใน docker-compose.yml ผิด path
- ในไฟล์ `app_classify.star` มี syntax error จาก dst ผิด — fix: ตรวจว่า apply function อ่าน dst จาก `metric.tags["dst"]` ไม่ใช่ `metric.fields["dst"]`

---

## Alert ไม่ Fire

### Symptom
- เห็น threshold ถูกละเมิดใน dashboard แต่ Alert ไม่เปลี่ยน state เป็น Firing
- Grafana Alert state ค้างที่ "Normal" หรือ "NoData"

### Diagnose
```
Grafana UI → Alerting → Alert rules → คลิกที่ rule → ดู State history
```

### Common Causes
- **Pending Period ยังไม่ครบ** — Rule ที่ตั้ง `for: 5m` ต้องละเมิด threshold ครบ 5 นาทีก่อน Firing
- **Mute Timing block** — ตรวจว่า routing policy กำหนด mute timing ที่อยู่ในช่วงปัจจุบัน
- **No data state** — ถ้า query return ไม่มีข้อมูล Alert จะเป็น NoData (ตั้งใน `noDataState`)
- **Query error** — ตรวจ datasource health, InfluxDB up หรือไม่

---

## Alert Fire บ่อยเกินไป (False Positive)

### Symptom
- Telegram/Email notification เข้ามาเยอะเกินไป
- Alert state กระพริบ Normal ↔ Pending ↔ Firing บ่อย

### Common Cause + Fix
1. **Threshold ต่ำเกินไป** → ปรับ threshold ให้สูงขึ้น
2. **Pending Period สั้นเกินไป** → เพิ่ม `for:` เป็น 5-15 นาที
3. **Baseline-based detection ไม่เหมาะ** → พิจารณา behavior-based แทน
4. **ไม่มี mute timing** → เพิ่ม Mute Timing สำหรับ off-hours

ดู thesis §3.4.4 สำหรับ engineering journey ของการ refine alert design

---

## Top-N Data Stale หรือไม่ Update

### Symptom
- Section 1 Top Conversations แสดงข้อมูลเก่า ไม่ update
- `SELECT * FROM topn_180d.topn_destinations WHERE time > now() - 10m` ไม่มีผล

### Diagnose
```bash
# 1. ตรวจ timer status
systemctl status topn-rollup.timer
systemctl list-timers topn-rollup

# 2. ตรวจ recent execution
journalctl -u topn-rollup.service -n 50

# 3. ตรวจ log file
tail -50 /var/log/topn_rollup.log

# 4. รัน manual
sudo systemctl start topn-rollup.service
```

### Common Causes
- Timer ไม่ active → `sudo systemctl enable --now topn-rollup.timer`
- Python script error (InfluxDB unreachable, query syntax) → ดู `journalctl` log
- Permission error เขียน `/var/log/topn_rollup.log`

---

## Grafana Email Logo เป็น Grafana ปกติ (ไม่ใช่ MUT)

### Symptom
- Alert email ส่งมาแต่ logo ด้านบนเป็น Grafana logo

### Diagnose
```bash
# ตรวจว่า volume mount ติด
docker inspect grafana --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' | grep ng_alert

# ตรวจ template content
docker exec grafana grep "mut.ac.th" /usr/share/grafana/public/emails/ng_alert_notification.html
```

### Fix
ใน `docker-compose.yml` ตรวจว่ามี volume mount:
```yaml
grafana:
  volumes:
    - ./grafana_templates/ng_alert_notification.html:/usr/share/grafana/public/emails/ng_alert_notification.html:ro
```

แล้ว `docker compose up -d grafana` (recreate)

---

## InfluxDB Container Restart Loop

### Symptom
- `docker ps` แสดง influxdb container ขึ้นแล้วดับซ้ำ ๆ

### Diagnose
```bash
docker logs influxdb --tail 100
docker compose logs influxdb
```

### Common Causes
1. **Permission ผิดบน volume** — fix: `sudo chown -R 1000:1000 ./influxdb_data`
2. **Disk เต็ม** — `df -h`, ลบ data หรือเพิ่ม disk
3. **OOM kill** — RAM ไม่พอ ดู [Cardinality Explosion](#cardinality-explosion)
4. **Config error** — env variable พิมพ์ผิด

---

## ระบบทั้งหมดเงียบ (ไม่มี traffic หลายชั่วโมง)

### Symptom
- Alert `MIIX-NetFlow-Collector-Health` fire
- Dashboard ทุก panel แสดง No Data

### Diagnose
รัน verification checklist จาก [deployment-guide.md Step 9](deployment-guide.md#step-9-verification) ทุกข้อ — จะระบุ subsystem ที่ล้มเหลว

### Recovery Steps
1. ตรวจ ASR + Telegraf + InfluxDB ทีละชั้น (ตามลำดับ data flow)
2. หา subsystem แรกที่ fail → focus diagnose ที่นั่น
3. ถ้าทุก subsystem OK แต่ flow ไม่มา → ตรวจ network routing
