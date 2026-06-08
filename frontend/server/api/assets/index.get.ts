export default defineEventHandler(async (event) => {
  const auth = getHeader(event, 'authorization') ?? ''
  const query = getQuery(event)
  return $fetch('http://api:8000/v1/assets', {
    headers: { Authorization: auth },
    query,
  })
})
