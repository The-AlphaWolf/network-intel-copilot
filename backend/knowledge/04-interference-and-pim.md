---
doc_id: interference-and-pim
title: Uplink/Downlink Interference and PIM Troubleshooting
version: "1.4"
category: runbook
owner: RF Engineering
---

> Synthetic reference documentation authored for this demonstration system.

# Uplink/Downlink Interference and PIM Troubleshooting

## Interference signature

Interference manifests primarily as SINR and RSRQ degradation while RSRP
remains largely unchanged - the signal is arriving at normal strength but is
being corrupted by unwanted energy on the same or adjacent channel.

Typical progression:

1. SINR falls, often sharply (a drop of 10+ dB is common for a new
   interference source).
2. RSRQ falls correspondingly, since RSRQ folds in interference/noise.
3. Throughput falls as modulation and coding scheme selection backs off to
   compensate for the noisier channel.
4. Drop rate and retransmission rate rise as marginal-quality connections
   fail.

## Common interference sources

- **PIM (Passive Intermodulation)**: corroded, loose, or damaged RF
  connectors and components generate intermodulation products that fall
  in-band. PIM alarms and rising uplink noise floor are the signature.
- **External RF interference**: non-network transmitters (illegal repeaters,
  industrial equipment, radar) on or near the operating band.
- **Uncoordinated neighbor reuse**: aggressive frequency reuse or a
  misconfigured neighbor cell radiating into the same coverage area without
  adequate isolation.
- **Intra-system interference**: overlapping coverage from cells with
  insufficient azimuth/tilt separation.

## Diagnostic checklist

1. Confirm SINR/RSRQ degradation while RSRP stays stable - this is the
   discriminator versus a coverage problem.
2. Check for PIM or VSWR alarms on the affected cell and its antenna ports.
   A VSWR alarm strongly suggests a physical connector or feeder fault.
3. Check whether the degradation is uplink-dominant (affects cell-edge
   throughput and drop rate more than downlink) - typical of PIM and external
   jammers, since PIM primarily corrupts the more sensitive uplink receiver
   path.
4. Review recent site work - any connector, jumper, or antenna work
   preceding the onset is a strong PIM indicator.
5. Check neighbor cell configurations for recent parameter changes
   (frequency, power, azimuth) that could explain new co-channel
   interference.

## Remediation

- **Suspected PIM**: dispatch a field technician to inspect and re-torque RF
  connectors, replace damaged jumpers, and run a PIM sweep. This is a
  physical fix, not a parameter change.
- **External interference**: coordinate spectrum monitoring to locate and
  report/remove the offending source; in the interim, consider temporary
  frequency reassignment if the band plan allows.
- **Neighbor reuse conflict**: adjust azimuth, tilt, or transmit power on the
  conflicting cell, or increase frequency reuse distance.

## Related documents

See "5G NR Alarm Reference" for the full PIM/VSWR alarm catalogue and
"Coverage Optimization and Antenna Tilt" for the discriminating checklist
between interference and coverage-driven quality loss.
