import type {
  AgentRequest,
  AgentResponse,
  BugDetectionRequest,
  BugDetectionResponse,
  ChatRequest,
  ChatResponse,
  CloneRepositoryRequest,
  CloneRepositoryResponse,
  HealthStatus,
  IssueListResponse,
  IssueTriageResponse,
  PullRequestListResponse,
  PullRequestReview,
  RepositoryListResponse,
  SearchRequest,
  SearchResponse,
} from "@/types/api"

const DEFAULT_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ApiClientError extends Error {
  readonly status: number

  constructor(
    message: string,
    status: number,
  ) {
    super(message)
    this.name = "ApiClientError"
    this.status = status
  }
}

export class ApiClient {
  private readonly baseUrl: string

  constructor(baseUrl: string = DEFAULT_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private get base() {
    return this.baseUrl.replace(/\/+$/, "")
  }

  private async request<T>(
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const response = await fetch(`${this.base}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    })

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`
      try {
        const body = (await response.json()) as {
          detail?: unknown
          message?: string
        }
        if (typeof body.detail === "string") {
          message = body.detail
        } else if (body.message) {
          message = body.message
        }
      } catch {
        // fall back to the status-based message
      }
      throw new ApiClientError(message, response.status)
    }

    return response.json() as Promise<T>
  }

  async health(): Promise<HealthStatus> {
    return this.request<HealthStatus>("/health")
  }

  async listRepositories(): Promise<RepositoryListResponse> {
    return this.request<RepositoryListResponse>("/repositories")
  }

  async cloneRepository(
    request: CloneRepositoryRequest,
  ): Promise<CloneRepositoryResponse> {
    return this.request<CloneRepositoryResponse>("/repositories/clone", {
      method: "POST",
      body: JSON.stringify(request),
    })
  }

  async search(
    repositoryId: number,
    request: SearchRequest,
  ): Promise<SearchResponse> {
    return this.request<SearchResponse>(
      `/api/repositories/${repositoryId}/search`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    )
  }

  async chat(
    repositoryId: number,
    request: ChatRequest,
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(
      `/api/repositories/${repositoryId}/chat`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    )
  }

  async runAgent(
    repositoryId: number,
    request: AgentRequest,
  ): Promise<AgentResponse> {
    return this.request<AgentResponse>(
      `/api/repositories/${repositoryId}/agent`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    )
  }

  async detectBugs(
    repositoryId: number,
    request: BugDetectionRequest,
  ): Promise<BugDetectionResponse> {
    return this.request<BugDetectionResponse>(
      `/api/repositories/${repositoryId}/bugs`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    )
  }

  async listPullRequests(
    repositoryId: number,
  ): Promise<PullRequestListResponse> {
    return this.request<PullRequestListResponse>(
      `/api/repositories/${repositoryId}/github/prs`,
    )
  }

  async reviewPullRequest(
    repositoryId: number,
    pullNumber: number,
  ): Promise<PullRequestReview> {
    return this.request<PullRequestReview>(
      `/api/repositories/${repositoryId}/github/prs/${pullNumber}/review`,
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    )
  }

  async listIssues(
    repositoryId: number,
  ): Promise<IssueListResponse> {
    return this.request<IssueListResponse>(
      `/api/repositories/${repositoryId}/github/issues`,
    )
  }

  async triageIssues(
    repositoryId: number,
  ): Promise<IssueTriageResponse> {
    return this.request<IssueTriageResponse>(
      `/api/repositories/${repositoryId}/github/issues/triage`,
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    )
  }
}

export const apiClient = new ApiClient()
