import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  // Forward auth when present — owners can view (and poll) their own
  // non-public boards; anonymous requests still get public boards.
  const auth = getHeader(event, 'authorization')
  return ofetch(`http://api:8000/v1/boards/${boardId}`, {
    headers: auth ? { Authorization: auth } : {},
  })
})
