import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const pathId = getRouterParam(event, 'pathId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch<unknown>(`http://api:8000/v1/learning-paths/${pathId}/publish`, {
    method: 'POST',
    headers: { Authorization: auth },
  })
})
