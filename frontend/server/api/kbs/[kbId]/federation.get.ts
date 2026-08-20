import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  return (await ofetch(`http://api:8000/v1/kbs/${kbId}/federation`, {
    headers: { Authorization: auth },
  })) ?? null
})
