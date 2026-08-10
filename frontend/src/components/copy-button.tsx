"use client"

import { useEffect, useRef, useState } from "react"

import { Check, Copy } from "lucide-react"

import { cn, copyText } from "@/lib/utils"

interface CopyButtonProps {
  text: string
  label?: string
  className?: string
  showLabel?: boolean
}

export function CopyButton({
  text,
  label = "Copy to clipboard",
  className,
  showLabel = false,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    }
  }, [])

  const handleCopy = async () => {
    const ok = await copyText(text)
    if (!ok) return
    setCopied(true)
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      aria-label={copied ? "Copied" : label}
      title={label}
      className={cn(
        "text-muted-foreground inline-flex h-7 items-center gap-1 rounded-md px-1.5 text-xs transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      {copied ? (
        <Check className="size-3.5 text-emerald-500" />
      ) : (
        <Copy className="size-3.5" />
      )}
      {showLabel && <span>{copied ? "Copied" : "Copy"}</span>}
    </button>
  )
}
