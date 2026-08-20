import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const subId = getRouterParam(event, 'subId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(`http://api:8000/v1/federation/subscriptions/${subId}/sync`, {
    method: 'POST',
    headers: { Authorization: auth },
  })
})
