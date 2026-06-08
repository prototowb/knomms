import { proxyRequest } from 'h3'

// Catch-all: forward /api/assets/* to FastAPI /v1/assets/*
export default defineEventHandler(async (event): Promise<void> => {
  const subPath = (event.context.params?.path as string | undefined) ?? ''
  await proxyRequest(event, `http://api:8000/v1/assets/${subPath}${event.path.includes('?') ? event.path.slice(event.path.indexOf('?')) : ''}`)
})
