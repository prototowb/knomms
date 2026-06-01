export default defineEventHandler(async (event): Promise<unknown> => {
  const auth = getHeader(event, 'authorization') ?? ''
  return $fetch<unknown>('http://api:8000/v1/my/boards', {
    headers: { Authorization: auth },
  })
})
