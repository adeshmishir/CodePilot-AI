import { createContext } from "react"

import type { FormattedError } from "@/lib/error-format"
import type { RepositoryListItem } from "@/types/api"

export type HealthState = "checking" | "connected" | "degraded" | "offline"

export interface WorkspaceContextValue {
  repositories: RepositoryListItem[]
  selected: RepositoryListItem | null
  selectedId: number | null
  loadingRepositories: boolean
  listError: FormattedError | null
  cloning: boolean
  cloneError: FormattedError | null
  health: HealthState
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  selectRepository: (repository: RepositoryListItem) => void
  cloneRepository: (url: string) => Promise<void>
  refreshRepositories: () => void
  clearCloneError: () => void
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(
  null,
)
