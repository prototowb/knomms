export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  return $fetch('http://api:8000/v1/boards/search', { query })
})
