"use client"

import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { apiClient } from "@/lib/api"
import type { AgentResponse } from "@/types/api"

interface AgentTabProps {
  repositoryId: number
}

export function AgentTab({ repositoryId }: AgentTabProps) {
  const [query, setQuery] = useState("")
  const [multi, setMulti] = useState(false)
  const { loading, error, result, run } = useAsyncSubmit(
    (q: string, mode: "single" | "multi") =>
      apiClient.runAgent(repositoryId, { query: q, max_steps: 5, mode }),
  )

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!query.trim() || loading) return
    void run(query.trim(), multi ? "multi" : "single")
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <Input
          placeholder="Describe a task for the agent to perform…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={loading}
        />
        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-1">
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
            {loading ? "Agent is working…" : "Run agent"}
          </Button>
        </div>
      </form>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {result && <AgentResult result={result} />}
    </div>
  )
}

function AgentResult({ result }: { result: AgentResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="whitespace-pre-wrap text-sm">
          {result.answer}
        </CardContent>
      </Card>

      {result.agents.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Agents</h3>
          {result.agents.map((agent, index) => (
            <Card key={index}>
              <CardContent className="flex flex-col gap-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge>{agent.name}</Badge>
                  <span className="text-muted-foreground">
                    {agent.summary}
                  </span>
                </div>
                {agent.detail && (
                  <pre className="text-muted-foreground overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
                    {agent.detail}
                  </pre>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {result.plan.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Plan</h3>
          <ol className="flex list-decimal flex-col gap-1 pl-5 text-sm">
            {result.plan.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      {result.tool_calls.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Tool calls</h3>
          {result.tool_calls.map((call, index) => (
            <Card key={index}>
              <CardContent className="flex flex-col gap-2 text-sm">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary">{call.tool}</Badge>
                </div>
                <pre className="text-muted-foreground overflow-x-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(call.arguments, null, 2)}
                </pre>
                <pre className="text-muted-foreground overflow-x-auto rounded-md bg-muted p-3 text-xs">
                  {call.observation}
                </pre>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
