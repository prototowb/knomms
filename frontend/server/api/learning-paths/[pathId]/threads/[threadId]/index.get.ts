import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const threadId = getRouterParam(event, 'threadId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(
    `http://api:8000/v1/learning-paths/${pathId}/threads/${threadId}`,
    { headers: { Authorization: auth } }
  )
})
