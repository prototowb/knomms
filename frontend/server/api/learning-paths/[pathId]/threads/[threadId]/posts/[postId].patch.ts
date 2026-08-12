import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const threadId = getRouterParam(event, 'threadId')
  const postId = getRouterParam(event, 'postId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return await ofetch(
    `http://api:8000/v1/learning-paths/${pathId}/threads/${threadId}/posts/${postId}`,
    { method: 'PATCH', headers: { Authorization: auth }, body }
  )
})
