import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
  id:          number
  user_name:   string
  name:        string
  picture:     string
  description: string
  user_type:   string
}

const STORAGE_KEY = 'user'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(loadFromStorage())

  function loadFromStorage(): User | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as User) : null
    } catch {
      return null
    }
  }

  const isLoggedIn  = computed(() => user.value !== null)
  const userName    = computed(() => user.value?.user_name ?? '')
  const userType    = computed(() => user.value?.user_type ?? '')

  function setUser(data: User) {
    user.value = data
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  }

  function clearUser() {
    user.value = null
    sessionStorage.removeItem(STORAGE_KEY)
  }

  return { user, isLoggedIn, userName, userType, setUser, clearUser }
})
