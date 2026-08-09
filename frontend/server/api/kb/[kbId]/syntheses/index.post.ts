import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return ofetch(`http://api:8000/v1/kbs/${kbId}/syntheses`, {
    method: 'POST',
    headers: { Authorization: auth },
    body,
  })
})
