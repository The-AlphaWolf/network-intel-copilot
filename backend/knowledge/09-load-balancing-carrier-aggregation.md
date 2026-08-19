---
doc_id: load-balancing-carrier-aggregation
title: Load Balancing and Carrier Aggregation Policy
version: "1.0"
category: optimization
owner: RAN Performance Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# Load Balancing and Carrier Aggregation Policy

## Mobility-based load balancing

When a cell is congested and a neighbor has PRB headroom, mobility
parameters can steer new and existing UEs toward the underutilized neighbor:

- **Cell reselection offset (idle mode)**: bias idle UEs toward the target
  neighbor by adjusting the reselection priority/offset.
- **Handover trigger bias (connected mode)**: temporarily lower the A3
  offset toward the underutilized neighbor so in-progress calls migrate
  sooner at the overlap boundary.
- Both should be applied conservatively and reverted once the source cell's
  PRB utilization normalizes, to avoid simply shifting congestion onto the
  target cell.

Load balancing is only viable when a neighbor has genuine headroom (PRB
utilization below ~60%) and adequate coverage overlap with the congested
cell.

## Carrier aggregation (CA) policy

For CA-capable UEs, adding a secondary component carrier increases available
scheduling resources without requiring mobility:

- Enable CA activation for eligible UEs on cells approaching 85% PRB
  utilization on the primary carrier.
- Prioritize CA activation for UEs with sustained high-throughput demand,
  since they benefit most and free up primary-carrier PRBs fastest.
- Monitor secondary carrier PRB utilization after activation to avoid simply
  relocating the congestion.

## Choosing between load balancing and CA

- Prefer CA when the congested cell's own secondary carrier has headroom -
  no mobility risk, no coverage-overlap dependency.
- Prefer load balancing when CA is unavailable (non-CA-capable UEs, no
  secondary carrier deployed) and a neighbor has confirmed headroom.
- Use both together for severe congestion (PRB > 95%): CA for capable UEs,
  load balancing for the remainder.

## Verification

After applying either measure, confirm within 1-2 measurement windows that
PRB utilization on the source cell has dropped and that the target
cell/carrier has not itself crossed the 85% threshold.
