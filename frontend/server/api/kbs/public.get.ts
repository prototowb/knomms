import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const query = getQuery(event)
  return ofetch<unknown>('http://api:8000/v1/kbs/public', { query })
})
