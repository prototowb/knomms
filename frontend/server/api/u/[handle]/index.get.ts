export default defineEventHandler(async (event) => {
  const handle = getRouterParam(event, 'handle')
  return $fetch(`http://api:8000/v1/u/${handle}`)
})
