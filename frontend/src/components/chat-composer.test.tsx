import { useState } from "react"

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ChatComposer } from "@/components/chat-composer"

function ControlledComposer({
  loading = false,
  onSubmit,
}: {
  loading?: boolean
  onSubmit: () => void
}) {
  const [value, setValue] = useState("")

  return (
    <ChatComposer
      value={value}
      onChange={setValue}
      onSubmit={onSubmit}
      loading={loading}
    />
  )
}

describe("ChatComposer", () => {
  it("submits on Enter", async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<ControlledComposer onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "hello{Enter}")

    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it("inserts a newline on Shift+Enter without submitting", async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<ControlledComposer onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "line1{Shift>}{Enter}{/Shift}")

    expect(textarea).toHaveValue("line1\n")
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("does not submit while loading", async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<ControlledComposer loading={true} onSubmit={onSubmit} />)

    const textarea = screen.getByLabelText("Message CodePilot")
    await user.type(textarea, "hello")
    await user.type(textarea, "{Enter}")

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
