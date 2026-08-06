import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(
    `http://api:8000/v1/learning-paths/${pathId}/analytics`,
    { headers: { Authorization: auth } }
  )
})
