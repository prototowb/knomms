import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const auth = getHeader(event, 'authorization') ?? ''
  const query = getQuery(event)
  return ofetch<unknown>('http://api:8000/v1/kbs/org', {
    headers: { Authorization: auth },
    query,
  })
})
