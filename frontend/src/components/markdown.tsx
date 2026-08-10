"use client"

import { useMemo } from "react"
import type { ReactNode } from "react"

import { CopyButton } from "@/components/copy-button"
import { cn } from "@/lib/utils"

interface CodeBlockProps {
  code: string
  language?: string
  className?: string
}

export function CodeBlock({
  code,
  language,
  className,
}: CodeBlockProps) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-lg border bg-muted/50",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b px-3 py-1.5">
        <span className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
          {language || "code"}
        </span>
        <CopyButton text={code} label="Copy code" />
      </div>
      <pre className="max-h-80 overflow-x-auto overflow-y-auto p-3 text-xs leading-relaxed">
        <code className="font-mono">{code}</code>
      </pre>
    </div>
  )
}

interface InlinePattern {
  type: "code" | "link" | "bold" | "italic" | "strike"
  re: RegExp
}

const INLINE_PATTERNS: InlinePattern[] = [
  { type: "code", re: /`([^`\n]+)`/ },
  { type: "link", re: /\[([^\]]+)\]\(([^)\s]+)\)/ },
  { type: "bold", re: /\*\*([^*\n]+)\*\*/ },
  { type: "italic", re: /\*([^*\n]+)\*/ },
  { type: "strike", re: /~~([^~\n]+)~~/ },
]

function isSafeLink(href: string) {
  return (
    /^(https?:|mailto:)/i.test(href) ||
    href.startsWith("/") ||
    href.startsWith("#")
  )
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const out: ReactNode[] = []
  let rest = text
  let key = 0

  while (rest.length > 0) {
    let best: {
      type: InlinePattern["type"]
      match: RegExpExecArray
      start: number
      end: number
    } | null = null

    for (const pattern of INLINE_PATTERNS) {
      const match = pattern.re.exec(rest)
      if (match && (best === null || match.index < best.start)) {
        best = {
          type: pattern.type,
          match,
          start: match.index,
          end: match.index + match[0].length,
        }
      }
    }

    if (!best) {
      out.push(<span key={`${keyPrefix}-${key}`}>{rest}</span>)
      break
    }

    if (best.start > 0) {
      out.push(<span key={`${keyPrefix}-${key}`}>{rest.slice(0, best.start)}</span>)
      key++
    }

    const inner = best.match[1]
    const elementKey = `${keyPrefix}-${key}`

    switch (best.type) {
      case "code":
        out.push(
          <code
            key={elementKey}
            className="bg-muted text-foreground rounded border px-1 py-0.5 font-mono text-[0.9em]"
          >
            {inner}
          </code>,
        )
        break
      case "bold":
        out.push(
          <strong key={elementKey}>{renderInline(inner, elementKey)}</strong>,
        )
        break
      case "italic":
        out.push(<em key={elementKey}>{renderInline(inner, elementKey)}</em>)
        break
      case "strike":
        out.push(<del key={elementKey}>{renderInline(inner, elementKey)}</del>)
        break
      case "link": {
        const href = best.match[2]
        if (isSafeLink(href)) {
          out.push(
            <a
              key={elementKey}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary font-medium underline underline-offset-2 hover:text-primary/80"
            >
              {renderInline(inner, elementKey)}
            </a>,
          )
        } else {
          out.push(<span key={elementKey}>{inner}</span>)
        }
        break
      }
    }

    key++
    rest = rest.slice(best.end)
  }

  return out
}

const HEADING_STYLES: Record<string, string> = {
  h1: "text-base font-semibold",
  h2: "text-base font-semibold",
  h3: "text-sm font-semibold",
  h4: "text-sm font-semibold",
  h5: "text-sm font-semibold",
  h6: "text-sm font-semibold",
}

function parseBlocks(markdown: string): ReactNode[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n")
  const out: ReactNode[] = []
  let buffer: string[] = []
  let blockKey = 0

  const flushParagraph = () => {
    if (buffer.length === 0) return
    const first = buffer[0]

    const headingMatch = /^(#{1,6})\s+(.*)$/.exec(first)
    if (buffer.length === 1 && headingMatch) {
      const level = headingMatch[1].length
      const Tag = `h${level}` as "h1" | "h2" | "h3" | "h4" | "h5" | "h6"
      out.push(
        <Tag key={blockKey++} className={HEADING_STYLES[Tag]}>
          {renderInline(headingMatch[2], `h-${blockKey}`)}
        </Tag>,
      )
      buffer = []
      return
    }

    if (buffer.length === 1 && /^(\s*[-*_]\s*){3,}$/.test(first)) {
      out.push(<hr key={blockKey++} className="border-border my-1" />)
      buffer = []
      return
    }

    if (buffer.every((line) => line.startsWith(">"))) {
      const content = buffer
        .map((line) => line.replace(/^>\s?/, ""))
        .join("\n")
      out.push(
        <blockquote
          key={blockKey++}
          className="text-muted-foreground border-l-2 border-border pl-3"
        >
          <div className="whitespace-pre-wrap">
            {renderInline(content, `q-${blockKey}`)}
          </div>
        </blockquote>,
      )
      buffer = []
      return
    }

    const unordered = buffer.every((line) => /^\s*[-*+]\s+/.test(line))
    const ordered = buffer.every((line) => /^\s*\d+[.)]\s+/.test(line))
    if (unordered || ordered) {
      const items = buffer.map((line) =>
        line
          .replace(/^\s*[-*+]\s+/, "")
          .replace(/^\s*\d+[.)]\s+/, ""),
      )
      const ListTag = ordered ? "ol" : "ul"
      out.push(
        <ListTag
          key={blockKey++}
          className={cn(
            "flex flex-col gap-1 pl-5",
            ordered ? "list-decimal" : "list-disc",
          )}
        >
          {items.map((item, index) => (
            <li key={`${blockKey}-${index}`}>
              {renderInline(item, `li-${blockKey}-${index}`)}
            </li>
          ))}
        </ListTag>,
      )
      buffer = []
      return
    }

    out.push(
      <p key={blockKey++} className="whitespace-pre-wrap">
        {renderInline(buffer.join("\n"), `p-${blockKey}`)}
      </p>,
    )
    buffer = []
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    if (/^\s*```/.test(line)) {
      flushParagraph()
      const language = line.replace(/^\s*```\s*/, "").trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !/^\s*```/.test(lines[i])) {
        codeLines.push(lines[i])
        i++
      }
      i++
      const code = codeLines.join("\n").replace(/\s+$/, "")
      out.push(
        <CodeBlock key={blockKey++} code={code} language={language} />,
      )
      continue
    }

    if (line.trim() === "") {
      flushParagraph()
      i++
      continue
    }

    buffer.push(line)
    i++
  }

  flushParagraph()
  return out
}

export function Markdown({ children }: { children: string }) {
  const blocks = useMemo(() => parseBlocks(children), [children])
  return (
    <div className="space-y-3 text-sm leading-relaxed break-words">
      {blocks}
    </div>
  )
}
