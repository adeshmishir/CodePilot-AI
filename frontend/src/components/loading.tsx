import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("size-4 animate-spin", className)} />
}

export function LoadingText({
  label = "Loading",
  className,
}: {
  label?: string
  className?: string
}) {
  return (
    <div className={cn("text-muted-foreground flex items-center gap-2 text-sm", className)}>
      <Spinner className="size-3.5" />
      <span>{label}</span>
    </div>
  )
}

export function TypingIndicator({
  label = "CodePilot is thinking",
}: {
  label?: string
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>{label}</span>
      <span className="flex items-center gap-0.5">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="bg-muted-foreground size-1 animate-bounce rounded-full"
            style={{ animationDelay: `${dot * 150}ms` }}
          />
        ))}
      </span>
    </div>
  )
}
