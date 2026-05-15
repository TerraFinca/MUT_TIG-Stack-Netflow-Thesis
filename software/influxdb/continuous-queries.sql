-- Continuous Queries for stepladder aggregation
-- See thesis §3.3.4 for design rationale

-- cq_5m: raw_24h.netflow → agg_5m_7d.netflow_5m every 5 minutes
CREATE CONTINUOUS QUERY "cq_5m" ON "netflow_db"
BEGIN
  SELECT SUM("in_bytes") AS "in_bytes",
         SUM("in_packets") AS "in_packets"
  INTO "agg_5m_7d"."netflow_5m"
  FROM "raw_24h"."netflow"
  GROUP BY time(5m), "src", "app", "protocol"
END;

-- cq_1h: agg_5m_7d.netflow_5m → agg_1h_180d.netflow_1h every 1 hour
CREATE CONTINUOUS QUERY "cq_1h" ON "netflow_db"
BEGIN
  SELECT SUM("in_bytes") AS "in_bytes",
         SUM("in_packets") AS "in_packets"
  INTO "agg_1h_180d"."netflow_1h"
  FROM "agg_5m_7d"."netflow_5m"
  GROUP BY time(1h), "src", "app", "protocol"
END;
