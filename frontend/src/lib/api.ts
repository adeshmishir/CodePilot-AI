import type {
  AgentRequest,
  AgentResponse,
  BugDetectionRequest,
  BugDetectionResponse,
  ChatRequest,
  ChatResponse,
  ChatSource,
  CloneJobStatus,
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

const DEV_BASE_URL = "http://localhost:8000"
const PRODUCTION_BASE_URL = "https://codepilot-ai-yjwz.onrender.com"

const envBaseUrl = import.meta.env.VITE_API_URL?.trim()

function resolveBaseUrl(): string {
  if (envBaseUrl) return envBaseUrl

  if (import.meta.env.PROD) {
    console.warn(
      `[api] VITE_API_URL is not set. Falling back to the production backend: ${PRODUCTION_BASE_URL}`,
    )
    return PRODUCTION_BASE_URL
  }

  console.warn(
    `[api] VITE_API_URL is not set. Falling back to the local backend: ${DEV_BASE_URL}`,
  )
  return DEV_BASE_URL
}

const DEFAULT_BASE_URL = resolveBaseUrl()

export class ApiClientError extends Error {
  readonly status: number
  readonly detail: string | undefined

  constructor(
    message: string,
    status: number,
    detail?: string,
  ) {
    super(message)
    this.name = "ApiClientError"
    this.status = status
    this.detail = detail
  }
}

export class TimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`)
    this.name = "TimeoutError"
  }
}

export interface StreamChatCallbacks {
  onDelta?: (text: string) => void
  onSources?: (sources: ChatSource[]) => void
  onDone?: () => void
}

function parseSseEvent(raw: string): Record<string, unknown> | null {
  const dataLines: string[] = []
  for (const line of raw.split("\n")) {
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart())
    }
  }
  if (dataLines.length === 0) return null
  try {
    return JSON.parse(dataLines.join("\n")) as Record<string, unknown>
  } catch {
    return null
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
    options?: { timeoutMs?: number },
  ): Promise<T> {
    const timeoutMs = options?.timeoutMs ?? 60_000
    const maxAttempts = 2
    const retryDelayMs = 1_000

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), timeoutMs)

      let response: Response

      try {
        response = await fetch(`${this.base}${path}`, {
          ...init,
          signal: controller.signal,
          headers: {
            "Content-Type": "application/json",
            ...init?.headers,
          },
        })
      } catch (caught) {
        if (controller.signal.aborted) {
          throw new TimeoutError(timeoutMs)
        }
        throw caught
      } finally {
        clearTimeout(timer)
      }

      if (response.ok) {
        return response.json() as Promise<T>
      }

      let message = `Request failed with status ${response.status}`
      let detail: string | undefined
      try {
        const body = (await response.json()) as {
          detail?: unknown
          message?: string
        }
        if (typeof body.message === "string") {
          message = body.message
        } else if (typeof body.detail === "string") {
          message = body.detail
        }
        if (typeof body.detail === "string") {
          detail = body.detail
        }
      } catch {
        // fall back to the status-based message
      }

      if (
        attempt < maxAttempts &&
        (response.status === 502 || response.status === 503)
      ) {
        await new Promise((resolve) => setTimeout(resolve, retryDelayMs))
        continue
      }

      throw new ApiClientError(message, response.status, detail)
    }

    throw new ApiClientError(`Request failed with status ${502}`, 502)
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
    return this.request<CloneRepositoryResponse>(
      "/repositories/clone",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      { timeoutMs: 300_000 },
    )
  }

  async getCloneStatus(jobId: string): Promise<CloneJobStatus> {
    return this.request<CloneJobStatus>(
      `/repositories/clone/status/${jobId}`,
      { method: "GET" },
    )
  }

  async reindexRepository(
    repositoryId: number,
  ): Promise<CloneRepositoryResponse> {
    return this.request<CloneRepositoryResponse>(
      `/repositories/${repositoryId}/reindex`,
      {
        method: "POST",
      },
      { timeoutMs: 300_000 },
    )
  }

  async deleteRepository(
    repositoryId: number,
  ): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(
      `/repositories/${repositoryId}`,
      {
        method: "DELETE",
      },
    )
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

  async streamChat(
    repositoryId: number,
    request: ChatRequest,
    callbacks: StreamChatCallbacks = {},
    options?: { timeoutMs?: number },
  ): Promise<ChatResponse> {
    const timeoutMs = options?.timeoutMs ?? 300_000
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)

    try {
      const response = await fetch(
        `${this.base}/api/repositories/${repositoryId}/chat/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
          signal: controller.signal,
        },
      )

      if (!response.ok || !response.body) {
        throw await this.readErrorBody(response)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let answer = ""
      let sources: ChatSource[] = []

      for (;;) {
        let chunk: ReadableStreamReadResult<Uint8Array>
        try {
          chunk = await reader.read()
        } catch (caught) {
          if (controller.signal.aborted) throw new TimeoutError(timeoutMs)
          throw caught
        }
        if (chunk.done) break
        buffer += decoder.decode(chunk.value, { stream: true })
        const events = buffer.split("\n\n")
        buffer = events.pop() ?? ""
        for (const raw of events) {
          const payload = parseSseEvent(raw)
          if (!payload) continue
          if (payload.type === "sources" && Array.isArray(payload.sources)) {
            sources = payload.sources as ChatSource[]
            callbacks.onSources?.(sources)
          } else if (
            payload.type === "delta" &&
            typeof payload.text === "string"
          ) {
            answer += payload.text
            callbacks.onDelta?.(payload.text)
          } else if (payload.type === "error") {
            throw new ApiClientError(
              typeof payload.detail === "string"
                ? payload.detail
                : "Unable to generate an answer.",
              500,
            )
          }
        }
      }

      callbacks.onDone?.()
      return { answer, sources }
    } finally {
      clearTimeout(timer)
    }
  }

  private async readErrorBody(response: Response): Promise<ApiClientError> {
    let message = `Request failed with status ${response.status}`
    let detail: string | undefined
    try {
      const body = (await response.json()) as {
        detail?: unknown
        message?: string
      }
      if (typeof body.message === "string") {
        message = body.message
      } else if (typeof body.detail === "string") {
        message = body.detail
      }
      if (typeof body.detail === "string") {
        detail = body.detail
      }
    } catch {
      // fall back to the status-based message
    }
    return new ApiClientError(message, response.status, detail)
  }

  async cancelCloneJob(
    jobId: string,
  ): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(
      `/repositories/clone/cancel/${jobId}`,
      { method: "POST" },
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
