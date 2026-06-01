export default defineEventHandler(async (event): Promise<unknown> => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  return $fetch<unknown>(`http://api:8000/v1/kbs/${kbId}/sources`, {
    headers: { Authorization: auth },
  })
})
