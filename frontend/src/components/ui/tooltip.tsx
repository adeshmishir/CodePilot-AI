import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface TooltipProps {
  content: string
  children: ReactNode
  side?: "top" | "bottom"
  className?: string
}

export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: TooltipProps) {
  const positionStyle: React.CSSProperties =
    side === "top"
      ? { bottom: "calc(100% + 6px)" }
      : { top: "calc(100% + 6px)" }

  return (
    <span className={cn("group relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        style={positionStyle}
        className="bg-foreground text-background pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 rounded-md px-2 py-1 text-[11px] font-medium whitespace-nowrap opacity-0 shadow-sm transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {content}
      </span>
    </span>
  )
}
