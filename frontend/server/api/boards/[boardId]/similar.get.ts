export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  const limit = getQuery(event).limit ?? 5
  return $fetch(`http://api:8000/v1/boards/${boardId}/similar?limit=${limit}`)
})
