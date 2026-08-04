import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return ofetch<unknown>(`http://api:8000/v1/kbs/${kbId}`, {
    method: 'PATCH',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
