export default defineNuxtPlugin(async () => {
  const auth = useAuthStore()
  // Restore session from localStorage token on every client-side page load.
  // Called once before any page setup() runs — ensures isLoggedIn is reliable
  // for route guards and page-level auth checks.
  await auth.fetchMe()
})
