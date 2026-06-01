import { proxyRequest } from 'h3'

// Multipart file upload routed to the board's dedicated KB.
// proxyRequest forwards the raw multipart body unchanged.
export default defineEventHandler(async (event): Promise<void> => {
  const boardId = getRouterParam(event, 'boardId')
  const auth = getHeader(event, 'authorization') ?? ''
  await proxyRequest(event, `http://api:8000/v1/boards/${boardId}/upload`, {
    headers: { authorization: auth },
  })
})
