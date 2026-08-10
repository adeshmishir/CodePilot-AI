"use client"

import { useEffect, useRef } from "react"

import { FolderGit2, Paperclip, Send, X } from "lucide-react"

import { Tooltip } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

const MAX_HEIGHT = 160

interface ChatComposerProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  loading: boolean
  placeholder?: string
  repositoryLabel?: string
  disabled?: boolean
}

export function ChatComposer({
  value,
  onChange,
  onSubmit,
  loading,
  placeholder = "Ask a question about this repository…",
  repositoryLabel,
  disabled = false,
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resize = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "0px"
    const next = Math.min(el.scrollHeight, MAX_HEIGHT)
    el.style.height = `${next}px`
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? "auto" : "hidden"
  }

  useEffect(() => {
    resize()
  }, [value])

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      onSubmit()
    }
  }

  const canSend = !loading && value.trim().length > 0 && !disabled

  return (
    <div className="px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-4">
      <div className="mx-auto w-full max-w-3xl">
        <div
          className={cn(
            "bg-card flex items-end gap-1.5 rounded-xl border p-2 shadow-sm transition-colors",
            "focus-within:border-ring focus-within:ring-ring/30 focus-within:ring-[3px]",
          )}
        >
          <Tooltip content="Attachments are not supported yet">
            <button
              type="button"
              disabled
              aria-label="Attach file (not supported)"
              className="text-muted-foreground hover:text-foreground focus-visible:ring-ring flex size-9 shrink-0 cursor-not-allowed items-center justify-center rounded-lg opacity-40 outline-none focus-visible:ring-2"
            >
              <Paperclip className="size-4" />
            </button>
          </Tooltip>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            autoFocus
            placeholder={placeholder}
            aria-label="Message CodePilot"
            aria-describedby="chat-composer-hint"
            disabled={disabled}
            className="placeholder:text-muted-foreground text-foreground max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-relaxed outline-none disabled:cursor-not-allowed disabled:opacity-50"
            style={{ overflowY: "hidden" }}
          />

          {value.length > 0 && (
            <Tooltip content="Clear input">
              <button
                type="button"
                onClick={() => onChange("")}
                aria-label="Clear input"
                className="text-muted-foreground hover:text-foreground focus-visible:ring-ring flex size-9 shrink-0 items-center justify-center rounded-lg outline-none hover:bg-accent focus-visible:ring-2"
              >
                <X className="size-4" />
              </button>
            </Tooltip>
          )}

          <Tooltip
            content={loading ? "CodePilot is responding" : "Send message (Enter)"}
          >
            <button
              type="button"
              onClick={onSubmit}
              disabled={!canSend}
              aria-label={loading ? "CodePilot is responding" : "Send message"}
              className={cn(
                "bg-primary text-primary-foreground flex size-9 shrink-0 items-center justify-center rounded-lg outline-none transition-colors",
                "hover:bg-primary/90 focus-visible:ring-ring focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50",
              )}
            >
              {loading ? (
                <span className="flex size-4 items-center justify-center">
                  <span className="bg-primary-foreground size-1.5 animate-pulse rounded-full" />
                </span>
              ) : (
                <Send className="size-4" />
              )}
            </button>
          </Tooltip>
        </div>

        <div
          id="chat-composer-hint"
          className="text-muted-foreground mt-1.5 flex flex-wrap items-center justify-between gap-x-3 gap-y-1 px-1 text-[11px]"
        >
          {repositoryLabel ? (
            <span className="font-mono flex min-w-0 items-center gap-1">
              <FolderGit2 className="size-3 shrink-0" />
              <span className="truncate">{repositoryLabel}</span>
            </span>
          ) : (
            <span />
          )}
          <span className="shrink-0">
            Enter to send · Shift+Enter for a new line
          </span>
        </div>
      </div>
    </div>
  )
}
