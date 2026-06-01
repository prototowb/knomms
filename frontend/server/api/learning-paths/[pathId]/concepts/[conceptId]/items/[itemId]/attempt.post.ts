export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const conceptId = getRouterParam(event, 'conceptId')
  const itemId = getRouterParam(event, 'itemId')
  const auth = getHeader(event, 'authorization') ?? ''
  const body = await readBody(event)
  return $fetch(
    `http://api:8000/v1/learning-paths/${pathId}/concepts/${conceptId}/items/${itemId}/attempt`,
    {
      method: 'POST',
      headers: { Authorization: auth, 'Content-Type': 'application/json' },
      body,
    }
  )
})
