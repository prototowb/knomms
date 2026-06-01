import { proxyRequest } from 'h3'

export default defineEventHandler(async (event): Promise<void> => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  await proxyRequest(event, `http://api:8000/v1/kbs/${kbId}/query`, {
    headers: { authorization: auth },
  })
})
