import { ofetch } from 'ofetch'

export default defineEventHandler(async (event): Promise<unknown> => {
  const authorization = getHeader(event, 'authorization')
  const response: unknown = await ofetch<unknown>('http://api:8000/v1/auth/me', {
    method: 'GET',
    headers: {
      ...(authorization ? { Authorization: authorization } : {}),
    },
  })
  return response
})
