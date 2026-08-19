const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ---- health ----
export const getSystemHealth = () => req<SystemHealth>("/health/system");

// ---- cells ----
export const listCells = () => req<Cell[]>("/cells");
export const getCell = (id: string) => req<Cell>(`/cells/${id}`);
export const getCellKpis = (id: string, hours = 24) => req<KpiSeriesResponse>(`/cells/${id}/kpis?hours=${hours}`);
export const getCellAnomalies = (id: string, hours = 6) => req<Anomaly[]>(`/cells/${id}/anomalies?hours=${hours}`);
export const getCellNeighbors = (id: string) => req<NeighborRelation[]>(`/cells/${id}/neighbors`);
export const getTopology = () => req<Topology>("/topology");
export const getOverview = () => req<Overview>("/overview");

// ---- knowledge ----
export const listDocuments = () => req<KbDocument[]>("/knowledge/documents");
export const searchKnowledge = (query: string, top_k = 5) =>
  req<KbSearchResult[]>("/knowledge/search", { method: "POST", body: JSON.stringify({ query, top_k }) });

// ---- agents ----
export const getAgents = () => req<AgentsResponse>("/agents");

// ---- evaluation ----
export const getEvaluation = () => req<EvaluationResponse>("/evaluation/latest");

// ---- investigations ----
export const investigate = (query: string, cell_id?: string, time_window_hours?: number) =>
  req<InvestigationResult>("/investigate", { method: "POST", body: JSON.stringify({ query, cell_id, time_window_hours }) });
export const getInvestigation = (id: string) => req<InvestigationResult>(`/investigate/${id}`);
export const listInvestigations = (limit = 20) => req<InvestigationResult[]>(`/investigations?limit=${limit}`);

// ================= Types =================

export interface SystemHealth {
  status: string;
  components: { name: string; status: string; detail: string }[];
  python_version: string;
  app_env: string;
}

export interface Cell {
  cell_id: string;
  site_id: string;
  site_name: string;
  band: string;
  technology: string;
  lat: number;
  lon: number;
  azimuth_deg: number;
  scenario: string;
  neighbor_ids: string[];
  admin_state: string;
  oper_state: string;
  active_alarms: string[];
  health_score: number;
}

export interface KpiSeriesResponse {
  cell_id: string;
  hours: number;
  series: Record<string, { timestamp: string; value: number }[]>;
  summary: Record<string, { current: number; mean: number; min: number; max: number }>;
}

export interface Anomaly {
  cell_id: string;
  kpi: string;
  hours: number;
  current: number | null;
  baseline_mean?: number;
  baseline_std?: number;
  z_score: number;
  mean_abs_z_score?: number;
  deviation_pct: number;
  severity: "normal" | "warning" | "critical";
  breached_threshold: boolean;
}

export interface NeighborRelation {
  cell_id: string;
  neighbor_id: string;
  distance_km: number;
  relation_status: string;
  neighbor_health_score: number;
  neighbor_scenario: string;
}

export interface Topology {
  sites: Record<string, { name: string; lat: number; lon: number }>;
  cells: Cell[];
  neighbor_relations: { cell_id: string; neighbor_id: string; distance_km: number; relation_status: string }[];
}

export interface Overview {
  active_incidents: number;
  cells_monitored: number;
  anomalies_24h: number;
}

export interface KbDocument {
  doc_id: string;
  title: string;
  category: string;
  version: string;
  owner: string;
  chunk_count: number;
}

export interface KbSearchResult {
  chunk_id: string;
  doc_id: string;
  title: string;
  section: string;
  category: string;
  text: string;
  score: number;
}

export interface AgentArchNode {
  id: string;
  name: string;
  role: string;
  tools: string[];
  depends_on: string[];
}

export interface AgentsResponse {
  architecture: AgentArchNode[];
  last_run_status: Record<string, AgentEvent>;
}

export interface EvaluationResponse {
  status: string;
  message?: string;
  [key: string]: unknown;
}

export interface AgentEvent {
  agent: string;
  status: string;
  message: string;
  tools_used: string[];
  duration_ms: number;
  timestamp: string;
}

export interface KpiAnomalyOut {
  kpi: string;
  current: number | null;
  baseline_mean?: number;
  z_score: number;
  deviation_pct: number;
  severity: string;
  breached_threshold: boolean;
}

export interface EvidenceOut {
  source: string;
  title: string;
  detail: string;
  severity: string;
  timestamp: string | null;
}

export interface CitationOut {
  doc_id: string;
  title: string;
  section: string;
  chunk_id: string;
  score: number;
  snippet: string;
}

export interface RootCauseOut {
  rank: number;
  cause: string;
  category: string;
  confidence: number;
  explanation: string;
  supporting_evidence: string[];
  citations: string[];
}

export interface RecommendationOut {
  priority: string;
  action: string;
  category: string;
  expected_impact: string;
  risk: string;
  owner_team: string;
  estimated_time: string;
  citations: string[];
}

export interface InvestigationResult {
  investigation_id: string;
  query: string;
  cell_id: string | null;
  status: string;
  summary: string;
  kpi_anomalies: KpiAnomalyOut[];
  evidence: EvidenceOut[];
  root_causes: RootCauseOut[];
  recommendations: RecommendationOut[];
  citations: CitationOut[];
  agent_execution: AgentEvent[];
  errors: string[];
  metrics: { llm_calls: number; tools_called: number; retrieval_hits: number; duration_ms: number };
}
