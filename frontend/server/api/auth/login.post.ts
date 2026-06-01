export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const body = await readBody(event)

  const response = await $fetch<unknown>('http://api:8000/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Forward the internal secret so the backend can verify requests originate from the BFF
      'X-Internal-Secret': config.secret,
    },
    body,
  })

  return response
})
