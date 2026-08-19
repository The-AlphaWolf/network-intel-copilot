---
doc_id: escalation-matrix-sla
title: Incident Escalation Matrix and SLA
version: "1.0"
category: process
owner: Network Operations Center
---

> Synthetic reference documentation authored for this demonstration system.

# Incident Escalation Matrix and SLA

## Severity classification

- **P1 (Critical)**: complete cell/site outage, or multi-cell impact
  affecting a large subscriber base, or any critical KPI breach sustained
  beyond 15 minutes with no automated mitigation available.
- **P2 (High)**: single-cell critical KPI breach (e.g. drop rate > 1.5%,
  packet loss > 5%, PRB saturation > 95%) with identified but unapplied
  mitigation.
- **P3 (Medium)**: warning-level KPI breach or degraded-but-functional
  service, mitigation available but not time-critical.
- **P4 (Low)**: informational anomalies, trend-worthy but no immediate user
  impact.

## Response time SLA

| Severity | Acknowledge | Initial diagnosis | Mitigation applied |
|---|---|---|---|
| P1 | 5 min | 15 min | 30 min |
| P2 | 15 min | 30 min | 2 hours |
| P3 | 1 hour | 4 hours | next business day |
| P4 | next business day | - | scheduled maintenance |

## Escalation path

1. **NOC Tier 1**: initial triage using automated tooling and this
   knowledge base; applies documented, low-risk mitigations directly
   (mobility parameter nudge, CA activation).
2. **Tier 2 / Domain Engineering** (RF, Transport, Core): engaged when
   Tier 1 triage identifies a domain-specific fault requiring specialist
   action (field dispatch, provider ticket, parameter change beyond
   standard runbook bounds).
3. **RAN Planning**: engaged for recurring or structural issues (capacity
   exhaustion, coverage plan revision) that require a planning-cycle fix
   rather than an incident-response action.
4. **Vendor/Provider escalation**: engaged when the fault lies outside
   operator control (backhaul provider link, third-party interference
   source pending regulatory action).

## Ownership by root-cause category

- Congestion -> RAN Planning (structural) / NOC Tier 1 (immediate mitigation)
- Interference / PIM -> RF Engineering
- Backhaul degradation -> Transport Engineering
- Poor coverage -> RF Engineering
- Handover problems -> RAN Performance Engineering
