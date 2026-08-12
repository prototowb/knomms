import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const synthesisId = getRouterParam(event, 'synthesisId')
  const auth = getHeader(event, 'authorization') ?? ''
  await ofetch(`http://api:8000/v1/kbs/${kbId}/syntheses/${synthesisId}`, {
    method: 'DELETE',
    headers: { Authorization: auth },
  })
  setResponseStatus(event, 204)
  return null
})
