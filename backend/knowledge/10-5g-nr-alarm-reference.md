---
doc_id: 5g-nr-alarm-reference
title: 5G NR Alarm Reference
version: "1.5"
category: reference
owner: Network Operations Center
---

> Synthetic reference documentation authored for this demonstration system.
> Alarm codes are illustrative, not a real vendor's alarm catalogue.

# 5G NR Alarm Reference

## Capacity alarms

- **PRB_THRESHOLD_CROSSED** (warning): PRB utilization exceeded the
  configured congestion threshold (default 90%) for a sustained interval.
- **CAPACITY_LICENSE_LIMIT** (critical): active connected users approaching
  or at the cell's licensed capacity limit.
- **RRC_CONN_REJECT** (warning): RRC connection requests being rejected by
  admission control due to resource exhaustion.

## Interference / RF alarms

- **PIM_ALARM** (warning): passive intermodulation product detected above
  threshold on an antenna port.
- **UL_NOISE_RISE** (warning): uplink noise floor risen above baseline,
  consistent with interference or PIM.
- **SINR_DEGRADED** (critical): sustained SINR degradation across a
  measurement window, independent of RSRP.
- **VSWR_ALARM** (warning): voltage standing wave ratio out of tolerance on
  an antenna port, indicating a connector, cable, or antenna fault.

## Coverage alarms

- **RSRP_BELOW_THRESHOLD** (warning): RSRP below the configured coverage
  threshold at cell edge, based on UE measurement reports.
- **COVERAGE_HOLE_SUSPECTED** (critical): correlated drive-test or
  crowd-sourced data suggests a coverage hole rather than a transient dip.

## Transport / backhaul alarms

- **TRANSPORT_LINK_ERROR** (critical): CRC or frame errors detected on the
  backhaul transport interface.
- **S1_LATENCY_HIGH** (warning): S1-U / NG-U interface latency exceeded the
  configured SLA threshold.
- **BACKHAUL_JITTER** (warning): backhaul link jitter exceeded threshold,
  affecting time-sensitive traffic.

## Mobility / handover alarms

- **X2_HO_FAILURE** (warning): X2/Xn handover preparation failure between
  the reporting cell and a neighbor.
- **HO_PING_PONG** (warning): repeated back-and-forth handovers detected
  between a cell pair within a short time window.
- **NEIGHBOR_RELATION_MISSING** (critical): handover pattern consistent with
  a missing or misconfigured neighbor relation for a physically adjacent
  cell pair.

## General

- **HEALTH_CHECK** (info): periodic automated health check completed with
  no fault detected. Informational only, not an incident indicator.

## Severity handling

- **info**: logged for audit/trend purposes only, no action required.
- **warning**: investigate within the current shift; escalate if it
  persists beyond 3 consecutive measurement windows or co-occurs with a KPI
  breach.
- **critical**: investigate immediately; open an incident ticket if a KPI
  breach is confirmed.
