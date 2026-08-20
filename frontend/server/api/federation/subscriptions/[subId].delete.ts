import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const subId = getRouterParam(event, 'subId')
  const auth = getHeader(event, 'authorization') ?? ''
  await ofetch(`http://api:8000/v1/federation/subscriptions/${subId}`, {
    method: 'DELETE',
    headers: { Authorization: auth },
  })
  setResponseStatus(event, 204)
  return null
})
