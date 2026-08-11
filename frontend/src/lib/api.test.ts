import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiClient, ApiClientError } from "@/lib/api"
import type { ChatSource } from "@/types/api"

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response
}

function sseResponse(body: string, status = 200) {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body))
      controller.close()
    },
  })
  return {
    ok: status >= 200 && status < 300,
    status,
    body: stream,
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

  it("retries once on a 502 before succeeding", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ message: "bad gateway" }, 502))
      .mockResolvedValueOnce(
        jsonResponse({ repositories: [] }),
      )

    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    const result = await client.listRepositories()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result).toEqual({ repositories: [] })
  })

  it("retries once on a 503 before succeeding", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ message: "unavailable" }, 503))
      .mockResolvedValueOnce(jsonResponse({ status: "healthy" }))

    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    const result = await client.health()

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result).toEqual({ status: "healthy" })
  })

  it("throws the 502 error after exhausting retries", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ message: "bad gateway" }, 502))

    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    await expect(client.health()).rejects.toMatchObject({
      status: 502,
      message: "bad gateway",
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("does not retry on 500", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ message: "boom" }, 500))

    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    await expect(client.health()).rejects.toMatchObject({
      status: 500,
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("fetches clone job status", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        job_id: "owner/repo",
        status: "running",
        phase: "indexing",
        files_done: 5,
        files_total: 10,
        message: "",
        error: "",
        repository_id: null,
      }),
    )
    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    const result = await client.getCloneStatus("owner/repo")

    expect(fetchMock).toHaveBeenCalledWith(
      "https://backend.example.com/repositories/clone/status/owner/repo",
      expect.objectContaining({ method: "GET" }),
    )
    expect(result).toEqual({
      job_id: "owner/repo",
      status: "running",
      phase: "indexing",
      files_done: 5,
      files_total: 10,
      message: "",
      error: "",
      repository_id: null,
    })
  })

  it("cancels a running clone job", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ success: true, message: "Clone cancelled." }),
    )
    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    const result = await client.cancelCloneJob("owner/repo")

    expect(fetchMock).toHaveBeenCalledWith(
      "https://backend.example.com/repositories/clone/cancel/owner/repo",
      expect.objectContaining({ method: "POST" }),
    )
    expect(result).toEqual({
      success: true,
      message: "Clone cancelled.",
    })
  })

  it("streams chat deltas and sources from the SSE endpoint", async () => {
    const events = [
      'data: {"type":"sources","sources":[{"file_path":"src/a.js","symbol_name":"foo","start_line":1,"end_line":2,"score":0.9}]}',
      'data: {"type":"delta","text":"Hello "}',
      'data: {"type":"delta","text":"world."}',
      'data: {"type":"done","message":""}',
    ].join("\n\n") + "\n\n"
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(events))
    vi.stubGlobal("fetch", fetchMock)

    const deltas: string[] = []
    let sources: ChatSource[] = []
    const client = new ApiClient("https://backend.example.com")

    const result = await client.streamChat(
      1,
      { query: "hi", limit: 5 },
      {
        onDelta: (text) => deltas.push(text),
        onSources: (next) => {
          sources = next
        },
      },
    )

    expect(fetchMock).toHaveBeenCalledWith(
      "https://backend.example.com/api/repositories/1/chat/stream",
      expect.objectContaining({ method: "POST" }),
    )
    expect(deltas).toEqual(["Hello ", "world."])
    expect(sources).toEqual([
      {
        file_path: "src/a.js",
        symbol_name: "foo",
        start_line: 1,
        end_line: 2,
        score: 0.9,
      },
    ])
    expect(result).toEqual({
      answer: "Hello world.",
      sources,
    })
  })

  it("throws when the streamed chat endpoint returns an error event", async () => {
    const events =
      'data: {"type":"error","detail":"Unable to generate an answer at this time."}\n\n'
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(events))
    vi.stubGlobal("fetch", fetchMock)

    const client = new ApiClient("https://backend.example.com")

    await expect(
      client.streamChat(1, { query: "hi", limit: 5 }),
    ).rejects.toMatchObject({
      status: 500,
      message: "Unable to generate an answer at this time.",
    })
  })
})
