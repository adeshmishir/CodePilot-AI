"use client"

import { useState } from "react"

import { Bot, ChevronDown, ListChecks, Terminal, User } from "lucide-react"

import { CopyButton } from "@/components/copy-button"
import { ErrorAlert } from "@/components/error-alert"
import { CodeBlock, Markdown } from "@/components/markdown"
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
import type { AgentResponse, AgentToolCall } from "@/types/api"

interface AgentTabProps {
  repositoryId: number
}

export function AgentTab({ repositoryId }: AgentTabProps) {
  const { selected } = useWorkspace()
  const [query, setQuery] = useState("")
  const [submittedQuery, setSubmittedQuery] = useState("")
  const [multi, setMulti] = useState(false)
  const { loading, error, result, run, reset } = useAsyncSubmit(
    (q: string, mode: "single" | "multi") =>
      apiClient.runAgent(repositoryId, { query: q, max_steps: 5, mode }),
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
    void run(text, multi ? "multi" : "single")
  }

  return (
    <div className="flex flex-col gap-4">
      <form
        onSubmit={handleSubmit}
        className="border-border bg-card mx-auto w-full max-w-3xl rounded-xl border p-4 shadow-sm"
      >
        <label htmlFor="agent-query" className="sr-only">
          Describe a task for the agent
        </label>
        <Input
          id="agent-query"
          placeholder={
            selected
              ? `Describe a task in ${selected.owner}/${selected.name}…`
              : "Describe a task for the agent to perform…"
          }
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
          className="h-10"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 pt-3">
          <div className="flex gap-1" role="group" aria-label="Agent mode">
            <Button
              type="button"
              variant={!multi ? "default" : "outline"}
              size="sm"
              onClick={() => setMulti(false)}
              disabled={loading}
            >
              Single agent
            </Button>
            <Button
              type="button"
              variant={multi ? "default" : "outline"}
              size="sm"
              onClick={() => setMulti(true)}
              disabled={loading}
            >
              Multi agent
            </Button>
          </div>
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? (
              <span className="flex items-center gap-2">
                <LoadingText
                  label="Agent is working"
                  className="text-current [&>svg]:size-3.5"
                />
              </span>
            ) : (
              "Run agent"
            )}
          </Button>
        </div>
      </form>

      {error && (
        <div className="mx-auto w-full max-w-3xl">
          <ErrorAlert
            error={error}
            onRetry={() => void run(query.trim(), multi ? "multi" : "single")}
          />
        </div>
      )}

      {loading && (
        <div className="mx-auto w-full max-w-3xl">
          <div className="bg-card border-border flex items-center gap-3 rounded-xl border p-4 text-sm shadow-sm">
            <LoadingText label={multi ? "Orchestrating agents…" : "Planning and executing…"} />
          </div>
        </div>
      )}

      {!loading && result && (
        <AgentResult result={result} requestQuery={submittedQuery} />
      )}
    </div>
  )
}

function AgentResult({
  result,
  requestQuery,
}: {
  result: AgentResponse
  requestQuery: string
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <section className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <User className="text-muted-foreground size-4" />
          <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Your request
          </h3>
        </div>
        <Card className="py-3">
          <div className="bg-card px-4 text-sm">
            <span className="text-muted-foreground text-sm whitespace-pre-wrap">
              {requestQuery}
            </span>
          </div>
        </Card>
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Bot className="text-muted-foreground size-4" />
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Final answer
            </h3>
          </div>
          <CopyButton text={result.answer} label="Copy answer" />
        </div>
        <Card className="py-4">
          <div className="px-4">
            <Markdown>{result.answer}</Markdown>
          </div>
        </Card>
      </section>

      {result.plan.length > 0 && (
        <section className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <ListChecks className="text-muted-foreground size-4" />
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Plan
            </h3>
          </div>
          <Card className="py-3">
            <ol className="flex list-decimal flex-col gap-1.5 px-4 text-sm pl-8">
              {result.plan.map((step, index) => (
                <li key={index} className="pl-1">
                  {step}
                </li>
              ))}
            </ol>
          </Card>
        </section>
      )}

      {result.agents.length > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Agents
          </h3>
          <div className="flex flex-col gap-2">
            {result.agents.map((agent, index) => (
              <Card key={index} className="py-3">
                <div className="flex flex-col gap-2 px-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Bot className="text-muted-foreground size-4 shrink-0" />
                    <Badge>{agent.name}</Badge>
                  </div>
                  <p className="text-muted-foreground">{agent.summary}</p>
                  {agent.detail && (
                    <details className="group">
                      <summary className="text-muted-foreground cursor-pointer text-xs list-none select-none hover:text-foreground">
                        <ChevronDown className="mr-1 inline size-3.5 transition-transform group-open:rotate-180" />
                        Details
                      </summary>
                      <pre className="text-muted-foreground mt-2 overflow-x-auto rounded-md bg-muted/50 p-3 text-xs whitespace-pre-wrap">
                        {agent.detail}
                      </pre>
                    </details>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {result.tool_calls.length > 0 && (
        <section className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Terminal className="text-muted-foreground size-4" />
            <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Tool calls
            </h3>
            <Badge variant="secondary" className="ml-auto">
              {result.tool_calls.length}
            </Badge>
          </div>
          <div className="flex flex-col gap-2">
            {result.tool_calls.map((call, index) => (
              <ToolCallCard key={index} call={call} index={index} />
            ))}
          </div>
        </section>
      )}

      {result.observations.length > 0 && (
        <section className="flex flex-col gap-2">
          <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Observations
          </h3>
          <Card className="py-3">
            <ol className="flex list-decimal flex-col gap-1.5 px-4 text-sm pl-8">
              {result.observations.map((observation, index) => (
                <li key={index} className="text-muted-foreground pl-1">
                  {observation}
                </li>
              ))}
            </ol>
          </Card>
        </section>
      )}
    </div>
  )
}

function ToolCallCard({
  call,
  index,
}: {
  call: AgentToolCall
  index: number
}) {
  return (
    <details className="border-border bg-card group rounded-xl border shadow-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 select-none">
        <ChevronDown className="text-muted-foreground size-4 shrink-0 transition-transform group-open:rotate-180" />
        <Badge variant="secondary" className="font-mono">
          {index + 1}. {call.tool}
        </Badge>
        <span
          className={cn(
            "text-muted-foreground min-w-0 flex-1 truncate text-xs",
          )}
        >
          {call.observation.slice(0, 80) || "No observation"}
        </span>
      </summary>
      <div className="flex flex-col gap-2 border-t px-4 py-3">
        {Object.keys(call.arguments).length > 0 && (
          <CodeBlock
            code={JSON.stringify(call.arguments, null, 2)}
            language="json"
          />
        )}
        <CodeBlock code={call.observation} />
      </div>
    </details>
  )
}
