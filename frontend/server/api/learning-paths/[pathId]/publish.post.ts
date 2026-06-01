export default defineEventHandler(async (event) => {
  const pathId = getRouterParam(event, 'pathId')
  const auth = getHeader(event, 'authorization') ?? ''
  return $fetch(`http://api:8000/v1/learning-paths/${pathId}/publish`, {
    method: 'POST',
    headers: { Authorization: auth },
  })
})
