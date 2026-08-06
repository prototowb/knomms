import { ofetch } from 'ofetch'

// KC-072: the compose page's model list now comes from the backend, which
// groups eval targets by provider (Ollama always; Anthropic only when the
// operator enabled cloud eval). Replaces the old direct Ollama-tags proxy.
export default defineEventHandler(async (event) => {
  const auth = getHeader(event, 'authorization') ?? ''
  try {
    return await ofetch<{ providers: { provider: string; models: string[] }[] }>(
      'http://api:8000/v1/eval-models',
      { headers: { Authorization: auth } }
    )
  } catch {
    return { providers: [{ provider: 'ollama', models: [] }] }
  }
})
