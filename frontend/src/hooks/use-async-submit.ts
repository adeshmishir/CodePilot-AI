import { useRef, useState } from "react"

import { formatApiError, type FormattedError } from "@/lib/error-format"

export function useAsyncSubmit<TArgs extends unknown[], TResult>(
  handler: (...args: TArgs) => Promise<TResult>,
) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<FormattedError | null>(null)
  const [result, setResult] = useState<TResult | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const requestRef = useRef(0)
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  const run = async (...args: TArgs) => {
    const requestId = ++requestRef.current
    setLoading(true)
    setError(null)
    try {
      const value = await handlerRef.current(...args)
      if (requestId !== requestRef.current) return null
      setResult(value)
      setSubmitted(true)
      return value
    } catch (caught) {
      if (requestId !== requestRef.current) return null
      setError(formatApiError(caught))
      return null
    } finally {
      if (requestId === requestRef.current) setLoading(false)
    }
  }

  const reset = () => {
    requestRef.current++
    setLoading(false)
    setError(null)
    setResult(null)
    setSubmitted(false)
  }

  return { loading, error, result, submitted, run, reset }
}
