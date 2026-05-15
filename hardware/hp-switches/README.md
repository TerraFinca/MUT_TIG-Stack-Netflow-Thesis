# HP Switches — Distribution & Access

HP A5500 (Distribution) และ HP 7506 (Aggregation) ของอาคาร MIIX — ทำหน้าที่ Layer 2 + Layer 3 switching

## VLAN Mapping (อาคาร MIIX)

| VLAN | ห้อง | Subnet |
|------|------|--------|
| 1311 | Indoor + Outdoor (PLC) | — |
| 1312 | PLC + 3D Printing | — |
| 1313 | Robotic Lab | — |
| 1314 | Indoor + Outdoor Workshop | — |
| 1315 | Staff Room | — |
| 1321 | Student Project Room | — |
| 1322 | Innovation Room | — |
| 1323 | MUT Satellite Center | — |
| 1324 | Office 1-2-3 | — |
| 1325 | Air Control | — |
| 1331 | Electronic Lab 1-2 | — |
| 1332 | Micro Lab | — |
| 1333 | Electronic Lab 3 | — |
| 1341 | Teacher Room | — |

## Notes

- **NetFlow ไม่ได้ตั้งบน HP switches** — Passive monitoring เกิดที่ ASR1001-X (edge router)
- HP switches ทำหน้าที่ L2 switching ภายใน VLAN และ L3 routing ระหว่าง VLAN
- Layer 2 broadcast/multicast storm ภายใน VLAN จะไม่ปรากฏใน NetFlow → ต้องใช้ SNMP/sFlow ที่ HP switch ถ้าต้องการตรวจ (ดู Future Work ในเล่ม §4.3.6)

## Out of scope

การกำหนดค่า HP switch ทั้งหมดอยู่นอกขอบเขตของโครงงาน (เป็น production network ที่มีอยู่แล้ว) เอกสารนี้บันทึกเฉพาะข้อมูลที่จำเป็นต่อการอ้างอิงในระบบ monitoring
