# Cisco ASR1001-X — FlexNetFlow Configuration

อุปกรณ์ edge router หลักของมหาวิทยาลัย ทำหน้าที่ Passive Flow Monitoring สำหรับ traffic ของอาคาร MIIX

## Hardware

| Spec | Value |
|------|-------|
| Model | Cisco ASR1001-X |
| Serial | JAE27240TQ6 |
| Hostname | MUT-Q-SRV-EDGE1 |
| IOS XE | 17.9.08 |
| BGP AS | 55760 |

## Interface Bindings (Production Path)

| Interface | Role | Subnet |
|-----------|------|--------|
| TenGigabitEthernet0/0/0 | KSC 8 Gbps Internet Uplink | xxx.xxx.xxx.xx/30 |
| TenGigabitEthernet0/0/1 | Campus-facing | xxx.xxx.xxx.xx/24 |
| GigabitEthernet0/0/2 | (3BB — out of thesis scope) | — |

## FlexNetFlow Components

1. **flow record NECS-RECORD** — Match: ipv4 dscp, protocol, src/dst addr, transport src/dst port; Collect: counter bytes/packets long, timestamp sys-uptime first/last
2. **flow exporter NECS-EXPORT** — Destination: xxx.xxx.xxx.xx UDP 2055, template-data timeout 60
3. **flow monitor MIIX-MONITOR** — Cache active 60s / inactive 15s, 200K entries
4. **Interface binding** — `ip flow monitor MIIX-MONITOR input` AND `output` บน Te0/0/0 + Te0/0/1

> ⚠️ **Anonymization note:** IP addresses in `flexnetflow-config.txt` are shown as `xxx.xxx.xxx.xx`. Replace with your actual collector IP, ASR-side IP, and uplink IPs before applying to a real device.

## Configuration Files

- `flexnetflow-config.txt` — `show run | section flow` output

> **Note:** ไฟล์ flexnetflow-config.txt ในตอนนี้ยังว่างอยู่ — เพิ่ม output ของ `show run | section flow` จากอุปกรณ์ ASR เพื่อให้ผู้ทำซ้ำสามารถ apply ได้ตรง ๆ

## Verification Commands

```
show flow exporter NECS-EXPORT statistics
show flow monitor MIIX-MONITOR statistics
show flow interface
```

## Notes

- FlexNetFlow ทำงานใน hardware QFP — ไม่ใช้ CPU control plane
- Sampling Rate 1:1 (ทุก packet)
- ใช้ทั้ง input + output direction → จับ flow ครบ 2 ทิศทาง
