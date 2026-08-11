"use client"

import { useState } from "react"

import { FileText, Search } from "lucide-react"

import { CopyButton } from "@/components/copy-button"
import { ErrorAlert } from "@/components/error-alert"
import { LoadingText } from "@/components/loading"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useWorkspace } from "@/context/use-workspace"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { useRepositoryReset } from "@/hooks/use-repository-reset"
import { apiClient } from "@/lib/api"
import type { SearchResponse } from "@/types/api"

interface SearchTabProps {
  repositoryId: number
}

export function SearchTab({ repositoryId }: SearchTabProps) {
  const { selected } = useWorkspace()
  const [query, setQuery] = useState("")
  const [submittedQuery, setSubmittedQuery] = useState("")
  const { loading, error, result, submitted, run, reset } = useAsyncSubmit(
    (q: string) => apiClient.search(repositoryId, { query: q, limit: 10 }),
  )

  useRepositoryReset(repositoryId, () => {
    reset()
    setSubmittedQuery("")
  })

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const text = query.trim()
    if (!text || loading) return
    setSubmittedQuery(text)
    setQuery("")
    void run(text)
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl">
        <div className="relative">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={loading}
            placeholder={`Search ${selected ? `${selected.owner}/${selected.name}` : "the repository"}…`}
            aria-label="Search repository"
            className="h-10 pl-9 pr-3"
          />
        </div>
        <div className="flex items-center justify-between gap-2 pt-2">
          <p className="text-muted-foreground text-xs">
            Semantic search across indexed code. Press Enter to search.
          </p>
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? (
              <span className="flex items-center gap-2">
                <LoadingText label="Searching" className="text-current [&>svg]:size-3.5" />
              </span>
            ) : (
              "Search"
            )}
          </Button>
        </div>
      </form>

      {error && (
        <div className="mx-auto w-full max-w-3xl">
          <ErrorAlert
            error={error}
            onRetry={() => void run(submittedQuery)}
          />
        </div>
      )}

      {!loading && !error && submitted && (
        <SearchResults result={result} query={submittedQuery} />
      )}
    </div>
  )
}

function SearchResults({
  result,
  query,
}: {
  result: SearchResponse | null
  query: string
}) {
  if (!result) return null

  if (result.results.length === 0) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-2 py-12 text-center">
        <FileText className="text-muted-foreground size-8" />
        <p className="text-sm font-medium">No results</p>
        <p className="text-muted-foreground max-w-sm text-xs">
          Nothing matched “{query}”. Try different wording or a broader
          search.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
      <p className="text-muted-foreground text-xs">
        {result.results.length} result{result.results.length > 1 ? "s" : ""} for
        “{query}”
      </p>
      {result.results.map((item, index) => (
        <Card key={index} className="py-3">
          <div className="flex flex-col gap-2 px-4 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono flex min-w-0 items-center gap-1.5 text-xs">
                <FileText className="text-muted-foreground size-3.5 shrink-0" />
                <span className="truncate">
                  {item.file_path}
                  {item.symbol_name ? ` · ${item.symbol_name}` : ""}
                </span>
              </span>
              <CopyButton text={item.content} label="Copy code snippet" />
            </div>

            <div className="flex flex-wrap items-center gap-1.5 text-xs">
              {item.symbol_type && (
                <Badge variant="outline">{item.symbol_type}</Badge>
              )}
              <Badge variant="secondary">
                {Math.round(item.score * 1000) / 1000}
              </Badge>
              <span className="text-muted-foreground">
                Lines {item.start_line}–{item.end_line}
              </span>
            </div>

            <pre className="bg-muted/50 text-muted-foreground max-h-48 overflow-x-auto overflow-y-auto rounded-md p-3 text-xs leading-relaxed whitespace-pre">
              {item.content}
            </pre>
          </div>
        </Card>
      ))}
    </div>
  )
}
