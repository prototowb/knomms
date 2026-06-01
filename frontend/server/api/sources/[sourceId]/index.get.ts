export default defineEventHandler(async (event): Promise<unknown> => {
  const sourceId = getRouterParam(event, 'sourceId')
  const auth = getHeader(event, 'authorization') ?? ''
  return $fetch<unknown>(`http://api:8000/v1/sources/${sourceId}`, {
    headers: { Authorization: auth },
  })
})
