# ASN-based Application Classifier

Python script ที่ generate `app_classify.star` (Starlark) สำหรับใช้ใน Telegraf processor — แปลง destination IP → ชื่อ Application โดยอาศัย ASN

## Why ASN-based?

ในยุค HTTPS/TLS 1.3 + ECH การจำแนกผ่าน DPI ไม่ยั่งยืน — ASN-based ทนทานต่อ encryption ทุกระดับเพราะใช้ network-layer signal

ดู thesis §2.3.5 (rationale) + §3.3.5 (implementation)

## Files

| File | Purpose |
|------|---------|
| `generate_app_classify.py` | Main generator — download iptoasn.com data, build Starlark file |
| `auto-classify.service` | systemd service unit |
| `auto-classify.timer` | systemd timer (daily 03:00) |
| `app_classify.star` | **NOT in repo** — auto-generated output (in `.gitignore`) |

## How it works

1. Download `ip2asn-v4.tsv.gz` จาก https://iptoasn.com (~6.7 MB, public domain)
2. Parse → `asn_ranges = {ASN: [(start_ip, end_ip), ...]}`
3. รวม ranges ของทุก ASN ใน `APP_ASNS` dictionary แล้ว merge contiguous
4. Flatten + sort → 3 parallel arrays (STARTS, ENDS, APPS) สำหรับ binary search O(log n)
5. Write เป็นไฟล์ `app_classify.star`

## APP_ASNS Dictionary

อยู่ใน `generate_app_classify.py` — manual-curated list ของ Application → ASN mapping

ตัวอย่าง:
```python
APP_ASNS = {
    "YouTube/Google":   [15169, 36040, 36384, ...],
    "LINE":             [38631, 23576, 17676],
    "Thai-Local":       [9931, 9737, 17552, ...],  # CAT, TOT, TRUE, ...
    # ...
}
```

**ไม่กำหนดจำนวนหมวดตายตัว** — รายการเติบโตได้ตาม ASN ที่พบใน traffic จริง (manual curation pattern)
เมื่อเห็น traffic ใน "Other" category ที่ใช้ Bandwidth สูง → เพิ่ม ASN เข้า dict → rerun script

## Installation

```bash
sudo mkdir -p /opt/topn_rollup
sudo cp generate_app_classify.py /opt/topn_rollup/
sudo cp auto-classify.service /etc/systemd/system/
sudo cp auto-classify.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now auto-classify.timer

# Run once to generate initial app_classify.star
sudo python3 /opt/topn_rollup/generate_app_classify.py
```

## Verification

```bash
systemctl status auto-classify.timer
ls -la /root/TIG_PRODUCTION/app_classify.star  # Should be ~500 KB
docker exec influxdb influx -database netflow_db -execute "SHOW TAG VALUES FROM netflow WITH KEY = app"
```

## Performance Notes

- **Binary search** (O(log n)) แทน linear search → CPU 5-10% (เดิม 114% ก่อน refactor)
- ใช้ pre-sorted parallel arrays แทน dict lookup → memory-efficient
- File size ~500 KB ครอบคลุม IP ranges ~300 ล้าน address
