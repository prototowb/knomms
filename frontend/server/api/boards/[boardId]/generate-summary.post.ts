import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(`http://api:8000/v1/boards/${boardId}/generate-summary`, {
    method: 'POST',
    headers: { Authorization: auth },
  })
})
