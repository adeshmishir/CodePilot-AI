"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { RepositoryListItem } from "@/types/api"

interface RepositorySidebarProps {
  repositories: RepositoryListItem[]
  selectedId: number | null
  onSelect: (repository: RepositoryListItem) => void
  onClone: (url: string) => Promise<void>
  cloning: boolean
  error: string | null
}

export function RepositorySidebar({
  repositories,
  selectedId,
  onSelect,
  onClone,
  cloning,
  error,
}: RepositorySidebarProps) {
  const [url, setUrl] = useState("")

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!url.trim() || cloning) return
    await onClone(url.trim())
    setUrl("")
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r bg-muted/40">
      <div className="border-b p-4">
        <h2 className="mb-3 text-sm font-semibold">Repositories</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <Input
            placeholder="https://github.com/owner/repo"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={cloning}
          />
          <Button type="submit" disabled={cloning || !url.trim()}>
            {cloning ? "Cloning…" : "Clone repository"}
          </Button>
          {error && (
            <p className="text-destructive text-xs">{error}</p>
          )}
        </form>
      </div>

      <nav className="flex-1 overflow-y-auto p-2">
        {repositories.length === 0 ? (
          <p className="text-muted-foreground px-2 py-4 text-sm">
            No repositories yet. Clone one to get started.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {repositories.map((repository) => (
              <li key={repository.id}>
                <button
                  type="button"
                  onClick={() => onSelect(repository)}
                  className={cn(
                    "hover:bg-accent flex w-full flex-col items-start gap-0.5 rounded-md px-3 py-2 text-left",
                    selectedId === repository.id &&
                      "bg-accent text-accent-foreground"
                  )}
                >
                  <span className="text-sm font-medium">
                    {repository.owner}/{repository.name}
                  </span>
                  <span className="text-muted-foreground truncate text-xs">
                    {repository.local_path}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </nav>
    </aside>
  )
}
