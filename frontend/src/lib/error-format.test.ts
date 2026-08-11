import { describe, expect, it } from "vitest"

import { ApiClientError, TimeoutError } from "@/lib/api"
import { formatApiError } from "@/lib/error-format"

describe("formatApiError", () => {
  it("surfaces the backend message for 400 errors", () => {
    const caught = new ApiClientError(
      "GitHub reports that this repository does not exist, was renamed, or is not publicly accessible.",
      400,
      "repository not found",
    )

    const formatted = formatApiError(caught)

    expect(formatted.message).toBe(
      "GitHub reports that this repository does not exist, was renamed, or is not publicly accessible.",
    )
    expect(formatted.detail).toBe("repository not found")
  })

  it("uses the backend message for 404 errors", () => {
    const caught = new ApiClientError("Repository not found", 404)

    const formatted = formatApiError(caught)

    expect(formatted.message).toBe("Repository not found")
  })

  it("falls back to a generic message when only a status is available", () => {
    const caught = new ApiClientError("Request failed with status 400", 400)

    const formatted = formatApiError(caught)

    expect(formatted.message).toBe(
      "The request was invalid. Please adjust the input and try again.",
    )
  })

  it("keeps a generic message for 500 errors", () => {
    const caught = new ApiClientError(
      "Request failed with status 500",
      500,
      "Internal Server Error",
    )

    const formatted = formatApiError(caught)

    expect(formatted.message).toBe(
      "CodePilot backend encountered an error. Please try again.",
    )
    expect(formatted.detail).toBe("Internal Server Error")
  })

  it("keeps a generic message for 502/503 errors", () => {
    const caught = new ApiClientError("Request failed with status 503", 503)

    const formatted = formatApiError(caught)

    expect(formatted.message).toBe(
      "CodePilot backend is temporarily unavailable. Please try again shortly.",
    )
  })

  it("reports network failures for TypeErrors", () => {
    const formatted = formatApiError(new TypeError("Failed to fetch"))

    expect(formatted.message).toBe(
      "Unable to reach CodePilot backend. Please check your connection and try again.",
    )
  })

  it("reports timeouts", () => {
    const formatted = formatApiError(new TimeoutError(60_000))

    expect(formatted.message).toBe(
      "The request took too long and timed out. Please try again.",
    )
  })
})
