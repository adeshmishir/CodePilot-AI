"use client"

import { useState } from "react"

import {
  Check,
  FolderGit2,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react"

import { ErrorAlert } from "@/components/error-alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { useWorkspace } from "@/context/use-workspace"
import { cn } from "@/lib/utils"
import type { RepositoryListItem } from "@/types/api"

export function RepositorySidebar() {
  const {
    repositories,
    selectedId,
    loadingRepositories,
    listError,
    cloning,
    cloneError,
    cloneProgress,
    deletingId,
    deleteError,
    reindexingId,
    repoActionError,
    sidebarOpen,
    selectRepository,
    cloneRepository,
    deleteRepository,
    reindexRepository,
    refreshRepositories,
    clearCloneError,
    clearRepoActionError,
  } = useWorkspace()
  const [url, setUrl] = useState("")
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!url.trim() || cloning) return
    await cloneRepository(url.trim())
    setUrl("")
  }

  const handleConfirmDelete = async (repository: RepositoryListItem) => {
    await deleteRepository(repository)
    setPendingDeleteId(null)
  }

  return (
    <aside
      className={cn(
        "bg-muted/40 fixed inset-y-0 left-0 z-50 flex w-72 shrink-0 flex-col border-r transition-transform md:static md:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full",
      )}
      aria-label="Repositories"
    >
      <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Repositories</h2>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground text-xs">
            {repositories.length}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-7"
            onClick={refreshRepositories}
            aria-label="Refresh repositories"
            title="Refresh repositories"
          >
            <RefreshCw className="size-3.5" />
          </Button>
        </div>
      </div>

      <div className="border-b p-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <label htmlFor="clone-url" className="sr-only">
            Repository URL to clone
          </label>
          <div className="relative">
            <Plus className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2" />
            <Input
              id="clone-url"
              placeholder="https://github.com/owner/repo"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              disabled={cloning}
              className="pl-8"
            />
          </div>
          <Button
            type="submit"
            variant="secondary"
            disabled={cloning || !url.trim()}
          >
            {cloning ? "Cloning…" : "Clone repository"}
          </Button>
          {cloneError && (
            <div className="flex items-start gap-1">
              <ErrorAlert error={cloneError} className="flex-1" />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="mt-0.5 size-6 shrink-0"
                onClick={clearCloneError}
                aria-label="Dismiss clone error"
                title="Dismiss"
              >
                <X className="size-3.5" />
              </Button>
            </div>
          )}
        </form>

        {cloneProgress && (
          <div
            className="mt-3 flex flex-col gap-1.5"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={cloneProgress.percent}
            aria-label="Clone progress"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-xs font-medium">
                {cloneProgress.phase === "cloning" ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <FolderGit2 className="size-3" />
                )}
                {cloneProgress.phase === "cloning"
                  ? "Cloning repository…"
                  : "Indexing files…"}
              </span>
              <span className="text-muted-foreground text-xs tabular-nums">
                {cloneProgress.percent}%
              </span>
            </div>
            <div className="bg-muted h-1.5 w-full overflow-hidden rounded-full">
              <div
                className="bg-primary h-full rounded-full transition-[width] duration-300"
                style={{ width: `${cloneProgress.percent}%` }}
              />
            </div>
            {cloneProgress.filesTotal > 0 && (
              <p className="text-muted-foreground text-[11px] tabular-nums">
                {cloneProgress.filesDone.toLocaleString()} /{" "}
                {cloneProgress.filesTotal.toLocaleString()} files
              </p>
            )}
          </div>
        )}
      </div>

      {repoActionError && (
        <div className="border-b p-3">
          <div className="flex items-start gap-1">
            <ErrorAlert error={repoActionError} className="flex-1" />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="mt-0.5 size-6 shrink-0"
              onClick={clearRepoActionError}
              aria-label="Dismiss error"
              title="Dismiss"
            >
              <X className="size-3.5" />
            </Button>
          </div>
        </div>
      )}

      <nav className="flex-1 overflow-y-auto p-2">
        {loadingRepositories ? (
          <div className="flex flex-col gap-2 p-1">
            {[0, 1, 2].map((item) => (
              <div
                key={item}
                className="flex flex-col gap-1.5 rounded-md px-3 py-2"
              >
                <Skeleton className="h-3.5 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : listError ? (
          <div className="p-2">
            <ErrorAlert error={listError} onRetry={refreshRepositories} />
          </div>
        ) : repositories.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-8 text-center">
            <FolderGit2 className="text-muted-foreground size-8" />
            <p className="text-sm font-medium">No repositories yet</p>
            <p className="text-muted-foreground text-xs">
              Paste a GitHub URL above to clone and index your first
              repository.
            </p>
          </div>
        ) : (
          <ul className="flex flex-col gap-1">
            {repositories.map((repository) => {
              const active = selectedId === repository.id
              const isDeleting = deletingId === repository.id
              const isReindexing = reindexingId === repository.id
              const busy = isDeleting || isReindexing
              const confirming = pendingDeleteId === repository.id

              return (
                <li key={repository.id}>
                  <div
                    className={cn(
                      "flex items-center rounded-md transition-colors",
                      active &&
                        "bg-accent text-accent-foreground ring-border ring-1 ring-inset",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => selectRepository(repository)}
                      aria-current={active ? "true" : undefined}
                      className="hover:bg-accent flex min-w-0 flex-1 flex-col items-start gap-0.5 rounded-md py-2 pr-1 pl-3 text-left transition-colors"
                    >
                      <span className="flex w-full items-center justify-between gap-2">
                        <span className="min-w-0 flex-1 truncate text-sm font-medium">
                          {repository.owner}/{repository.name}
                        </span>
                        {active && (
                          <Check className="text-primary size-4 shrink-0" />
                        )}
                      </span>
                      <span className="text-muted-foreground w-full truncate text-xs">
                        {repository.local_path}
                      </span>
                    </button>

                    <div className="flex shrink-0 items-center gap-0.5 pr-1.5">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        onClick={() => reindexRepository(repository)}
                        disabled={busy}
                        aria-label={`Reindex ${repository.owner}/${repository.name}`}
                        title="Reindex repository"
                      >
                        {isReindexing ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="size-3.5" />
                        )}
                      </Button>

                      {confirming && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-7"
                          onClick={() => setPendingDeleteId(null)}
                          disabled={busy}
                          aria-label="Cancel delete"
                          title="Cancel"
                        >
                          <X className="size-3.5" />
                        </Button>
                      )}

                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className={cn(
                          "size-7",
                          confirming
                            ? "text-destructive hover:text-destructive"
                            : "hover:text-destructive",
                        )}
                        onClick={() =>
                          confirming
                            ? void handleConfirmDelete(repository)
                            : setPendingDeleteId(repository.id)
                        }
                        disabled={busy}
                        aria-label={
                          confirming
                            ? `Confirm delete ${repository.owner}/${repository.name}`
                            : `Delete ${repository.owner}/${repository.name}`
                        }
                        title={
                          confirming
                            ? "Confirm delete repository"
                            : "Delete repository"
                        }
                      >
                        {isDeleting ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="size-3.5" />
                        )}
                      </Button>
                    </div>
                  </div>
                  {deleteError && confirming && (
                    <div className="mt-1 px-1">
                      <ErrorAlert error={deleteError} className="text-xs" />
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </nav>
    </aside>
  )
}
