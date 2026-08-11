import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ChatTab } from "@/components/chat-tab"

const chatMock = vi.hoisted(() => vi.fn())

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return {
    ...actual,
    apiClient: { ...actual.apiClient, chat: chatMock },
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

describe("ChatTab", () => {
  beforeEach(() => {
    chatMock.mockReset()
  })

  it("clears the input and appends the user message on send", async () => {
    const user = userEvent.setup()
    chatMock.mockResolvedValue({ answer: "Here is the answer.", sources: [] })

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "What is authentication?{Enter}")

    expect(textarea).toHaveValue("")

    expect(screen.getByText("What is authentication?")).toBeInTheDocument()

    expect(chatMock).toHaveBeenCalledWith(1, {
      query: "What is authentication?",
      limit: 5,
    })
  })

  it("renders the assistant response", async () => {
    const user = userEvent.setup()
    chatMock.mockResolvedValue({ answer: "Here is the answer.", sources: [] })

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "How does login work?{Enter}")

    expect(
      await screen.findByText("Here is the answer."),
    ).toBeInTheDocument()
  })

  it("does not send empty or whitespace-only input", async () => {
    const user = userEvent.setup()

    render(<ChatTab repositoryId={1} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "   {Enter}")

    expect(chatMock).not.toHaveBeenCalled()
  })
})
