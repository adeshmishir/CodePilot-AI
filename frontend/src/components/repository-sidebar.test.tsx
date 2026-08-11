import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RepositorySidebar } from "@/components/repository-sidebar"

const mocks = vi.hoisted(() => ({
  cloneRepository: vi.fn(),
  deleteRepository: vi.fn(),
  reindexRepository: vi.fn(),
  cloneError: null as { message: string; detail?: string } | null,
  deleteError: null as { message: string; detail?: string } | null,
}))

vi.mock("@/context/use-workspace", () => ({
  useWorkspace: () => ({
    repositories: [
      {
        id: 1,
        owner: "adeshmishir",
        name: "CoinOracle",
        clone_url: "https://github.com/adeshmishir/CoinOracle",
        local_path: "data/repos/adeshmishir/CoinOracle",
      },
    ],
    selectedId: 1,
    loadingRepositories: false,
    listError: null,
    cloning: false,
    cloneError: mocks.cloneError,
    deletingId: null,
    deleteError: mocks.deleteError,
    reindexingId: null,
    repoActionError: null,
    sidebarOpen: true,
    selectRepository: vi.fn(),
    cloneRepository: mocks.cloneRepository,
    deleteRepository: mocks.deleteRepository,
    reindexRepository: mocks.reindexRepository,
    refreshRepositories: vi.fn(),
    clearCloneError: vi.fn(),
    clearRepoActionError: vi.fn(),
  }),
}))

describe("RepositorySidebar", () => {
  beforeEach(() => {
    mocks.cloneError = null
    mocks.deleteError = null
    mocks.cloneRepository.mockReset()
    mocks.deleteRepository.mockReset()
    mocks.reindexRepository.mockReset()
  })

  it("shows the backend clone error message", () => {
    mocks.cloneError = {
      message:
        "GitHub reports that this repository does not exist, was renamed, or is not publicly accessible.",
      detail: "repository not found",
    }

    render(<RepositorySidebar />)

    expect(
      screen.getByText(
        "GitHub reports that this repository does not exist, was renamed, or is not publicly accessible.",
      ),
    ).toBeInTheDocument()
  })

  it("shows the clone authentication error message", () => {
    mocks.cloneError = {
      message:
        "Repository could not be cloned. GitHub authentication is missing or invalid, or the token does not have access to this repository.",
      detail: "fatal: Authentication failed",
    }

    render(<RepositorySidebar />)

    expect(
      screen.getByText(/Repository could not be cloned/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/GitHub authentication is missing or invalid/),
    ).toBeInTheDocument()
  })

  it("deletes a repository after confirming", async () => {
    const user = userEvent.setup()
    mocks.deleteRepository.mockResolvedValue(undefined)

    render(<RepositorySidebar />)

    await user.click(
      screen.getByRole("button", {
        name: "Delete adeshmishir/CoinOracle",
      }),
    )

    await user.click(
      screen.getByRole("button", {
        name: "Confirm delete adeshmishir/CoinOracle",
      }),
    )

    expect(mocks.deleteRepository).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1, name: "CoinOracle" }),
    )
  })

  it("reindexes a repository", async () => {
    const user = userEvent.setup()
    mocks.reindexRepository.mockResolvedValue(undefined)

    render(<RepositorySidebar />)

    await user.click(
      screen.getByRole("button", {
        name: "Reindex adeshmishir/CoinOracle",
      }),
    )

    expect(mocks.reindexRepository).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1 }),
    )
  })
})
