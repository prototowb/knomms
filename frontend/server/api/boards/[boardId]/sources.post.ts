export default defineEventHandler(async (event) => {
  const boardId = getRouterParam(event, 'boardId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return $fetch(`http://api:8000/v1/boards/${boardId}/sources`, {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
