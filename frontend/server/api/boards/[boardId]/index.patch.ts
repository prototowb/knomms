export default defineEventHandler(async (event): Promise<unknown> => {
  const boardId = getRouterParam(event, 'boardId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return $fetch<unknown>(`http://api:8000/v1/boards/${boardId}`, {
    method: 'PATCH',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
