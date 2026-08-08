export interface HealthStatus {
  status: string
}

export interface CloneRepositoryRequest {
  url: string
}

export interface CloneRepositoryResponse {
  success: boolean
  id: number
  repository: string
  owner: string
  local_path: string
  message: string
}

export interface RepositoryListItem {
  id: number
  owner: string
  name: string
  clone_url: string
  local_path: string
}

export interface RepositoryListResponse {
  repositories: RepositoryListItem[]
}

export interface SearchRequest {
  query: string
  limit?: number
}

export interface SearchResult {
  score: number
  repository_id: number
  file_path: string
  symbol_name: string
  symbol_type: string
  start_line: number
  end_line: number
  content: string
}

export interface SearchResponse {
  results: SearchResult[]
}

export interface ChatRequest {
  query: string
  limit?: number
}

export interface ChatSource {
  file_path: string
  symbol_name: string
  start_line: number
  end_line: number
  score: number
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
}

export interface AgentRequest {
  query: string
  max_steps?: number
}

export interface AgentToolCall {
  tool: string
  arguments: Record<string, unknown>
  observation: string
}

export interface AgentResponse {
  answer: string
  plan: string[]
  tool_calls: AgentToolCall[]
  observations: string[]
}

export type Severity = "low" | "medium" | "high" | "critical"

export interface BugDetectionRequest {
  query: string
  limit?: number
}

export interface BugFinding {
  title: string
  severity: Severity
  description: string
  file_path: string
  start_line: number
  end_line: number
  evidence: string
  recommendation: string
}

export interface BugDetectionSource {
  file_path: string
  symbol_name: string
  start_line: number
  end_line: number
  score: number
}

export interface BugDetectionResponse {
  findings: BugFinding[]
  sources: BugDetectionSource[]
}

export interface ApiError {
  detail?: string
  message?: string
}
