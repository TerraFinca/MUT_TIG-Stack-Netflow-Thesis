# Grafana Email Template Customization

`ng_alert_notification.html` — แก้ Grafana logo เป็น MUT logo สำหรับ alert email

## ทำไมต้อง patch

Grafana default ใช้ logo จาก `grafana.com` ใน alert email — สำหรับโครงงานนี้แก้เป็น MUT logo เพื่อให้ผู้รับเห็นต้นทาง

## Logo Source

ดาวน์โหลดจาก https://mut.ac.th/wp-content/uploads/2025/10/MAHANAKORN-UNIVERSITY-OF-TECHNOLOGY-Logo.svg แล้ว reference URL ตรงจาก template

## Deployment

Mount as read-only volume ใน `docker-compose.yml`:

```yaml
grafana:
  volumes:
    - ./grafana_templates/ng_alert_notification.html:/usr/share/grafana/public/emails/ng_alert_notification.html:ro
```

จากนั้น `docker compose up -d grafana` (recreate container)

## Rollback

ถ้าต้องการกลับไปใช้ Grafana logo เดิม:
```bash
# ลบ volume mount จาก docker-compose.yml
docker compose up -d grafana
# หรือ comment out บรรทัด mount แล้ว recreate
```
