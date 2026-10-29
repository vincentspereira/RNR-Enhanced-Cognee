// API Response Types
export interface MemoryResponse {
  memory_id: string;
  version: number;
  project_id: string;
  state: string;
  content: string;
  data_type: string;
  memory_type: string | null;
  memory_concept: string | null;
  summary: string | null;
  created_at: string;
  updated_at: string;
  char_count: number | null;
  estimated_tokens: number | null;
  agent_id?: string | null;
  tags?: string[] | null;
  before_state?: string | null;
  after_state?: string | null;
  files?: string[] | null;
  facts?: string[] | null;
  metadata?: Record<string, unknown>;
  related_memories?: MemoryResponse[];
  similarity?: number;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  agent_id: string;
  start_time: string;
  end_time: string | null;
  summary: string | null;
  memory_count: number;
}

export interface SystemStatsResponse {
  total_memories: number;
  total_sessions: number;
  active_sessions: number;
  avg_tokens_per_memory: number;
  token_efficiency_percent: number;
  database_status: Record<string, boolean>;
  server_uptime: string;
}

export interface SearchResponse {
  query: string;
  result_count: number;
  results: MemoryResponse[];
  token_savings: Record<string, unknown>;
}

export interface TimelineResponse {
  memory_id: string;
  before: MemoryResponse[];
  current: MemoryResponse | null;
  after: MemoryResponse[];
}

export interface StructuredStatsResponse {
  total_observations: number;
  bugfix_count: number;
  feature_count: number;
  decision_count: number;
  refactor_count: number;
  discovery_count: number;
  general_count: number;
}

// Request Types
export interface MemoryFilters {
  limit?: number;
  offset?: number;
  agent_id?: string;
  memory_type?: string;
  memory_concept?: string;
}

export interface SearchFilters {
  query: string;
  agent_id?: string;
  limit?: number;
}

export interface SessionFilters {
  limit?: number;
  agent_id?: string;
  active_only?: boolean;
}

export interface TimelineFilters {
  before?: number;
  after?: number;
}

// Local Types (extended from API types)
export interface Memory extends MemoryResponse {
  id: string; // Alias for memory_id
}

export interface Session extends SessionResponse {
  id: string; // Alias for session_id
}
