#!/usr/bin/env python3
"""
TopN Rollback for NetFlow Architecture v6 (180-day)

Queries raw_24h every 5 minutes:
- Top 200 destinations (dst, app)
- Top 200 conversations (src, dst, app)

Writes to topn_180d retention policy.
"""
import sys
import logging
import requests
from datetime import datetime, timezone

INFLUX_URL = "http://localhost:8086"
DATABASE = "netflow_db"
TOP_N = 200
WINDOW = "5m"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/topn_rollup.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger()


def query(q):
    r = requests.get(
        f"{INFLUX_URL}/query",
        params={"db": DATABASE, "q": q},
        timeout=60
    )
    r.raise_for_status()
    return r.json()


def write_points(rp, lines):
    if not lines:
        return
    r = requests.post(
        f"{INFLUX_URL}/write",
        params={"db": DATABASE, "rp": rp, "precision": "s"},
        data="\n".join(lines),
        timeout=60
    )
    r.raise_for_status()


def escape_tag(v):
    return str(v).replace(",", "\\,").replace("=", "\\=").replace(" ", "\\ ")


def rollback_destinations(ts):
    """Top 200 destinations by traffic"""
    q = (
        'SELECT sum("in_bytes") AS "v", sum("in_packets") AS "p" '
        'FROM "raw_24h"."netflow" '
        f'WHERE time >= now() - {WINDOW} AND time < now() '
        'AND "src" =~ /^203\\.188\\.5/ '
        'AND "dst" !~ /^203\\.188\\./ '
        'AND "dst" !~ /^224\\./ AND "dst" !~ /^10\\./ '
        'AND "dst" !~ /^172\\./ AND "dst" !~ /^192\\.168\\./ '
        'GROUP BY "dst", "app"'
    )

    result = query(q)
    series = result.get('results', [{}])[0].get('series', [])

    records = []
    for s in series:
        tags = s.get('tags', {})
        dst = tags.get('dst', '')
        app = tags.get('app', 'Other')
        if not dst:
            continue
        values = s.get('values', [])
        if not values:
            continue
        total_bytes = sum(v[1] for v in values if v[1] is not None)
        total_packets = sum(v[2] for v in values if v[2] is not None)
        if total_bytes > 0:
            records.append((dst, app, total_bytes, total_packets))

    records.sort(key=lambda x: x[2], reverse=True)
    top = records[:TOP_N]

    lines = []
    for dst, app, b, p in top:
        lines.append(
            f"topn_destinations,dst={escape_tag(dst)},app={escape_tag(app)} "
            f"in_bytes={int(b)}i,in_packets={int(p)}i {ts}"
        )

    write_points("topn_180d", lines)
    log.info(f"Destinations: {len(records)} unique -> wrote Top {len(lines)}")


def rollback_conversations(ts):
    """Top 200 conversations by traffic"""
    q = (
        'SELECT sum("in_bytes") AS "v", sum("in_packets") AS "p" '
        'FROM "raw_24h"."netflow" '
        f'WHERE time >= now() - {WINDOW} AND time < now() '
        'AND "src" =~ /^203\\.188\\.5/ '
        'AND "dst" !~ /^203\\.188\\./ '
        'AND "dst" !~ /^224\\./ AND "dst" !~ /^10\\./ '
        'AND "dst" !~ /^172\\./ AND "dst" !~ /^192\\.168\\./ '
        'GROUP BY "src", "dst", "app"'
    )

    result = query(q)
    series = result.get('results', [{}])[0].get('series', [])

    records = []
    for s in series:
        tags = s.get('tags', {})
        src = tags.get('src', '')
        dst = tags.get('dst', '')
        app = tags.get('app', 'Other')
        if not src or not dst:
            continue
        values = s.get('values', [])
        if not values:
            continue
        total_bytes = sum(v[1] for v in values if v[1] is not None)
        total_packets = sum(v[2] for v in values if v[2] is not None)
        if total_bytes > 0:
            records.append((src, dst, app, total_bytes, total_packets))

    records.sort(key=lambda x: x[3], reverse=True)
    top = records[:TOP_N]

    lines = []
    for src, dst, app, b, p in top:
        lines.append(
            f"topn_conversations,src={escape_tag(src)},dst={escape_tag(dst)},app={escape_tag(app)} "
            f"in_bytes={int(b)}i,in_packets={int(p)}i {ts}"
        )

    write_points("topn_180d", lines)
    log.info(f"Conversations: {len(records)} unique -> wrote Top {len(lines)}")


def main():
    log.info("=== TopN Rollback START ===")
    now = datetime.now(timezone.utc)
    minute = (now.minute // 5) * 5
    ts = int(now.replace(minute=minute, second=0, microsecond=0).timestamp())
    
    try:
        rollback_destinations(ts)
    except Exception as e:
        log.error(f"Destinations rollback failed: {e}")
    
    try:
        rollback_conversations(ts)
    except Exception as e:
        log.error(f"Conversations rollback failed: {e}")
    
    log.info("=== TopN Rollback DONE ===")


if __name__ == "__main__":
    main()
