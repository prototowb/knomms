export default defineEventHandler(async () => {
  try {
    const data = await $fetch<{ models: { name: string }[] }>('http://ollama:11434/api/tags')
    return { models: (data.models ?? []).map((m) => m.name) }
  } catch {
    return { models: [] }
  }
})
