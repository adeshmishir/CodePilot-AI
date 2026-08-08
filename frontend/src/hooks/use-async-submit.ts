import { useState } from "react"

export function useAsyncSubmit<TArgs extends unknown[], TResult>(
  handler: (...args: TArgs) => Promise<TResult>,
) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TResult | null>(null)

  const run = async (...args: TArgs) => {
    setLoading(true)
    setError(null)
    try {
      const value = await handler(...args)
      setResult(value)
      return value
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Request failed",
      )
      return null
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setLoading(false)
    setError(null)
    setResult(null)
  }

  return { loading, error, result, run, reset }
}
