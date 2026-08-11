import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ChatTab } from "@/components/chat-tab"
import type { ChatSource } from "@/types/api"

const streamChatMock = vi.hoisted(() => vi.fn())

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return {
    ...actual,
    apiClient: { ...actual.apiClient, streamChat: streamChatMock },
  }
})

vi.mock("@/context/use-workspace", () => ({
  useWorkspace: () => ({
    selected: {
      id: 1,
      owner: "adeshmishir",
      name: "CoinOracle",
      clone_url: "https://github.com/adeshmishir/CoinOracle",
      local_path: "data/repos/adeshmishir/CoinOracle",
    },
  }),
}))

function streamAnswer(
  answer: string,
  sources: ChatSource[] = [],
) {
  return async (
    _repositoryId: number,
    _request: unknown,
    callbacks?: {
      onDelta?: (text: string) => void
      onSources?: (sources: ChatSource[]) => void
    },
  ) => {
    callbacks?.onSources?.(sources)
    callbacks?.onDelta?.(answer)
    return { answer, sources }
  }
}

describe("ChatTab", () => {
  beforeEach(() => {
    streamChatMock.mockReset()
  })

  it("clears the input and appends the user message on send", async () => {
    const user = userEvent.setup()
    streamChatMock.mockImplementation(streamAnswer("Here is the answer."))

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "What is authentication?{Enter}")

    expect(textarea).toHaveValue("")

    expect(screen.getByText("What is authentication?")).toBeInTheDocument()

    expect(streamChatMock).toHaveBeenCalledWith(
      1,
      { query: "What is authentication?", limit: 5 },
      expect.any(Object),
    )
  })

  it("renders the assistant response", async () => {
    const user = userEvent.setup()
    streamChatMock.mockImplementation(streamAnswer("Here is the answer."))

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "How does login work?{Enter}")

    expect(
      await screen.findByText("Here is the answer."),
    ).toBeInTheDocument()
  })

  it("renders the answer progressively as it streams", async () => {
    const user = userEvent.setup()

    let resolveStream!: (value: {
      answer: string
      sources: ChatSource[]
    }) => void

    streamChatMock.mockImplementation(
      async (_id, _request, callbacks) => {
        callbacks?.onDelta?.("Part one ")
        callbacks?.onDelta?.("part two.")
        return new Promise((resolve) => {
          resolveStream = resolve
        })
      },
    )

    render(<ChatTab repositoryId={1} />)

    await user.type(screen.getByLabelText("Message CodePilot"), "hi{Enter}")

    expect(await screen.findByText(/Part one/)).toBeInTheDocument()
    expect(screen.getByText(/part two./)).toBeInTheDocument()

    resolveStream({ answer: "Part one part two.", sources: [] })
  })

  it("shows sources only after clicking the sources toggle", async () => {
    const user = userEvent.setup()

    streamChatMock.mockImplementation(
      streamAnswer("Check the auth service.", [
        {
          file_path: "src/auth/service.js",
          symbol_name: "authenticateUser",
          start_line: 42,
          end_line: 71,
          score: 0.82,
        },
      ]),
    )

    render(<ChatTab repositoryId={1} />)

    await user.type(screen.getByLabelText("Message CodePilot"), "auth?{Enter}")

    const toggle = await screen.findByRole("button", {
      name: "Sources (1)",
    })

    expect(
      screen.queryByText(/src\/auth\/service\.js/),
    ).not.toBeInTheDocument()

    await user.click(toggle)

    expect(
      screen.getByText(/src\/auth\/service\.js/),
    ).toBeInTheDocument()
    expect(screen.getByText("L42–71")).toBeInTheDocument()
  })

  it("does not send empty or whitespace-only input", async () => {
    const user = userEvent.setup()

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "   {Enter}")

    expect(streamChatMock).not.toHaveBeenCalled()
  })
})
