import { proxyRequest } from 'h3'

// Catch-all: forward /api/harnesses/* to FastAPI /v1/harnesses/*
export default defineEventHandler(async (event): Promise<void> => {
  const subPath = (event.context.params?.path as string | undefined) ?? ''
  await proxyRequest(event, `http://api:8000/v1/harnesses/${subPath}${event.path.includes('?') ? event.path.slice(event.path.indexOf('?')) : ''}`)
})
