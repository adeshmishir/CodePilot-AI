"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { apiClient } from "@/lib/api"
import type { SearchResponse } from "@/types/api"

interface SearchTabProps {
  repositoryId: number
}

export function SearchTab({ repositoryId }: SearchTabProps) {
  const [query, setQuery] = useState("")
  const { loading, error, result, run } = useAsyncSubmit(
    (q: string) =>
      apiClient.search(repositoryId, { query: q, limit: 10 }),
  )

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!query.trim() || loading) return
    void run(query.trim())
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          placeholder="Search the repository semantically…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </form>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {result && <SearchResults result={result} />}
    </div>
  )
}

function SearchResults({ result }: { result: SearchResponse }) {
  if (result.results.length === 0) {
    return <p className="text-muted-foreground text-sm">No results.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {result.results.map((item, index) => (
        <Card key={index}>
          <CardContent className="flex flex-col gap-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs">
                {item.file_path}
                {item.symbol_name ? ` · ${item.symbol_name}` : ""}
              </span>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{item.symbol_type}</Badge>
                <Badge>{item.score.toFixed(3)}</Badge>
              </div>
            </div>
            <span className="text-muted-foreground text-xs">
              Lines {item.start_line}–{item.end_line}
            </span>
            <pre className="text-muted-foreground overflow-x-auto rounded-md bg-muted p-3 text-xs">
              {item.content}
            </pre>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
