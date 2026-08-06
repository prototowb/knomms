import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const kbId = getRouterParam(event, 'kbId')
  const grantId = getRouterParam(event, 'grantId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch<unknown>(`http://api:8000/v1/kbs/${kbId}/grants/${grantId}`, {
    method: 'DELETE',
    headers: { Authorization: auth },
  })
})
