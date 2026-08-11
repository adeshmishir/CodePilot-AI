import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { RepositorySidebar } from "@/components/repository-sidebar"

const mocks = vi.hoisted(() => ({
  cloneRepository: vi.fn(),
  cancelClone: vi.fn(),
  deleteRepository: vi.fn(),
  reindexRepository: vi.fn(),
  cloneError: null as { message: string; detail?: string } | null,
  deleteError: null as { message: string; detail?: string } | null,
  cloneProgress: null as {
    jobId: string
    phase: string
    percent: number
    filesDone: number
    filesTotal: number
  } | null,
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
    cloneProgress: mocks.cloneProgress,
    deletingId: null,
    deleteError: mocks.deleteError,
    reindexingId: null,
    repoActionError: null,
    sidebarOpen: true,
    selectRepository: vi.fn(),
    cloneRepository: mocks.cloneRepository,
    cancelClone: mocks.cancelClone,
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
    mocks.cloneProgress = null
    mocks.cloneRepository.mockReset()
    mocks.cancelClone.mockReset()
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

  it("shows clone progress while a job is running", () => {
    mocks.cloneProgress = {
      jobId: "adeshmishir/CoinOracle",
      phase: "indexing",
      percent: 42,
      filesDone: 420,
      filesTotal: 1000,
    }

    render(<RepositorySidebar />)

    expect(screen.getByText("Indexing files…")).toBeInTheDocument()
    expect(screen.getByText("42%")).toBeInTheDocument()
    expect(screen.getByText(/420/)).toBeInTheDocument()
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "42",
    )
  })

  it("shows the cloning phase while cloning", () => {
    mocks.cloneProgress = {
      jobId: "adeshmishir/CoinOracle",
      phase: "cloning",
      percent: 0,
      filesDone: 0,
      filesTotal: 0,
    }

    render(<RepositorySidebar />)

    expect(screen.getByText("Cloning repository…")).toBeInTheDocument()
  })

  it("cancels a running clone job", async () => {
    const user = userEvent.setup()
    mocks.cloneProgress = {
      jobId: "adeshmishir/CoinOracle",
      phase: "indexing",
      percent: 30,
      filesDone: 30,
      filesTotal: 100,
    }

    render(<RepositorySidebar />)

    await user.click(
      screen.getByRole("button", { name: "Cancel clone" }),
    )

    expect(mocks.cancelClone).toHaveBeenCalledTimes(1)
  })
})
