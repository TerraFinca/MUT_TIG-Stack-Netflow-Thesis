-- Retention Policies for netflow_db
-- See thesis §3.3.4 for tier design rationale

CREATE DATABASE netflow_db;

-- Tier 1: Raw flow records, 24 hours (default)
CREATE RETENTION POLICY "raw_24h" ON "netflow_db"
  DURATION 24h REPLICATION 1 DEFAULT;

-- Tier 2: 5-minute aggregate, 7 days
CREATE RETENTION POLICY "agg_5m_7d" ON "netflow_db"
  DURATION 7d REPLICATION 1;

-- Tier 3: 1-hour aggregate, 180 days
CREATE RETENTION POLICY "agg_1h_180d" ON "netflow_db"
  DURATION 180d REPLICATION 1;

-- Tier 4: Top-N pre-computed (dst + conversations), 180 days
CREATE RETENTION POLICY "topn_180d" ON "netflow_db"
  DURATION 180d REPLICATION 1;
