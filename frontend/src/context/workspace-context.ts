import { createContext } from "react"

import type { FormattedError } from "@/lib/error-format"
import type { RepositoryListItem } from "@/types/api"

export type HealthState = "checking" | "connected" | "degraded" | "unavailable"

export interface CloneProgress {
  jobId: string
  phase: string
  percent: number
  filesDone: number
  filesTotal: number
}

export interface WorkspaceContextValue {
  repositories: RepositoryListItem[]
  selected: RepositoryListItem | null
  selectedId: number | null
  loadingRepositories: boolean
  listError: FormattedError | null
  cloning: boolean
  cloneError: FormattedError | null
  cloneProgress: CloneProgress | null
  deletingId: number | null
  deleteError: FormattedError | null
  reindexingId: number | null
  repoActionError: FormattedError | null
  health: HealthState
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  selectRepository: (repository: RepositoryListItem) => void
  cloneRepository: (url: string) => Promise<void>
  deleteRepository: (repository: RepositoryListItem) => Promise<void>
  reindexRepository: (repository: RepositoryListItem) => Promise<void>
  refreshRepositories: () => void
  clearCloneError: () => void
  clearRepoActionError: () => void
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(
  null,
)
