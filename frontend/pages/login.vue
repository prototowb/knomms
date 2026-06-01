<script setup lang="ts">
definePageMeta({ layout: false })

const auth = useAuthStore()
const route = useRoute()

if (auth.isLoggedIn) {
  await navigateTo('/')
}

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  if (!email.value.trim() || !password.value || loading.value) return
  loading.value = true
  error.value = null
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await navigateTo(redirect)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Login failed — check your credentials'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-surface-secondary flex items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-semibold text-text-primary">Knowledge Commons</h1>
        <p class="text-sm text-text-muted mt-1">Sign in to your account</p>
      </div>

      <div class="bg-surface rounded-2xl border border-border p-6 shadow-sm">
        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-text-secondary mb-1.5">Email</label>
            <input
              v-model="email"
              type="email"
              autocomplete="email"
              required
              :disabled="loading"
              class="w-full border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-text-secondary mb-1.5">Password</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              :disabled="loading"
              class="w-full border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
              placeholder="••••••••"
            />
          </div>

          <p v-if="error" class="text-xs text-warning">{{ error }}</p>

          <button
            type="submit"
            :disabled="loading || !email.trim() || !password"
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>

        <p class="text-center text-xs text-text-muted mt-5">
          No account?
          <NuxtLink to="/register" class="text-accent hover:underline">Create one</NuxtLink>
        </p>
      </div>
    </div>
  </div>
</template>
