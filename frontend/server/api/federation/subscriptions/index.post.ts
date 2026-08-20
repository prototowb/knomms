import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return ofetch('http://api:8000/v1/federation/subscriptions', {
    method: 'POST',
    headers: { Authorization: auth },
    body,
  })
})
