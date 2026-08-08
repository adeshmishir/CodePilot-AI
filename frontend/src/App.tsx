"use client"

import { useEffect, useState } from "react"

import { AgentTab } from "@/components/agent-tab"
import { BugDetectionTab } from "@/components/bug-detection-tab"
import { ChatTab } from "@/components/chat-tab"
import { GitHubTab } from "@/components/github-tab"
import { RepositorySidebar } from "@/components/repository-sidebar"
import { SearchTab } from "@/components/search-tab"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { apiClient, ApiClientError } from "@/lib/api"
import type { RepositoryListItem } from "@/types/api"

export default function App() {
  const [repositories, setRepositories] = useState<RepositoryListItem[]>([])
  const [selected, setSelected] = useState<RepositoryListItem | null>(null)
  const [cloning, setCloning] = useState(false)
  const [cloneError, setCloneError] = useState<string | null>(null)
  const [listError, setListError] = useState<string | null>(null)

  const loadRepositories = async (): Promise<RepositoryListItem[]> => {
    try {
      const response = await apiClient.listRepositories()
      setRepositories(response.repositories)
      setListError(null)
      return response.repositories
    } catch (caught) {
      setListError(
        caught instanceof Error ? caught.message : "Unable to load repositories",
      )
      return []
    }
  }

  useEffect(() => {
    void loadRepositories()
  }, [])

  const handleClone = async (url: string) => {
    setCloning(true)
    setCloneError(null)
    try {
      const result = await apiClient.cloneRepository({ url })
      const updated = await loadRepositories()
      const repository = updated.find(
        (item) => item.id === result.id,
      )
      if (repository) {
        setSelected(repository)
      }
    } catch (caught) {
      setCloneError(
        caught instanceof ApiClientError || caught instanceof Error
          ? caught.message
          : "Unable to clone repository",
      )
    } finally {
      setCloning(false)
    }
  }

  const handleSelect = (repository: RepositoryListItem) => {
    setSelected(repository)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <RepositorySidebar
        repositories={repositories}
        selectedId={selected?.id ?? null}
        onSelect={handleSelect}
        onClone={handleClone}
        cloning={cloning}
        error={cloneError}
      />

      <main className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b px-6 py-4">
          <h1 className="text-lg font-semibold">CodePilot AI</h1>
          {selected ? (
            <span className="text-muted-foreground text-sm">
              {selected.owner}/{selected.name}
            </span>
          ) : (
            <span className="text-muted-foreground text-sm">
              Select a repository to begin
            </span>
          )}
        </header>

        {listError && (
          <p className="border-b bg-destructive/10 px-6 py-2 text-sm text-destructive">
            {listError}
          </p>
        )}

        <div className="flex-1 overflow-auto p-6">
          {selected ? (
            <Tabs defaultValue="chat">
              <TabsList>
                <TabsTrigger value="chat">Chat</TabsTrigger>
                <TabsTrigger value="search">Search</TabsTrigger>
                <TabsTrigger value="agent">Agent</TabsTrigger>
                <TabsTrigger value="bugs">Bug Detection</TabsTrigger>
                <TabsTrigger value="github">GitHub</TabsTrigger>
              </TabsList>

              <TabsContent value="chat" className="mt-4">
                <ChatTab repositoryId={selected.id} />
              </TabsContent>
              <TabsContent value="search" className="mt-4">
                <SearchTab repositoryId={selected.id} />
              </TabsContent>
              <TabsContent value="agent" className="mt-4">
                <AgentTab repositoryId={selected.id} />
              </TabsContent>
              <TabsContent value="bugs" className="mt-4">
                <BugDetectionTab repositoryId={selected.id} />
              </TabsContent>
              <TabsContent value="github" className="mt-4">
                <GitHubTab repositoryId={selected.id} />
              </TabsContent>
            </Tabs>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-muted-foreground">
                Clone a repository from the sidebar to get started.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
