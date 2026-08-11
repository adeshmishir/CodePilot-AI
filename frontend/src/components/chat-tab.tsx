"use client"

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"

import { ArrowDown, Bot, FileText, Trash2 } from "lucide-react"

import { ChatComposer } from "@/components/chat-composer"
import { CopyButton } from "@/components/copy-button"
import { ErrorAlert } from "@/components/error-alert"
import { Markdown } from "@/components/markdown"
import { TypingIndicator } from "@/components/loading"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useWorkspace } from "@/context/use-workspace"
import { useAsyncSubmit } from "@/hooks/use-async-submit"
import { apiClient } from "@/lib/api"
import type { ChatSource } from "@/types/api"

interface ChatMessage {
  id: number
  role: "user" | "assistant"
  content: string
  sources?: ChatSource[]
}

interface ChatTabProps {
  repositoryId: number
}

const NEAR_BOTTOM_OFFSET = 100

function scrollToTopOf(el: HTMLElement) {
  if (typeof el.scrollIntoView !== "function") return
  try {
    el.scrollIntoView({ block: "start", inline: "nearest" })
  } catch {
    // no-op in test environments that do not implement scrolling
  }
}

function scrollContainerToBottom(el: HTMLElement) {
  if (typeof el.scrollTo === "function") {
    try {
      el.scrollTo({ top: el.scrollHeight, behavior: "auto" })
      return
    } catch {
      // fall through to scrollTop assignment
    }
  }
  el.scrollTop = el.scrollHeight
}

export function ChatTab({ repositoryId }: ChatTabProps) {
  const { selected } = useWorkspace()
  const [query, setQuery] = useState("")
  const [histories, setHistories] = useState<Record<number, ChatMessage[]>>({})
  const idRef = useRef(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const messageRefs = useRef<Record<number, HTMLDivElement | null>>({})
  const nearBottomRef = useRef(true)
  const sendingRef = useRef(false)
  const pendingScrollBottomRef = useRef(false)
  const [showJump, setShowJump] = useState(false)
  const previousRepoRef = useRef<number | null>(null)

  const { loading, error, run, reset } = useAsyncSubmit(
    (q: string) => apiClient.chat(repositoryId, { query: q, limit: 5 }),
  )

  useEffect(() => {
    if (
      previousRepoRef.current !== null &&
      previousRepoRef.current !== repositoryId
    ) {
      reset()
      sendingRef.current = false
      setShowJump(false)
      nearBottomRef.current = true
    }
    previousRepoRef.current = repositoryId
  }, [repositoryId, reset])

  const messages = useMemo(
    () => histories[repositoryId] ?? [],
    [histories, repositoryId],
  )
  const repositoryLabel = selected
    ? `${selected.owner}/${selected.name}`
    : undefined

  const updateMessages = (
    updater: (messages: ChatMessage[]) => ChatMessage[],
  ) => {
    setHistories((prev) => ({
      ...prev,
      [repositoryId]: updater(prev[repositoryId] ?? []),
    }))
  }

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior })
    nearBottomRef.current = true
    setShowJump(false)
  }

  useEffect(() => {
    const el = scrollRef.current
    if (!el || !nearBottomRef.current) return
    el.scrollTop = el.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    if (messages.length === 0) return
    const last = messages[messages.length - 1]
    if (
      last.role === "assistant" &&
      last.content.length > 0 &&
      !nearBottomRef.current
    ) {
      setShowJump(true)
    }
  }, [messages])

  const lastAssistantId = useMemo(() => {
    if (messages.length === 0) return null
    const last = messages[messages.length - 1]
    return last.role === "assistant" ? last.id : null
  }, [messages])

  useLayoutEffect(() => {
    if (!pendingScrollBottomRef.current) return
    pendingScrollBottomRef.current = false
    const el = scrollRef.current
    if (!el) return
    scrollContainerToBottom(el)
    setShowJump(false)
  }, [messages])

  useLayoutEffect(() => {
    if (lastAssistantId == null || !nearBottomRef.current) return
    const el = messageRefs.current[lastAssistantId]
    if (!el) return
    scrollToTopOf(el)
    setShowJump(false)
  }, [lastAssistantId])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const near =
      el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_OFFSET
    nearBottomRef.current = near
    if (near) setShowJump(false)
  }

  const handleSend = () => {
    const text = query.trim()
    if (!text || loading || sendingRef.current) return

    sendingRef.current = true
    updateMessages((current) => [
      ...current,
      { id: ++idRef.current, role: "user", content: text },
    ])
    setQuery("")
    nearBottomRef.current = true
    pendingScrollBottomRef.current = true

    void run(text).then((result) => {
      sendingRef.current = false
      if (!result) return
      updateMessages((current) => [
        ...current,
        {
          id: ++idRef.current,
          role: "assistant",
          content: result.answer,
          sources: result.sources,
        },
      ])
    })
  }

  const handleRetry = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user")
    if (!lastUser || sendingRef.current) return
    sendingRef.current = true
    void run(lastUser.content).then(() => {
      sendingRef.current = false
    })
  }

  const handleClear = () => {
    setHistories((prev) => ({ ...prev, [repositoryId]: [] }))
    setQuery("")
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b px-4 py-2.5 sm:px-6">
        <div className="flex min-w-0 items-center gap-2">
          <Bot className="text-muted-foreground size-4 shrink-0" />
          <h2 className="text-sm font-semibold">Chat</h2>
          {repositoryLabel && (
            <Badge variant="secondary" className="font-mono max-w-44 truncate">
              {repositoryLabel}
            </Badge>
          )}
        </div>
        {messages.length > 0 && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            aria-label="Clear conversation"
            title="Clear conversation"
          >
            <Trash2 className="size-4" />
            <span className="hidden sm:inline">Clear</span>
          </Button>
        )}
      </header>

      <div className="relative min-h-0 flex-1">
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto px-4 py-4 sm:px-6"
        >
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
            {messages.length === 0 && !loading && (
              <EmptyChatState />
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                ref={(el) => {
                  messageRefs.current[message.id] = el
                }}
              >
                <ChatMessageView message={message} />
              </div>
            ))}

            {loading && (
              <div className="flex items-start gap-3">
                <span className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full">
                  <Bot className="size-4" />
                </span>
                <div className="bg-card rounded-xl border px-4 py-3">
                  <TypingIndicator />
                </div>
              </div>
            )}
          </div>
        </div>

        {showJump && (
          <button
            type="button"
            onClick={() => scrollToBottom("smooth")}
            aria-label="Scroll to latest response"
            className="bg-primary text-primary-foreground absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium shadow-sm transition-opacity hover:bg-primary/90"
          >
            <ArrowDown className="size-3.5" />
            New response
          </button>
        )}
      </div>

      {error && (
        <div className="mx-auto w-full max-w-3xl px-4 pb-1 sm:px-6">
          <ErrorAlert error={error} onRetry={handleRetry} />
        </div>
      )}

      <ChatComposer
        value={query}
        onChange={setQuery}
        onSubmit={handleSend}
        loading={loading}
        repositoryLabel={repositoryLabel}
      />
    </div>
  )
}

function EmptyChatState() {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <div className="bg-primary/10 flex size-12 items-center justify-center rounded-full">
        <Bot className="text-primary size-6" />
      </div>
      <p className="text-sm font-medium">Ask CodePilot about this repository</p>
      <p className="text-muted-foreground max-w-sm text-xs">
        Ask about architecture, code flows, potential bugs, or how to
        implement something. Answers cite the files they are based on.
      </p>
    </div>
  )
}

function ChatMessageView({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="bg-primary text-primary-foreground max-w-[85%] rounded-2xl rounded-br-sm px-4 py-2.5 text-sm">
          <p className="break-words whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <span className="bg-primary text-primary-foreground flex size-8 shrink-0 items-center justify-center rounded-full">
        <Bot className="size-4" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-muted-foreground text-xs font-semibold">
            CodePilot
          </span>
          <CopyButton text={message.content} label="Copy response" />
        </div>
        <div className="mt-1.5">
          <Markdown>{message.content}</Markdown>
        </div>
        {message.sources && message.sources.length > 0 && (
          <SourcesList sources={message.sources} />
        )}
      </div>
    </div>
  )
}

function SourcesList({ sources }: { sources: ChatSource[] }) {
  return (
    <div className="mt-4 flex flex-col gap-2">
      <span className="text-muted-foreground text-[11px] font-medium tracking-wide uppercase">
        Sources
      </span>
      <div className="flex flex-col gap-1.5">
        {sources.map((source, index) => (
          <div
            key={index}
            className="border-border bg-muted/40 flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs"
          >
            <FileText className="text-muted-foreground size-3.5 shrink-0" />
            <span className="font-mono min-w-0 flex-1 truncate">
              {source.file_path}
              {source.symbol_name ? ` · ${source.symbol_name}` : ""}
            </span>
            <span className="text-muted-foreground shrink-0">
              L{source.start_line}–{source.end_line}
            </span>
            <Badge variant="secondary" className="shrink-0">
              {source.score.toFixed(3)}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  )
}
