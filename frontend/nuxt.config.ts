// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@pinia/nuxt',
    '@vueuse/nuxt',
    '@nuxtjs/tailwindcss',
  ],

  routeRules: {
    // Default: SPA for all app routes
    '/**': { ssr: false },
    // Public routes need SEO — server-render them
    '/explore/**': { ssr: true },
    '/board/**': { ssr: true },
    '/u/**': { ssr: true },
  },

  runtimeConfig: {
    // Server-only (not exposed to client)
    secret: '',
    // Exposed to client via useRuntimeConfig().public
    public: {
      apiBase: '/api',
    },
  },

  typescript: {
    strict: true,
    typeCheck: false,
  },

  devtools: { enabled: true },
})
