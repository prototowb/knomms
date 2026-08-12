import { ref, type Ref } from 'vue'

interface StreamingQueryResult {
  response: Ref<string>
  citations: Ref<Record<string, any>>
  isStreaming: Ref<boolean>
  error: Ref<string | null>
  submit: (query: string, sourceIds?: string[]) => Promise<void>
}

/** Streams a grounded generation over the shared SSE contract.
 *  endpoint 'query' = single-hop Q&A; 'synthesize' = multi-source comparison
 *  (pass sourceIds to submit) — the events are byte-identical (docs/16, OQ-67). */
export function useStreamingQuery(
  kbId: string,
  endpoint: 'query' | 'synthesize' = 'query',
): StreamingQueryResult {
  const response = ref('')
  const citations = ref<Record<string, any>>({})
  const isStreaming = ref(false)
  const error = ref<string | null>(null)

  async function submit(query: string, sourceIds?: string[]): Promise<void> {
    const auth = useAuthStore()
    response.value = ''
    citations.value = {}
    error.value = null
    isStreaming.value = true

    const body = endpoint === 'synthesize'
      ? { question: query, source_ids: sourceIds ?? [] }
      : { query }

    try {
      const res = await fetch(`/api/kb/${kbId}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        throw new Error(`Request failed: ${res.status} ${res.statusText}`)
      }
      if (!res.body) {
        throw new Error('Response body is null — streaming not supported')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE events are separated by double newlines
        const events = buffer.split('\n\n')
        // Keep the last (potentially incomplete) chunk in the buffer
        buffer = events.pop() ?? ''

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue

          // Parse SSE fields from the event block
          const lines = rawEvent.split('\n')
          let eventType = 'message'
          let data = ''

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice('event:'.length).trim()
            } else if (line.startsWith('data:')) {
              // SSE spec: strip exactly one leading space after 'data:'.
              // .trim() would eat spaces that are part of the token value itself,
              // causing words to run together in streamed Ollama responses.
              const raw = line.slice('data:'.length)
              data = raw.startsWith(' ') ? raw.slice(1) : raw
            }
          }

          if (!data) continue

          if (eventType === 'citations') {
            try {
              citations.value = JSON.parse(data) as Record<string, any>
            } catch {
              // malformed citations payload — skip
            }
          } else {
            // Default: token stream — append to response
            response.value += data
          }
        }
      }
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : 'An unknown error occurred'
    } finally {
      isStreaming.value = false
    }
  }

  return { response, citations, isStreaming, error, submit }
}
