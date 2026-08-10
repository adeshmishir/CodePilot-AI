import { useEffect, useRef } from "react"

export function useRepositoryReset(
  repositoryId: number,
  reset: () => void,
) {
  const previousRef = useRef<number | null>(null)
  const initializedRef = useRef(false)

  useEffect(() => {
    if (initializedRef.current && previousRef.current !== repositoryId) {
      reset()
    }
    initializedRef.current = true
    previousRef.current = repositoryId
  }, [repositoryId, reset])
}
