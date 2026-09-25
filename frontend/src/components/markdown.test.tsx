import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Markdown } from "@/components/markdown"

describe("Markdown", () => {
  it("renders heading hierarchy", () => {
    render(<Markdown>{"# Title\n\n## Section\n\nBody text"}</Markdown>)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Title",
    )
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      "Section",
    )
  })

  it("renders unordered and ordered lists", () => {
    render(
      <Markdown>{"- one\n- two\n\n1. first\n2. second"}</Markdown>,
    )
    const listItems = screen.getAllByRole("listitem")
    expect(listItems).toHaveLength(4)
    expect(screen.getAllByRole("list")).toHaveLength(2)
  })

  it("renders inline code", () => {
    render(<Markdown>{"Open `src/main.py` to continue."}</Markdown>)
    expect(screen.getByText("src/main.py")).toBeInTheDocument()
  })

  it("renders a fenced code block with its language label", () => {
    render(<Markdown>{"```ts\nconst x = 1\n```"}</Markdown>)
    expect(screen.getByText("const x = 1")).toBeInTheDocument()
    expect(screen.getByText("ts")).toBeInTheDocument()
  })

  it("renders a markdown table", () => {
    const md = [
      "| Layer | Tech |",
      "| --- | --- |",
      "| Frontend | React + Vite |",
      "| Backend | FastAPI |",
    ].join("\n")
    render(<Markdown>{md}</Markdown>)
    expect(screen.getByRole("table")).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Layer" })).toBeInTheDocument()
    expect(
      screen.getByRole("cell", { name: "React + Vite" }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("cell", { name: "FastAPI" }),
    ).toBeInTheDocument()
  })

  it("renders blockquote and bold text", () => {
    render(
      <Markdown>{"> Note: important\n\nThis uses **bold** emphasis."}</Markdown>,
    )
    expect(screen.getByRole("blockquote")).toBeInTheDocument()
    expect(screen.getByText("bold")).toBeInTheDocument()
  })
})