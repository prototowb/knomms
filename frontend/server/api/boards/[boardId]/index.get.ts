import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  return ofetch(`http://api:8000/v1/boards/${boardId}`)
})
