import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiClient, ApiClientError } from "@/lib/api"

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response
}

describe("ApiClient", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("deletes a repository with a DELETE request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ success: true, message: "Repository deleted." }),
    )
    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    const result = await client.deleteRepository(42)

    expect(fetchMock).toHaveBeenCalledWith(
      "https://backend.example.com/repositories/42",
      expect.objectContaining({ method: "DELETE" }),
    )
    expect(result).toEqual({
      success: true,
      message: "Repository deleted.",
    })
  })

  it("prefers the backend message over detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            success: false,
            message: "Repository could not be cloned.",
            detail: "repository not found",
          },
          400,
        ),
      ),
    )

    const client = new ApiClient("https://backend.example.com")

    await expect(
      client.cloneRepository({ url: "https://github.com/owner/nope" }),
    ).rejects.toMatchObject({
      status: 400,
      message: "Repository could not be cloned.",
      detail: "repository not found",
    })
  })

  it("falls back to detail when no message is present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "Repository not found" }, 404),
      ),
    )

    const client = new ApiClient("https://backend.example.com")

    await expect(client.listRepositories()).rejects.toMatchObject({
      status: 404,
      message: "Repository not found",
    })
  })

  it("throws a status-based error when the body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("invalid json")),
      } as Response),
    )

    const client = new ApiClient("https://backend.example.com")

    await expect(client.health()).rejects.toMatchObject({
      status: 500,
      message: "Request failed with status 500",
    })
  })

  it("surfaces a typed ApiClientError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ message: "boom" }, 400)),
    )

    const client = new ApiClient("https://backend.example.com")

    try {
      await client.health()
      expect.unreachable()
    } catch (caught) {
      expect(caught).toBeInstanceOf(ApiClientError)
    }
  })
})
