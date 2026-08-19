---
doc_id: packet-loss-triage
title: Packet Loss Triage Guide
version: "1.0"
category: runbook
owner: Network Operations Center
---

> Synthetic reference documentation authored for this demonstration system.

# Packet Loss Triage Guide

Packet loss can originate at several layers. This guide maps the
accompanying KPI pattern to the most likely origin so effort is not spent
investigating the wrong layer.

## Radio-layer packet loss (congestion)

- Accompanied by high PRB utilization (> 85%) and elevated active users.
- RSRP/RSRQ/SINR normal.
- Loss driven by RLC/PDCP buffer overflow under sustained scheduling
  pressure.
- Typical magnitude: 1-3%.
- See: Congestion Triage Runbook.

## Radio-layer packet loss (poor link quality)

- Accompanied by low SINR and/or low RSRP.
- Loss driven by uncorrectable transmission errors and retransmission
  exhaustion on a poor-quality link.
- See: Interference and PIM Troubleshooting, or Coverage Optimization and
  Antenna Tilt, depending on whether RSRP is also degraded.

## Transport-layer packet loss (backhaul)

- PRB utilization and radio KPIs normal.
- Loss decoupled from active user count.
- Often paired with high latency and high jitter, and transport CRC/link
  alarms.
- Typical magnitude: can exceed 5% in severe cases.
- See: Transport and Backhaul Troubleshooting Guide.

## Core-network packet loss

- Rare in this dataset's scope, but worth ruling out: if loss is observed
  simultaneously across many unrelated cells sharing a common core network
  element, suspect a core-side fault rather than any individual cell or its
  backhaul.

## Triage order

1. Check PRB utilization first - it is the fastest discriminator between
   radio-congestion loss and everything else.
2. If PRB is normal, check SINR/RSRP - if either is degraded, it is a
   link-quality problem (interference or coverage).
3. If PRB, SINR, and RSRP are all normal but loss is elevated, check latency
   and jitter - elevated values point to backhaul.
4. If loss appears simultaneously across many cells on shared
   infrastructure, escalate to core network operations rather than
   continuing single-cell RAN triage.
