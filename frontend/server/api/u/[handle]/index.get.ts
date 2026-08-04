import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const handle = getRouterParam(event, 'handle')
  return ofetch(`http://api:8000/v1/u/${handle}`)
})
