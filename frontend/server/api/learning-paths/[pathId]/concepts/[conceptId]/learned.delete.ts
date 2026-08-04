import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const conceptId = getRouterParam(event, 'conceptId')
  const auth = getHeader(event, 'authorization') ?? ''
  return ofetch(
    `http://api:8000/v1/learning-paths/${pathId}/concepts/${conceptId}/learned`,
    { method: 'DELETE', headers: { Authorization: auth } }
  )
})
