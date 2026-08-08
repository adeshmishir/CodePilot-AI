"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { apiClient } from "@/lib/api"
import type { ChatResponse } from "@/types/api"

interface ChatTabProps {
  repositoryId: number
}

export function ChatTab({ repositoryId }: ChatTabProps) {
  const [query, setQuery] = useState("")
  const { loading, error, result, run } = useAsyncSubmit(
    (q: string) =>
      apiClient.chat(repositoryId, { query: q, limit: 5 }),
  )

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!query.trim() || loading) return
    void run(query.trim())
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Textarea
          placeholder="Ask a question about this repository…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
          rows={3}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Thinking…" : "Ask"}
          </Button>
        </div>
      </form>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {result && <ChatResult result={result} />}
    </div>
  )
}

function ChatResult({ result }: { result: ChatResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="prose prose-sm max-w-none whitespace-pre-wrap">
          {result.answer}
        </CardContent>
      </Card>

      {result.sources.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Sources</h3>
          {result.sources.map((source, index) => (
            <Card key={index}>
              <CardContent className="flex flex-col gap-1 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs">
                    {source.file_path}
                    {source.symbol_name
                      ? ` · ${source.symbol_name}`
                      : ""}
                  </span>
                  <Badge variant="secondary">
                    {source.score.toFixed(3)}
                  </Badge>
                </div>
                <span className="text-muted-foreground text-xs">
                  Lines {source.start_line}–{source.end_line}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
