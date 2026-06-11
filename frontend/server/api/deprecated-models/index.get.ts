export default defineEventHandler(async () => {
  return $fetch<{ deprecated: string[] }>('http://api:8000/v1/deprecated-models').catch(() => ({ deprecated: [] }))
})
