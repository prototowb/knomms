import { ofetch } from 'ofetch'

export default defineEventHandler(async () => {
  return ofetch<{ deprecated: string[] }>('http://api:8000/v1/deprecated-models').catch(() => ({ deprecated: [] }))
})
