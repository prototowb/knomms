export default defineEventHandler(async (event) => {
  const authorization = getHeader(event, 'authorization')

  const response = await $fetch<unknown>('http://api:8000/v1/auth/me', {
    method: 'GET',
    headers: {
      ...(authorization ? { Authorization: authorization } : {}),
    },
  })

  return response
})
