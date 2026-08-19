---
doc_id: prb-utilization-capacity
title: PRB Utilization and Capacity Management
version: "1.0"
category: capacity
owner: RAN Performance Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# PRB Utilization and Capacity Management

## What PRB utilization measures

Physical Resource Blocks (PRBs) are the smallest schedulable unit of
frequency-time resource in NR. PRB utilization is the fraction of available
PRBs scheduled in a measurement window, separately tracked for uplink and
downlink. It is the single strongest predictor of cell-level congestion.

## Congestion signature

A cell entering congestion typically shows, in this order:

1. Active user count rises above the cell's provisioned capacity for its
   bandwidth/band combination.
2. PRB utilization climbs past 85% during busy-hour windows.
3. Per-user throughput falls as the scheduler divides a fixed resource pool
   across more users.
4. Queuing at the scheduler increases user-plane latency (typically +30 to
   +80 ms above baseline) even though the transport network is healthy.
5. Buffer overflows at the RLC/PDCP layer under sustained saturation produce
   measurable packet loss (typically 1-3%).

Crucially, RSRP, RSRQ, and SINR remain within normal range during pure
congestion - the radio link itself is fine, the resource pool is exhausted.
This distinguishes congestion from interference or coverage problems, which
directly degrade the radio link quality metrics.

## Distinguishing congestion from backhaul degradation

Both congestion and backhaul degradation raise latency and packet loss, but:

- Congestion: PRB utilization > 85%, latency rise correlates tightly with
  active user count, throughput per user falls but aggregate cell throughput
  stays near capacity.
- Backhaul degradation: PRB utilization stays normal, latency rise is
  decoupled from user count, aggregate throughput is hard-capped well below
  the cell's radio capacity regardless of load, and jitter is elevated.

## Remediation options, in order of typical deployment speed

1. **Load balancing** - steer eligible UEs to underutilized neighbor cells or
   secondary carriers via mobility parameter tuning or carrier aggregation
   policy.
2. **Carrier aggregation activation** - enable or expand CA for capable UEs to
   spread load across component carriers.
3. **Scheduler prioritization** - adjust QoS weighting so latency-sensitive
   traffic classes are protected first.
4. **Temporary capacity augmentation** - activate a standby carrier or
   spectrum refarm if available.
5. **Physical capacity expansion** - additional sector, small cell, or
   spectrum licensing - a planning-cycle action, not an incident response.

## Related documents

See "Congestion Triage Runbook" for a step-by-step diagnostic procedure and
"Load Balancing and Carrier Aggregation" for configuration-level detail on
remediation option 1 and 2.
