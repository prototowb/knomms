export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return $fetch(`http://api:8000/v1/kbs/${kbId}/learning-paths`, {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
