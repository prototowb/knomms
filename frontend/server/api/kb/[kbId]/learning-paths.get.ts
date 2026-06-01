export default defineEventHandler(async (event) => {
  const kbId = getRouterParam(event, 'kbId')
  const auth = getHeader(event, 'authorization') ?? ''
  return $fetch(`http://api:8000/v1/kbs/${kbId}/learning-paths`, {
    headers: { Authorization: auth },
  })
})
