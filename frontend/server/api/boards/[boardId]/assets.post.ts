import { proxyRequest } from 'h3'

// proxyRequest (not $fetch) — the typed-router $fetch overload hits TS
// "excessive stack depth" now that the route count has grown.
export default defineEventHandler(async (event): Promise<void> => {
  const boardId = getRouterParam(event, 'boardId')
  await proxyRequest(event, `http://api:8000/v1/boards/${boardId}/assets`)
})
