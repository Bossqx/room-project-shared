import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Semester {
  year_no:  string
  semester: string
}

export const useSemesterStore = defineStore('semester', () => {
  const semester = ref<Semester | null>(null)

  async function fetchActiveSemester(apiBase: string) {
    try {
      const res = await fetch(`${apiBase}/schedule/get_active_semester`)
      if (res.ok) semester.value = await res.json()
    } catch { /* leave null */ }
  }

  return { semester, fetchActiveSemester }
})
