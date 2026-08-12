import { proxyRequest } from 'h3'

// Multipart bundle upload — proxyRequest forwards the raw body unchanged
export default defineEventHandler(async (event): Promise<void> => {
  const auth = getHeader(event, 'authorization') ?? ''
  await proxyRequest(event, 'http://api:8000/v1/kbs/import', {
    headers: { authorization: auth },
  })
})
