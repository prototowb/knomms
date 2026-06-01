export default defineEventHandler(async (event): Promise<unknown> => {
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return $fetch<unknown>('http://api:8000/v1/sources/', {
    method: 'POST',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body,
  })
})
