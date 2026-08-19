---
doc_id: handover-parameter-optimization
title: Handover Parameter Optimization
version: "1.3"
category: optimization
owner: RAN Performance Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# Handover Parameter Optimization

## Key handover parameters

- **A3 offset**: the margin (in dB) by which a neighbor cell's signal must
  exceed the serving cell's before a measurement report triggers. Too low
  causes premature/unnecessary handovers; too high causes late handovers and
  dropped calls at the cell edge.
- **Time-to-Trigger (TTT)**: how long the A3 condition must hold before the
  UE reports it. Too short causes ping-pong handovers in fluctuating RF
  conditions; too long causes late handovers.
- **Hysteresis**: an additional margin applied to prevent oscillation around
  the trigger threshold.

## Handover failure signature

A cell with degraded handover success rate but otherwise normal KPIs
(RSRP/RSRQ/SINR/PRB all within range) points to a parameter or configuration
issue rather than a radio-condition issue:

1. Handover success rate falls below 95%.
2. X2/Xn handover preparation failures appear in logs, often concentrated
   between one specific cell pair.
3. "Ping-pong" events (handover back to the previous cell within a short
   window) indicate TTT set too short or hysteresis too low for that
   cell pair.
4. A missing or one-directional neighbor relation between physically
   adjacent cells causes handovers to fail outright for UEs moving in that
   direction - the target cell is never offered as a candidate.

## Diagnostic checklist

1. Confirm the neighbor relation table includes both directions for every
   physically adjacent cell pair. A missing relation is the single most
   common cause of a hard handover-success floor for one direction of
   travel.
2. Check for ping-pong clustering on a specific cell pair - suggests TTT/
   hysteresis retuning is needed for that pair specifically, not a network-
   wide parameter change.
3. Check whether failures correlate with cell-edge RSRP (below -100 dBm) -
   if so, the A3 offset may be too conservative, triggering too late.
4. Review recent neighbor list or ANR (Automatic Neighbor Relation) changes
   that might have removed or deprioritized a relation.

## Remediation

- **Missing neighbor relation**: add the bidirectional relation; if ANR is
  enabled, verify it has not been suppressed for that pair.
- **Ping-pong**: increase TTT and/or hysteresis for the affected cell pair.
- **Late handover / cell-edge drops**: decrease A3 offset or increase
  handover trigger sensitivity for that pair.
- Always tune at the cell-pair level first; network-wide parameter changes
  risk introducing regressions elsewhere.

## Related documents

See "5G NR Alarm Reference" for X2/Xn handover failure alarm codes.
