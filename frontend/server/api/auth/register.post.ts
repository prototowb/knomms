export default defineEventHandler(async (event): Promise<unknown> => {
  const config = useRuntimeConfig()
  const body = await readBody(event)
  return $fetch<unknown>('http://api:8000/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Secret': config.secret,
    },
    body,
  })
})
