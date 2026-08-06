import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return ofetch(`http://api:8000/v1/learning-paths/${pathId}`, {
    method: 'PATCH',
    headers: { Authorization: auth },
    body,
  })
})
