import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const auth = getHeader(event, 'authorization') ?? ''
  const query = getQuery(event)
  return ofetch('http://api:8000/v1/assets', {
    headers: { Authorization: auth },
    query,
  })
})
