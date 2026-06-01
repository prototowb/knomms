import { proxyRequest } from 'h3'

// Catch-all: forward /api/v1/* directly to FastAPI.
// This enables direct API access (curl, Swagger UI "Try it out") while
// keeping all BFF-handled paths (/api/auth/*, /api/kbs/*, etc.) routing
// through their dedicated server route handlers.
export default defineEventHandler(async (event): Promise<void> => {
  // event.path is the full path: /api/v1/auth/login → /v1/auth/login at FastAPI
  const apiPath = event.path.replace(/^\/api/, '')
  await proxyRequest(event, `http://api:8000${apiPath}`)
})
