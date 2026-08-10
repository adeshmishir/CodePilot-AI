import { ApiClientError, TimeoutError } from "@/lib/api"

export interface FormattedError {
  message: string
  detail?: string
}

export function formatApiError(caught: unknown): FormattedError {
  if (caught instanceof ApiClientError) {
    const detail = caught.message
    switch (caught.status) {
      case 404:
        return {
          message: "The requested repository could not be found.",
          detail,
        }
      case 400:
        return {
          message: "The request was invalid. Please adjust the input and try again.",
          detail,
        }
      case 401:
      case 403:
        return {
          message: "You are not authorized to access the CodePilot backend.",
          detail,
        }
      case 408:
        return {
          message: "The request timed out. Please try again.",
          detail,
        }
      case 502:
      case 503:
        return {
          message:
            "CodePilot backend is temporarily unavailable. Please try again shortly.",
          detail,
        }
      case 500:
        return {
          message: "CodePilot backend encountered an error. Please try again.",
          detail,
        }
      default:
        return {
          message: `The request failed (${caught.status}). Please try again.`,
          detail,
        }
    }
  }

  if (caught instanceof TimeoutError) {
    return {
      message: "The request took too long and timed out. Please try again.",
      detail: caught.message,
    }
  }

  if (caught instanceof TypeError) {
    return {
      message:
        "Unable to reach CodePilot backend. Please check your connection and try again.",
      detail: String(caught.message),
    }
  }

  return {
    message: "Something went wrong. Please try again.",
    detail: caught instanceof Error ? caught.message : String(caught),
  }
}
