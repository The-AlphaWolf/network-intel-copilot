"""API response schemas for the investigation endpoint."""
from __future__ import annotations

from pydantic import BaseModel


class InvestigateRequest(BaseModel):
    query: str
    cell_id: str | None = None
    time_window_hours: int | None = None


class KpiAnomalyOut(BaseModel):
    kpi: str
    current: float | None
    baseline_mean: float | None = None
    z_score: float
    deviation_pct: float
    severity: str
    breached_threshold: bool = False


class EvidenceOut(BaseModel):
    source: str
    title: str
    detail: str
    severity: str
    timestamp: str | None = None


class CitationOut(BaseModel):
    doc_id: str
    title: str
    section: str
    chunk_id: str
    score: float
    snippet: str


class RootCauseOut(BaseModel):
    rank: int
    cause: str
    category: str
    confidence: float
    explanation: str
    supporting_evidence: list[str] = []
    citations: list[str] = []


class RecommendationOut(BaseModel):
    priority: str
    action: str
    category: str
    expected_impact: str
    risk: str
    owner_team: str
    estimated_time: str
    citations: list[str] = []


class AgentExecutionOut(BaseModel):
    agent: str
    status: str
    message: str
    tools_used: list[str]
    duration_ms: float
    timestamp: str


class InvestigationMetrics(BaseModel):
    llm_calls: int
    tools_called: int
    retrieval_hits: int
    duration_ms: float


class InvestigationResult(BaseModel):
    investigation_id: str
    query: str
    cell_id: str | None
    status: str
    summary: str
    kpi_anomalies: list[KpiAnomalyOut]
    evidence: list[EvidenceOut]
    root_causes: list[RootCauseOut]
    recommendations: list[RecommendationOut]
    citations: list[CitationOut]
    agent_execution: list[AgentExecutionOut]
    errors: list[str]
    metrics: InvestigationMetrics
