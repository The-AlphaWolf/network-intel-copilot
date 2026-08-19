---
doc_id: transport-backhaul-troubleshooting
title: Transport and Backhaul Troubleshooting Guide
version: "1.1"
category: runbook
owner: Transport Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# Transport and Backhaul Troubleshooting Guide

## Backhaul degradation signature

Backhaul (the link between a cell site and the core network, e.g.
microwave, fiber, or leased line) degradation is diagnosed by the pattern
of impact rather than any single metric:

1. Latency rises, often substantially (100+ ms), and is accompanied by high
   jitter/variance - unlike congestion-driven latency, which rises smoothly
   with load.
2. Packet loss rises, sometimes severely (5%+), independent of the number of
   active users.
3. Throughput is hard-capped at a value well below the cell's radio
   capacity, and stays capped regardless of load - the bottleneck is the
   transport link, not the radio scheduler.
4. PRB utilization stays normal - the radio side has no trouble scheduling,
   it simply cannot deliver data through the link fast enough.
5. Transport-layer alarms (CRC errors, link flap, S1-U/NG-U latency SLA
   breach) typically accompany the KPI degradation.

## Discriminating from congestion

The single clearest discriminator is the relationship between throughput and
active users. Under congestion, aggregate cell throughput tracks close to
capacity and rises with load. Under backhaul degradation, throughput is flat
and capped regardless of how many or few users are active, because the
ceiling is imposed by the transport link, not the radio resource pool.

## Diagnostic checklist

1. Check PRB utilization - if normal (< 70%) while latency/loss are
   elevated, backhaul is the leading hypothesis.
2. Check for transport link alarms (CRC errors, interface flap, jitter
   threshold breach) on the site's backhaul interface.
3. Check whether the throughput ceiling is stable across different load
   levels - a flat cap independent of active users confirms a transport
   bottleneck rather than radio congestion.
4. Check for recent changes: backhaul provider maintenance, microwave link
   fade (weather-correlated for microwave links), or fiber cuts reported in
   the area.

## Remediation

1. Engage the transport/backhaul provider or field team to inspect the
   physical link (fiber continuity, microwave alignment/fade margin,
   leased-line provider ticket).
2. If a redundant/backup path exists, fail over traffic while the primary
   link is repaired.
3. If the link is congested rather than faulty (aggregate backhaul demand
   across multiple co-sited cells exceeds provisioned capacity), engage
   transport capacity planning for an upgrade.
4. Apply QoS shaping at the site router to protect latency-sensitive traffic
   classes while the underlying link issue is resolved.

## Related documents

See "PRB Utilization and Capacity Management" for the congestion signature
this guide is designed to be distinguished from.
