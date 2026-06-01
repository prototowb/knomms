import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
  id: string
  handle: string
  email: string
  display_name: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  const isLoggedIn = computed(() => user.value !== null && token.value !== null)

  async function register(email: string, password: string, handle: string, displayName: string): Promise<void> {
    const data = await $fetch<{ token: string; user: User }>('/api/auth/register', {
      method: 'POST',
      body: { email, password, handle, display_name: displayName },
    })
    token.value = data.token
    user.value = data.user
    if (import.meta.client) {
      localStorage.setItem('kc_token', data.token)
    }
  }

  async function login(email: string, password: string): Promise<void> {
    const data = await $fetch<{ token: string; user: User }>('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    token.value = data.token
    user.value = data.user
    if (import.meta.client) {
      localStorage.setItem('kc_token', data.token)
    }
  }

  function logout(): void {
    user.value = null
    token.value = null
    if (import.meta.client) {
      localStorage.removeItem('kc_token')
    }
  }

  async function fetchMe(): Promise<void> {
    const storedToken = import.meta.client ? localStorage.getItem('kc_token') : null
    const bearerToken = token.value ?? storedToken
    if (!bearerToken) return

    const data = await $fetch<User>('/api/auth/me', {
      headers: { Authorization: `Bearer ${bearerToken}` },
    })
    user.value = data
    token.value = bearerToken
  }

  return { user, token, isLoggedIn, register, login, logout, fetchMe }
})
