import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(`http://api:8000/v1/kbs/${kbId}/syntheses`, {
    headers: { Authorization: auth },
  })
})
