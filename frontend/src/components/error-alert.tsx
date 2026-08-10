"use client"

import { AlertCircle } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { FormattedError } from "@/lib/error-format"

interface ErrorAlertProps {
  error: FormattedError | null
  onRetry?: () => void
  retryLabel?: string
  className?: string
}

export function ErrorAlert({
  error,
  onRetry,
  retryLabel = "Try again",
  className,
}: ErrorAlertProps) {
  if (!error) return null

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <p className="text-destructive">{error.message}</p>
        </div>
        {onRetry && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="shrink-0"
          >
            {retryLabel}
          </Button>
        )}
      </div>
      {error.detail && (
        <details className="text-muted-foreground text-xs">
          <summary className="cursor-pointer select-none">
            Technical details
          </summary>
          <pre className="border-border mt-2 max-h-32 overflow-auto rounded-md border bg-background/60 p-2 font-mono whitespace-pre-wrap">
            {error.detail}
          </pre>
        </details>
      )}
    </div>
  )
}
