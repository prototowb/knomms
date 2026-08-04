import { ofetch } from 'ofetch'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  return ofetch('http://api:8000/v1/boards', { query })
})
