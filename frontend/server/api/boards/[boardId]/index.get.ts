export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  return $fetch(`http://api:8000/v1/boards/${boardId}`)
})
