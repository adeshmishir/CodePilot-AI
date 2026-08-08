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
  mode?: "single" | "multi"
}

export interface AgentToolCall {
  tool: string
  arguments: Record<string, unknown>
  observation: string
}

export interface AgentContribution {
  name: string
  summary: string
  detail: string
}

export interface AgentResponse {
  answer: string
  plan: string[]
  tool_calls: AgentToolCall[]
  observations: string[]
  agents: AgentContribution[]
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

export interface GitHubPullRequest {
  number: number
  title: string
  author: string
  state: string
  created_at: string | null
  updated_at: string | null
  additions: number
  deletions: number
  changed_files: number
  head_branch: string | null
  base_branch: string | null
  url: string | null
}

export interface PullRequestListResponse {
  pull_requests: GitHubPullRequest[]
  needs_github_token: boolean
}

export interface ReviewComment {
  file_path: string
  line: number | null
  severity: string
  category: string
  message: string
}

export interface PullRequestReview {
  pull_request_number: number
  title: string
  summary: string
  comments: ReviewComment[]
}

export interface GitHubIssue {
  number: number
  title: string
  author: string
  state: string
  labels: string[]
  created_at: string | null
  updated_at: string | null
  url: string | null
}

export interface IssueListResponse {
  issues: GitHubIssue[]
  needs_github_token: boolean
}

export interface IssueTriageEntry {
  issue_number: number
  title: string
  state: string
  author: string
  category: string
  severity: string
  suggested_labels: string[]
  summary: string
  labels: string[]
  created_at: string | null
  url: string | null
}

export interface IssueTriageResponse {
  issues: IssueTriageEntry[]
  needs_github_token: boolean
}

export interface ApiError {
  detail?: string
  message?: string
}
