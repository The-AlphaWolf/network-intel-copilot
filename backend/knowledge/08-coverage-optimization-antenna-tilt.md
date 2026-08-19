---
doc_id: coverage-optimization-antenna-tilt
title: Coverage Optimization and Antenna Tilt
version: "1.2"
category: optimization
owner: RF Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# Coverage Optimization and Antenna Tilt

## Coverage problem signature

Coverage (poor RSRP) problems are distinguished from interference problems
by the behavior of RSRP itself:

1. RSRP degrades, often substantially (below -105 dBm at cell edge, below
   -115 dBm in severe cases).
2. RSRQ and SINR typically degrade in step with RSRP, since a weak signal is
   more vulnerable to a given noise floor - unlike pure interference, where
   RSRP stays stable while RSRQ/SINR fall independently.
3. Handover success rate falls at the affected cell edge, since UEs there
   are in marginal signal conditions when a handover decision must be made.
4. Drop rate rises for UEs at the affected edge.
5. VSWR or antenna-related alarms may be present if the cause is physical
   (misaligned antenna, damaged element, blocked line of sight).

## Common causes

- **Excessive electrical or mechanical downtilt**: shrinks effective
  coverage radius, creating a hole at the intended edge of coverage.
- **Insufficient uptilt / overshoot on a neighboring cell**: can also create
  perceived edge problems by pulling UEs onto a weaker serving cell.
- **Physical obstruction**: new construction, foliage growth, or terrain
  changes blocking line of sight.
- **Antenna or feeder fault**: damaged element, misaligned azimuth, or
  connector fault reducing effective radiated power.
- **Insufficient transmit power** for the cell's designed coverage radius.

## Diagnostic checklist

1. Confirm RSRP, RSRQ, and SINR are degrading together - this is the
   discriminator versus a pure interference case (where RSRP stays stable).
2. Check for VSWR or antenna alarms indicating a physical fault.
3. Review recent site or nearby construction that could introduce a new
   obstruction.
4. Compare against the cell's engineered coverage plan (tilt, azimuth,
   power) for unintended drift or a configuration error introduced during
   recent maintenance.
5. Correlate with drive-test or crowd-sourced coverage data where available
   to confirm a physical coverage hole versus a localized measurement
   artifact.

## Remediation

1. If a physical/antenna fault is confirmed, dispatch a field team to
   repair or realign.
2. If downtilt is excessive, reduce electrical tilt incrementally and
   re-measure - avoid large single-step changes, which can create new holes
   elsewhere.
3. If transmit power is below the engineered design value, restore it
   (subject to regulatory and interference-coordination limits).
4. If overshoot from a neighbor is pulling UEs off this cell, address the
   neighbor's tilt/power rather than only compensating on the affected
   cell.

## Related documents

See "5G NR Alarm Reference" for VSWR and antenna fault alarm codes, and
"Interference and PIM Troubleshooting" for the discriminating checklist
against interference-driven quality loss.
