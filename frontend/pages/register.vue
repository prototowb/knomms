<script setup lang="ts">
definePageMeta({ layout: false })

const auth = useAuthStore()

if (auth.isLoggedIn) {
  await navigateTo('/')
}

const email = ref('')
const password = ref('')
const handle = ref('')
const displayName = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  if (!email.value.trim() || !password.value || !handle.value.trim() || loading.value) return
  loading.value = true
  error.value = null
  try {
    await auth.register(
      email.value.trim(),
      password.value,
      handle.value.trim().toLowerCase(),
      displayName.value.trim() || handle.value.trim(),
    )
    await navigateTo('/')
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Registration failed'
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
        <p class="text-sm text-text-muted mt-1">Create your account</p>
      </div>

      <div class="bg-surface rounded-2xl border border-border p-6 shadow-sm">
        <form @submit.prevent="submit" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-text-secondary mb-1.5">Handle</label>
            <input
              v-model="handle"
              type="text"
              autocomplete="username"
              required
              :disabled="loading"
              pattern="[a-z0-9_\-]{2,50}"
              title="Lowercase letters, numbers, underscores, hyphens (2–50 chars)"
              class="w-full border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
              placeholder="yourhandle"
            />
            <p class="text-xs text-text-muted mt-1">Lowercase letters, numbers, underscores only</p>
          </div>

          <div>
            <label class="block text-xs font-medium text-text-secondary mb-1.5">Display name</label>
            <input
              v-model="displayName"
              type="text"
              :disabled="loading"
              class="w-full border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
              placeholder="Your Name (optional)"
            />
          </div>

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
              autocomplete="new-password"
              required
              minlength="8"
              :disabled="loading"
              class="w-full border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary bg-surface placeholder:text-text-muted focus:outline-none focus:border-accent disabled:opacity-50 transition-colors"
              placeholder="Minimum 8 characters"
            />
          </div>

          <p v-if="error" class="text-xs text-warning">{{ error }}</p>

          <button
            type="submit"
            :disabled="loading || !email.trim() || !password || !handle.trim()"
            class="w-full py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {{ loading ? 'Creating account…' : 'Create account' }}
          </button>
        </form>

        <p class="text-center text-xs text-text-muted mt-5">
          Already have an account?
          <NuxtLink to="/login" class="text-accent hover:underline">Sign in</NuxtLink>
        </p>
      </div>
    </div>
  </div>
</template>
