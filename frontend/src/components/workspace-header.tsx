"use client"

import { useState } from "react"

import {
  Check,
  ChevronDown,
  FolderGit2,
  Menu,
  Sparkles,
} from "lucide-react"

import { Tooltip } from "@/components/ui/tooltip"
import { useWorkspace } from "@/context/use-workspace"
import type { HealthState } from "@/context/workspace-context"
import { cn } from "@/lib/utils"
import type { RepositoryListItem } from "@/types/api"

export type WorkspaceTab =
  | "chat"
  | "search"
  | "agent"
  | "bugs"
  | "github"

const TAB_LABELS: Record<WorkspaceTab, string> = {
  chat: "Chat",
  search: "Search",
  agent: "Agent",
  bugs: "Bug Detection",
  github: "GitHub",
}

const HEALTH_META: Record<
  HealthState,
  { dot: string; label: string }
> = {
  checking: { dot: "bg-muted-foreground animate-pulse", label: "Checking backend" },
  connected: { dot: "bg-emerald-500", label: "Connected" },
  degraded: { dot: "bg-amber-500", label: "Backend degraded" },
  unavailable: {
    dot: "bg-amber-500",
    label: "Backend status unavailable",
  },
}

interface WorkspaceHeaderProps {
  activeTab: WorkspaceTab
}

export function WorkspaceHeader({ activeTab }: WorkspaceHeaderProps) {
  const {
    setSidebarOpen,
    repositories,
    selectedId,
    selectRepository,
    health,
  } = useWorkspace()

  const healthMeta = HEALTH_META[health]

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b px-4 sm:px-6">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open repositories sidebar"
          className="text-muted-foreground hover:text-foreground focus-visible:ring-ring -ml-1 flex size-9 shrink-0 items-center justify-center rounded-lg outline-none hover:bg-accent focus-visible:ring-2 md:hidden"
        >
          <Menu className="size-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="bg-primary text-primary-foreground flex size-7 shrink-0 items-center justify-center rounded-md">
            <Sparkles className="size-4" />
          </span>
          <span className="text-sm font-semibold whitespace-nowrap">
            CodePilot AI
          </span>
        </div>

        <span className="border-border hidden h-5 w-px bg-border sm:block" />
        <span className="text-muted-foreground hidden text-sm sm:block">
          {TAB_LABELS[activeTab]}
        </span>
      </div>

      <div className="flex min-w-0 items-center gap-2">
        <RepositorySwitcher
          repositories={repositories}
          selectedId={selectedId}
          onSelect={selectRepository}
        />

        <Tooltip
          content={healthMeta.label}
          side="bottom"
        >
          <div
            className="border-border flex items-center gap-1.5 rounded-md border px-2 py-1.5"
            aria-label={`Backend status: ${healthMeta.label}`}
          >
            <span className={cn("size-2 rounded-full", healthMeta.dot)} />
            <span className="text-muted-foreground hidden text-xs lg:inline">
              {healthMeta.label}
            </span>
          </div>
        </Tooltip>
      </div>
    </header>
  )
}

interface RepositorySwitcherProps {
  repositories: RepositoryListItem[]
  selectedId: number | null
  onSelect: (repository: RepositoryListItem) => void
}

function RepositorySwitcher({
  repositories,
  selectedId,
  onSelect,
}: RepositorySwitcherProps) {
  const [open, setOpen] = useState(false)
  const selected = repositories.find((repository) => repository.id === selectedId)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={selected ? `Switch repository (currently ${selected.owner}/${selected.name})` : "Select a repository"}
        className="focus-visible:ring-ring flex h-8 min-w-0 items-center gap-1.5 rounded-md border bg-background px-2 text-sm transition-colors outline-none hover:bg-accent focus-visible:ring-2"
      >
        <FolderGit2 className="text-muted-foreground size-4 shrink-0" />
        <span className="min-w-0 max-w-40 truncate font-medium">
          {selected ? `${selected.owner}/${selected.name}` : "Select repository"}
        </span>
        <ChevronDown className="text-muted-foreground size-4 shrink-0" />
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-30"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
          <div
            role="listbox"
            aria-label="Repositories"
            className="bg-popover text-popover-foreground absolute right-0 z-40 mt-2 max-h-72 w-72 overflow-y-auto rounded-lg border p-1 shadow-lg"
          >
            {repositories.length === 0 && (
              <p className="text-muted-foreground px-3 py-3 text-xs">
                No repositories yet. Clone one from the sidebar.
              </p>
            )}
            {repositories.map((repository) => {
              const active = repository.id === selectedId
              return (
                <button
                  key={repository.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    onSelect(repository)
                    setOpen(false)
                  }}
                  className={cn(
                    "hover:bg-accent hover:text-accent-foreground flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm",
                    active && "bg-accent text-accent-foreground",
                  )}
                >
                  <span className="min-w-0 truncate">
                    {repository.owner}/{repository.name}
                  </span>
                  {active && <Check className="size-4 shrink-0" />}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
