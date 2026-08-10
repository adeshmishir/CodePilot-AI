"use client"

import { useState } from "react"

import {
  Bot,
  Bug,
  FolderGit2,
  GitPullRequest,
  MessageSquare,
  Search,
  Sparkles,
} from "lucide-react"

import { AgentTab } from "@/components/agent-tab"
import { BugDetectionTab } from "@/components/bug-detection-tab"
import { ChatTab } from "@/components/chat-tab"
import { GitHubTab } from "@/components/github-tab"
import { RepositorySidebar } from "@/components/repository-sidebar"
import { SearchTab } from "@/components/search-tab"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { WorkspaceHeader } from "@/components/workspace-header"
import type { WorkspaceTab } from "@/components/workspace-header"
import { WorkspaceProvider } from "@/context/workspace-provider"
import { useWorkspace } from "@/context/use-workspace"

export default function App() {
  return (
    <WorkspaceProvider>
      <Workspace />
    </WorkspaceProvider>
  )
}

function Workspace() {
  const { selected, selectedId, sidebarOpen, setSidebarOpen, listError, refreshRepositories } =
    useWorkspace()
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("chat")

  return (
    <div className="bg-background text-foreground flex h-dvh overflow-hidden">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <RepositorySidebar />

      <main className="flex min-w-0 flex-1 flex-col">
        <WorkspaceHeader activeTab={activeTab} />

        {listError && (
          <div className="border-border flex items-center justify-between gap-3 border-b bg-destructive/10 px-4 py-2 sm:px-6">
            <p className="text-destructive text-sm">{listError.message}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={refreshRepositories}
            >
              Retry
            </Button>
          </div>
        )}

        {selected && selectedId !== null ? (
          <Tabs
            value={activeTab}
            onValueChange={(value) => setActiveTab(value as WorkspaceTab)}
            className="min-h-0 flex-1 overflow-hidden"
          >
            <TabsList className="mx-3 mt-3 max-w-[calc(100%-1.5rem)] overflow-x-auto md:mx-auto">
              <TabsTrigger value="chat">
                <MessageSquare className="size-4" />
                <span className="hidden sm:inline">Chat</span>
              </TabsTrigger>
              <TabsTrigger value="search">
                <Search className="size-4" />
                <span className="hidden sm:inline">Search</span>
              </TabsTrigger>
              <TabsTrigger value="agent">
                <Bot className="size-4" />
                <span className="hidden sm:inline">Agent</span>
              </TabsTrigger>
              <TabsTrigger value="bugs">
                <Bug className="size-4" />
                <span className="hidden sm:inline">Bug Detection</span>
              </TabsTrigger>
              <TabsTrigger value="github">
                <GitPullRequest className="size-4" />
                <span className="hidden sm:inline">GitHub</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent
              value="chat"
              forceMount
              className="flex min-h-0 flex-1 flex-col overflow-hidden"
            >
              <ChatTab repositoryId={selectedId} />
            </TabsContent>
            <TabsContent
              value="search"
              forceMount
              className="min-h-0 flex-1 overflow-y-auto pt-4 sm:pt-6"
            >
              <SearchTab repositoryId={selectedId} />
            </TabsContent>
            <TabsContent
              value="agent"
              forceMount
              className="min-h-0 flex-1 overflow-y-auto pt-4 sm:pt-6"
            >
              <AgentTab repositoryId={selectedId} />
            </TabsContent>
            <TabsContent
              value="bugs"
              forceMount
              className="min-h-0 flex-1 overflow-y-auto pt-4 sm:pt-6"
            >
              <BugDetectionTab repositoryId={selectedId} />
            </TabsContent>
            <TabsContent
              value="github"
              forceMount
              className="min-h-0 flex-1 overflow-y-auto pt-4 sm:pt-6"
            >
              <GitHubTab repositoryId={selectedId} />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
            <div className="bg-primary/10 flex size-14 items-center justify-center rounded-2xl">
              <Sparkles className="text-primary size-7" />
            </div>
            <h2 className="text-base font-semibold">Get started with CodePilot</h2>
            <p className="text-muted-foreground max-w-sm text-sm">
              Clone a repository from the sidebar to ask questions, search
              the code, run agents, and detect bugs.
            </p>
            <Button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="mt-1 md:hidden"
            >
              <FolderGit2 className="size-4" />
              Open repositories
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}
