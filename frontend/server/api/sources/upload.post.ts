import { proxyRequest } from 'h3'

export default defineEventHandler(async (event): Promise<void> => {
  const auth = getHeader(event, 'authorization') ?? ''
  await proxyRequest(event, 'http://api:8000/v1/sources/upload', {
    headers: { authorization: auth },
  })
})
