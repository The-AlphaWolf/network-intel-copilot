---
doc_id: congestion-triage-runbook
title: Congestion Incident Triage Runbook
version: "2.1"
category: runbook
owner: Network Operations Center
---

> Synthetic reference documentation authored for this demonstration system.

# Congestion Incident Triage Runbook

Use this runbook when a cell shows elevated latency and/or packet loss and
congestion is suspected.

## Step 1: Confirm the congestion signature

Pull PRB utilization, active users, RSRP, RSRQ, and SINR for the affected
cell over the incident window.

- PRB utilization sustained above 85%: congestion likely.
- RSRP/RSRQ/SINR within normal range: rules out coverage/interference as the
  primary cause.
- Active user count elevated relative to the cell's typical busy-hour
  baseline: confirms a demand-side event.

If PRB utilization is normal but latency is elevated, stop this runbook and
follow the Transport & Backhaul Troubleshooting Guide instead.

## Step 2: Check for a root demand cause

- Correlate with known events (stadium, transit hub, planned maintenance on
  a neighbor cell that shifted load, promotional data offer).
- Check neighbor cells for simultaneous PRB spikes indicating an area-wide
  event versus a single-cell anomaly.
- Check for RRC connection reject or admission control log events, which
  confirm the cell is actively shedding load.

## Step 3: Immediate mitigation

1. If neighbor cells have PRB headroom (< 60%), trigger load-balancing
   mobility parameter adjustment to steer new attaches toward them.
2. If UEs support carrier aggregation and a secondary carrier has headroom,
   enable/expand CA policy for this cell.
3. If neither is available and congestion is severe (PRB > 95%, packet loss
   > 2%), apply scheduler QoS prioritization to protect latency-sensitive
   traffic while the underlying capacity issue is addressed.

## Step 4: Escalation criteria

Escalate to RAN Planning if:

- Congestion recurs on 3+ consecutive busy-hour windows after mitigation.
- No neighbor cell has usable headroom for load balancing.
- Active user count has structurally exceeded the cell's provisioned design
  capacity (see Capacity Planning Guidelines).

## Step 5: Verification

After mitigation, confirm within 2 measurement windows that:

- PRB utilization has dropped below 85%.
- Latency has returned to within 20% of the cell's baseline.
- Packet loss has returned below 0.5%.

Document the incident with timestamps, applied mitigation, and time-to-
resolution for the capacity planning backlog.
