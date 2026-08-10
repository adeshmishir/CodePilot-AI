"use client"

import { useState } from "react"

import { Check, FolderGit2, Plus, RefreshCw } from "lucide-react"

import { ErrorAlert } from "@/components/error-alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { useWorkspace } from "@/context/use-workspace"
import { cn } from "@/lib/utils"

export function RepositorySidebar() {
  const {
    repositories,
    selectedId,
    loadingRepositories,
    listError,
    cloning,
    cloneError,
    sidebarOpen,
    selectRepository,
    cloneRepository,
    refreshRepositories,
  } = useWorkspace()
  const [url, setUrl] = useState("")

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!url.trim() || cloning) return
    await cloneRepository(url.trim())
    setUrl("")
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
            <p role="alert" className="text-destructive text-xs">
              {cloneError.message}
            </p>
          )}
        </form>
      </div>

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
              return (
                <li key={repository.id}>
                  <button
                    type="button"
                    onClick={() => selectRepository(repository)}
                    aria-current={active ? "true" : undefined}
                    className={cn(
                      "hover:bg-accent group relative flex w-full flex-col items-start gap-0.5 rounded-md py-2 pr-3 pl-3 text-left transition-colors",
                      active &&
                        "bg-accent text-accent-foreground ring-border ring-1 ring-inset",
                    )}
                  >
                    <span className="flex w-full items-center justify-between gap-2">
                      <span
                        className={cn(
                          "min-w-0 flex-1 truncate text-sm font-medium",
                        )}
                      >
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
                </li>
              )
            })}
          </ul>
        )}
      </nav>
    </aside>
  )
}
