---
doc_id: capacity-planning-guidelines
title: Capacity Planning Guidelines
version: "1.0"
category: planning
owner: RAN Planning
---

> Synthetic reference documentation authored for this demonstration system.

# Capacity Planning Guidelines

## When an incident becomes a planning problem

Incident response (load balancing, CA activation, scheduler prioritization)
buys time but does not add capacity. An incident should be handed to
capacity planning when:

- Congestion recurs on the same cell across 3 or more consecutive busy-hour
  windows after incident mitigations have been applied.
- Neighbor cells consistently lack headroom for load balancing, indicating
  an area-wide capacity shortfall rather than a single-cell anomaly.
- Active user growth trend, extrapolated, crosses the cell's provisioned
  design capacity within the next planning cycle.

## Capacity expansion options, roughly in order of lead time

1. **Software/parameter-level**: scheduler and mobility tuning, CA policy
   expansion - days.
2. **Spectrum refarming**: reallocating existing spectrum to the affected
   band/cell - weeks to months, subject to coordination.
3. **Additional carrier / small cell deployment**: adding a new carrier or
   infill small cell in a hotspot area - months.
4. **New macro site**: full site acquisition and build - typically 6-18
   months.

## Data inputs for a capacity planning request

- 90-day PRB utilization trend for the affected cell and its immediate
  neighbors.
- Active user growth trend.
- Busy-hour throughput demand versus available capacity.
- Frequency and duration of congestion incidents in the period, with
  applied mitigations and their effectiveness.
- Any known upcoming demand events (venue openings, transit changes) in the
  cell's coverage area.

## Prioritization

Capacity requests are prioritized by subscriber impact (affected user-hours
of degraded service) and recurrence frequency, not solely by peak severity
of any single incident.
