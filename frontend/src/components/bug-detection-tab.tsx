"use client"

import { useState } from "react"

import { CheckCircle2, FileWarning } from "lucide-react"

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
import { cn } from "@/lib/utils"
import type { BugDetectionResponse, BugFinding, Severity } from "@/types/api"

interface BugDetectionTabProps {
  repositoryId: number
}

export function BugDetectionTab({ repositoryId }: BugDetectionTabProps) {
  const { selected } = useWorkspace()
  const [query, setQuery] = useState("")
  const { loading, error, result, submitted, run, reset } = useAsyncSubmit(
    (q: string) => apiClient.detectBugs(repositoryId, { query: q, limit: 8 }),
  )

  useRepositoryReset(repositoryId, reset)

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const text = query.trim()
    if (!text || loading) return
    void run(text)
  }

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={handleSubmit}
        className="border-border bg-card mx-auto w-full max-w-3xl rounded-xl border p-4 shadow-sm"
      >
        <label htmlFor="bug-query" className="sr-only">
          Area of the repository to analyze
        </label>
        <Input
          id="bug-query"
          placeholder={
            selected
              ? `Analyze ${selected.owner}/${selected.name} for bugs…`
              : "Area of the repository to analyze for bugs…"
          }
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
          className="h-10"
        />
        <div className="flex items-center justify-between gap-2 pt-3">
          <p className="text-muted-foreground text-xs">
            Scans retrieved code and reports likely issues with suggested
            fixes.
          </p>
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? (
              <span className="flex items-center gap-2">
                <LoadingText
                  label="Analyzing"
                  className="text-current [&>svg]:size-3.5"
                />
              </span>
            ) : (
              "Detect bugs"
            )}
          </Button>
        </div>
      </form>

      {error && (
        <div className="mx-auto w-full max-w-3xl">
          <ErrorAlert error={error} onRetry={() => void run(query.trim())} />
        </div>
      )}

      {!loading && !error && submitted && (
        <BugResults result={result} />
      )}
    </div>
  )
}

const severityStyles: Record<
  Severity,
  { className: string; dot: string }
> = {
  critical: {
    className: "border-transparent bg-red-500/15 text-red-600 dark:text-red-400",
    dot: "bg-red-500",
  },
  high: {
    className: "border-transparent bg-orange-500/15 text-orange-600 dark:text-orange-400",
    dot: "bg-orange-500",
  },
  medium: {
    className: "border-transparent bg-amber-500/15 text-amber-600 dark:text-amber-400",
    dot: "bg-amber-500",
  },
  low: {
    className: "border-transparent bg-slate-500/15 text-slate-600 dark:text-slate-400",
    dot: "bg-slate-500",
  },
}

function BugResults({ result }: { result: BugDetectionResponse | null }) {
  if (!result) return null

  if (result.findings.length === 0) {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-2 py-12 text-center">
        <CheckCircle2 className="text-emerald-500 size-8" />
        <p className="text-sm font-medium">No bugs found</p>
        <p className="text-muted-foreground max-w-sm text-xs">
          The analyzed area did not surface any likely issues.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-3">
      <p className="text-muted-foreground text-xs">
        {result.findings.length} potential issue
        {result.findings.length > 1 ? "s" : ""} found
      </p>
      {result.findings.map((finding, index) => (
        <BugFindingCard key={index} finding={finding} />
      ))}
    </div>
  )
}

function BugFindingCard({ finding }: { finding: BugFinding }) {
  const severity = severityStyles[finding.severity] ?? severityStyles.low

  return (
    <Card className="py-4">
      <div className="flex flex-col gap-3 px-4 text-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2">
            <span
              className={cn(
                "mt-1.5 size-2 shrink-0 rounded-full",
                severity.dot,
              )}
            />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium">{finding.title}</span>
              <span className="font-mono text-muted-foreground flex items-center gap-1 text-xs">
                <FileWarning className="size-3.5 shrink-0" />
                {finding.file_path}:{finding.start_line}–
                {finding.end_line}
              </span>
            </div>
          </div>
          <Badge className={severity.className}>{finding.severity}</Badge>
        </div>

        <p>{finding.description}</p>

        {finding.evidence && (
          <div className="group relative">
            <div className="absolute top-2 right-2 z-10">
              <CopyButton
                text={finding.evidence}
                label="Copy evidence"
              />
            </div>
            <pre className="bg-muted/50 text-muted-foreground overflow-x-auto rounded-md p-3 text-xs leading-relaxed whitespace-pre">
              {finding.evidence}
            </pre>
          </div>
        )}

        {finding.recommendation && (
          <div className="border-border flex flex-col gap-1 rounded-md border-l-2 border-l-primary bg-muted/40 p-3">
            <span className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
              Suggested fix
            </span>
            <p>{finding.recommendation}</p>
          </div>
        )}
      </div>
    </Card>
  )
}
