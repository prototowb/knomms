import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return ofetch(`http://api:8000/v1/boards/${boardId}/fork`, {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
