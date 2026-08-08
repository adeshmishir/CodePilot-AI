"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { apiClient } from "@/lib/api"
import type { BugDetectionResponse, Severity } from "@/types/api"

interface BugDetectionTabProps {
  repositoryId: number
}

export function BugDetectionTab({
  repositoryId,
}: BugDetectionTabProps) {
  const [query, setQuery] = useState("")
  const { loading, error, result, run } = useAsyncSubmit(
    (q: string) =>
      apiClient.detectBugs(repositoryId, { query: q, limit: 8 }),
  )

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!query.trim() || loading) return
    void run(query.trim())
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Input
          placeholder="Area of the repository to analyze for bugs…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Analyzing…" : "Detect bugs"}
          </Button>
        </div>
      </form>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {result && <BugResults result={result} />}
    </div>
  )
}

const severityVariant: Record<Severity, "destructive" | "secondary" | "outline" | "default"> = {
  critical: "destructive",
  high: "destructive",
  medium: "outline",
  low: "secondary",
}

function BugResults({ result }: { result: BugDetectionResponse }) {
  if (result.findings.length === 0) {
    return <p className="text-muted-foreground text-sm">No bugs found.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {result.findings.map((finding, index) => (
        <Card key={index}>
          <CardContent className="flex flex-col gap-2 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{finding.title}</span>
              <Badge variant={severityVariant[finding.severity]}>
                {finding.severity}
              </Badge>
            </div>

            <p>{finding.description}</p>

            <div className="flex items-center gap-2 text-xs">
              <span className="font-mono">
                {finding.file_path}:{finding.start_line}–
                {finding.end_line}
              </span>
            </div>

            <pre className="text-muted-foreground overflow-x-auto rounded-md bg-muted p-3 text-xs">
              {finding.evidence}
            </pre>

            <p className="text-muted-foreground text-xs">
              <span className="font-medium text-foreground">
                Recommendation:
              </span>{" "}
              {finding.recommendation}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
