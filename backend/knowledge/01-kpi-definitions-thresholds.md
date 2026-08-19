---
doc_id: kpi-definitions-thresholds
title: 5G NR KPI Definitions and Alert Thresholds
version: "1.2"
category: reference
owner: RAN Performance Engineering
---

> Synthetic reference documentation authored for this demonstration system.
> Not an operator or vendor specification.

# 5G NR KPI Definitions and Alert Thresholds

This document defines the core radio and transport KPIs tracked for 5G NR
cells and the thresholds used to classify a reading as normal, warning, or
critical.

## RSRP (Reference Signal Received Power)

RSRP measures the power level of the reference signal received by the UE,
expressed in dBm. It is the primary indicator of coverage.

- Good: > -90 dBm
- Fair: -90 to -105 dBm
- Poor: -105 to -115 dBm
- Critical / coverage hole: < -115 dBm

Sustained RSRP below -105 dBm across a cell's footprint indicates a coverage
problem: insufficient transmit power, antenna misalignment, excessive
downtilt, or physical obstruction.

## RSRQ (Reference Signal Received Quality)

RSRQ combines received signal strength with co-channel interference and
noise, expressed in dB. It is a better interference indicator than RSRP alone.

- Good: > -10 dB
- Fair: -10 to -15 dB
- Poor: < -15 dB

RSRQ dropping sharply while RSRP stays stable is a strong interference
signature, not a coverage signature.

## SINR (Signal to Interference plus Noise Ratio)

SINR, in dB, is the cleanest predictor of achievable throughput and link
quality.

- Excellent: > 20 dB
- Good: 13-20 dB
- Fair: 0-13 dB
- Poor: < 0 dB

A SINR collapse with stable RSRP almost always points to rising interference
(PIM, external jammer, uncoordinated neighbor reuse) rather than a coverage
issue.

## Latency

End-to-end user-plane latency, measured in milliseconds from UE to the core
network edge.

- Normal: < 20 ms
- Elevated: 20-50 ms
- Degraded: 50-100 ms
- Critical: > 100 ms

Latency spikes with high variance (jitter) and no corresponding radio KPI
degradation typically indicate a transport/backhaul problem rather than a
radio problem.

## Packet Loss

Percentage of user-plane packets dropped end to end.

- Normal: < 0.5%
- Elevated: 0.5-2%
- Degraded: 2-5%
- Critical: > 5%

## PRB Utilization

Percentage of Physical Resource Blocks scheduled over a measurement interval.
This is the primary capacity/congestion indicator.

- Normal: < 70%
- High: 70-85%
- Congested: 85-95%
- Saturated: > 95%

Sustained PRB utilization above 85% during busy hour, correlated with rising
latency and packet loss but stable RSRP/SINR, is the canonical congestion
signature.

## Handover Success Rate

Percentage of handover attempts that complete successfully.

- Normal: > 98%
- Degraded: 95-98%
- Critical: < 95%

## Drop Rate (Call/Session Drop Rate)

Percentage of active sessions terminated abnormally.

- Normal: < 0.5%
- Elevated: 0.5-1.5%
- Critical: > 1.5%

## Throughput

Average per-user or cell-aggregate data rate in Mbps. Interpreted relative to
band, bandwidth, and active user count rather than an absolute threshold.

## Active Users

Concurrent RRC-connected users on a cell. Used alongside PRB utilization to
distinguish genuine capacity exhaustion from a scheduler or configuration
fault.
