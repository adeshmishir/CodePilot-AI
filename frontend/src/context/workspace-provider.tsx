"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import type { ReactNode } from "react"

import {
  WorkspaceContext,
  type HealthState,
  type WorkspaceContextValue,
} from "@/context/workspace-context"
import { apiClient, ApiClientError } from "@/lib/api"
import { formatApiError } from "@/lib/error-format"
import type { RepositoryListItem } from "@/types/api"

const HEALTH_POLL_MS = 30_000

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [repositories, setRepositories] = useState<RepositoryListItem[]>([])
  const [selected, setSelected] = useState<RepositoryListItem | null>(null)
  const [loadingRepositories, setLoadingRepositories] = useState(true)
  const [listError, setListError] = useState<WorkspaceContextValue["listError"]>(
    null,
  )
  const [cloning, setCloning] = useState(false)
  const [cloneError, setCloneError] =
    useState<WorkspaceContextValue["cloneError"]>(null)
  const [health, setHealth] = useState<HealthState>("checking")
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const loadingRepositoriesRef = useRef(loadingRepositories)
  loadingRepositoriesRef.current = loadingRepositories

  const loadRepositories = useCallback(async () => {
    if (!loadingRepositoriesRef.current) setLoadingRepositories(true)
    try {
      const response = await apiClient.listRepositories()
      setRepositories(response.repositories)
      setListError(null)
      return response.repositories
    } catch (caught) {
      setListError(formatApiError(caught))
      return []
    } finally {
      setLoadingRepositories(false)
    }
  }, [])

  useEffect(() => {
    void loadRepositories()
  }, [loadRepositories])

  useEffect(() => {
    let active = true
    const check = async () => {
      try {
        const status = await apiClient.health()
        if (!active) return
        setHealth(status.status === "healthy" ? "connected" : "degraded")
      } catch (caught) {
        if (!active) return
        setHealth(
          caught instanceof ApiClientError && caught.status === 503
            ? "degraded"
            : "offline",
        )
      }
    }
    void check()
    const timer = setInterval(() => void check(), HEALTH_POLL_MS)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  const selectRepository = useCallback((repository: RepositoryListItem) => {
    setSelected((current) =>
      current?.id === repository.id ? current : repository,
    )
    setSidebarOpen(false)
  }, [])

  const cloneRepository = useCallback(
    async (url: string) => {
      setCloning(true)
      setCloneError(null)
      try {
        const result = await apiClient.cloneRepository({ url })
        const updated = await loadRepositories()
        const repository = updated.find((item) => item.id === result.id)
        if (repository) {
          setSelected(repository)
          setSidebarOpen(false)
        }
      } catch (caught) {
        setCloneError(formatApiError(caught))
      } finally {
        setCloning(false)
      }
    },
    [loadRepositories],
  )

  const refreshRepositories = useCallback(() => {
    void loadRepositories()
  }, [loadRepositories])

  const clearCloneError = useCallback(() => setCloneError(null), [])

  const value: WorkspaceContextValue = {
    repositories,
    selected,
    selectedId: selected?.id ?? null,
    loadingRepositories,
    listError,
    cloning,
    cloneError,
    health,
    sidebarOpen,
    setSidebarOpen,
    selectRepository,
    cloneRepository,
    refreshRepositories,
    clearCloneError,
  }

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  )
}
