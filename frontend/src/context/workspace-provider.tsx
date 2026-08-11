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
  const [deletingId, setDeletingId] =
    useState<WorkspaceContextValue["deletingId"]>(null)
  const [deleteError, setDeleteError] =
    useState<WorkspaceContextValue["deleteError"]>(null)
  const [reindexingId, setReindexingId] =
    useState<WorkspaceContextValue["reindexingId"]>(null)
  const [repoActionError, setRepoActionError] =
    useState<WorkspaceContextValue["repoActionError"]>(null)
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
    let inFlight = false
    let timer: number | undefined
    let consecutiveFailures = 0

    const MAX_CONSECUTIVE_FAILURES = 2

    const scheduleNext = () => {
      if (!active || document.visibilityState === "hidden") return
      timer = window.setTimeout(() => {
        void runCheck()
      }, HEALTH_POLL_MS)
    }

    const runCheck = async () => {
      if (inFlight || !active) return
      inFlight = true
      try {
        const status = await apiClient.health()
        if (!active) return
        consecutiveFailures = 0
        setHealth(status.status === "healthy" ? "connected" : "degraded")
      } catch (caught) {
        if (!active) return
        if (caught instanceof ApiClientError) {
          consecutiveFailures = 0
          setHealth("degraded")
        } else {
          consecutiveFailures += 1
          if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
            setHealth("unavailable")
          }
        }
      } finally {
        inFlight = false
        scheduleNext()
      }
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        if (timer !== undefined) window.clearTimeout(timer)
        void runCheck()
      }
    }

    void runCheck()
    document.addEventListener("visibilitychange", handleVisibilityChange)
    return () => {
      active = false
      if (timer !== undefined) window.clearTimeout(timer)
      document.removeEventListener("visibilitychange", handleVisibilityChange)
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

  const deleteRepository = useCallback(
    async (repository: RepositoryListItem) => {
      setDeletingId(repository.id)
      setDeleteError(null)
      setRepoActionError(null)
      try {
        await apiClient.deleteRepository(repository.id)
        const updated = await loadRepositories()
        setSelected((current) => {
          if (!current || current.id !== repository.id) return current
          return updated[0] ?? null
        })
      } catch (caught) {
        setDeleteError(formatApiError(caught))
      } finally {
        setDeletingId(null)
      }
    },
    [loadRepositories],
  )

  const reindexRepository = useCallback(
    async (repository: RepositoryListItem) => {
      setReindexingId(repository.id)
      setRepoActionError(null)
      try {
        await apiClient.reindexRepository(repository.id)
        await loadRepositories()
      } catch (caught) {
        setRepoActionError(formatApiError(caught))
      } finally {
        setReindexingId(null)
      }
    },
    [loadRepositories],
  )

  const clearRepoActionError = useCallback(
    () => setRepoActionError(null),
    [],
  )

  const value: WorkspaceContextValue = {
    repositories,
    selected,
    selectedId: selected?.id ?? null,
    loadingRepositories,
    listError,
    cloning,
    cloneError,
    deletingId,
    deleteError,
    reindexingId,
    repoActionError,
    health,
    sidebarOpen,
    setSidebarOpen,
    selectRepository,
    cloneRepository,
    deleteRepository,
    reindexRepository,
    refreshRepositories,
    clearCloneError,
    clearRepoActionError,
  }

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  )
}
