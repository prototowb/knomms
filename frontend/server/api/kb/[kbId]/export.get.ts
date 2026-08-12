import { proxyRequest } from 'h3'

// Streams the bundle download (attachment headers pass through unchanged)
export default defineEventHandler(async (event): Promise<void> => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  await proxyRequest(event, `http://api:8000/v1/kbs/${kbId}/export`, {
    headers: { authorization: auth },
  })
})
