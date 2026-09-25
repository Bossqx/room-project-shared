<script setup lang="ts">
import { ref, onMounted } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

interface Semester {
  id: number
  academic_year: string
  semester: string
  status: number
}

const semesters   = ref<Semester[]>([])
const listState   = ref<'idle' | 'loading' | 'error'>('idle')
const listErrMsg  = ref('')

async function fetchSemesters() {
  listState.value  = 'loading'
  listErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/migration/get_list_semester/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    semesters.value = await res.json()
    listState.value = 'idle'
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to load semesters: ${e}`
  }
}

onMounted(fetchSemesters)

const togglingId = ref<number | null>(null)

async function toggleStatus(item: Semester) {
  if (togglingId.value !== null) return
  togglingId.value = item.id
  try {
    const res = await fetch(`${apiBase}/migration/set_status/${item.id}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await fetchSemesters()
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to update status: ${e}`
  } finally {
    togglingId.value = null
  }
}

const showModal = ref(false)
const form = ref({
  academic_year: '',
  semester: '',
})

const createState = ref<'idle' | 'loading' | 'error'>('idle')
const createErrMsg = ref('')

function openModal() {
  form.value = { academic_year: '', semester: '' }
  createState.value  = 'idle'
  createErrMsg.value = ''
  showModal.value = true
}

async function createSemester() {
  if (!form.value.academic_year || !form.value.semester) return
  createState.value  = 'loading'
  createErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/migration/create_semester/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        academic_year: form.value.academic_year,
        semester: form.value.semester,
        status: 1,
        created_date: new Date().toISOString(),
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    showModal.value = false
    await fetchSemesters()
  } catch (e) {
    createState.value  = 'error'
    createErrMsg.value = `Failed to create semester: ${e}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <p class="card-title">Semesters</p>
        <button class="btn" @click="openModal">+ Add Semester</button>
      </div>

      <div v-if="listState === 'loading'" class="hint">Loading…</div>
      <div v-else-if="listState === 'error'" class="msg error-box">{{ listErrMsg }}</div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>Academic Year</th>
            <th>Semester</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="semesters.length === 0">
            <td colspan="3" class="empty">No semesters found.</td>
          </tr>
          <tr v-for="item in semesters" :key="item.id">
            <td>{{ item.academic_year }}</td>
            <td>{{ item.semester }}</td>
            <td>
              <button
                type="button"
                class="badge badge-toggle"
                :class="item.status === 1 ? 'badge-active' : 'badge-inactive'"
                :disabled="togglingId !== null"
                @click="toggleStatus(item)"
              >
                {{ togglingId === item.id ? 'Updating…' : (item.status === 1 ? 'Active' : 'Inactive') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create semester popup -->
    <Teleport to="body">
      <div v-if="showModal" class="overlay" @click.self="showModal = false">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="showModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">Add Semester</p>

          <form class="form" @submit.prevent="createSemester">
            <div class="field">
              <label class="lbl">Academic Year</label>
              <input v-model="form.academic_year" type="text" class="input" required />
            </div>

            <div class="field">
              <label class="lbl">Semester</label>
              <input v-model="form.semester" type="text" class="input" required />
            </div>

            <button class="btn" type="submit" :disabled="createState === 'loading'">
              <span v-if="createState === 'loading'" class="spinner"></span>
              {{ createState === 'loading' ? 'Creating…' : 'Create' }}
            </button>
          </form>

          <div v-if="createState === 'error'" class="msg error-box">{{ createErrMsg }}</div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  padding: 1.25rem 1%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.card-title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-link-hover);
  margin: 0;
}

.hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.table th {
  text-align: left;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--border);
}

.table td {
  padding: 0.6rem;
  border-bottom: 1px solid #273549;
}

.empty {
  text-align: center;
  color: #64748b;
  padding: 1.25rem 0.6rem;
}

.badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
}
.badge-active   { background: rgba(34,197,94,.12);  color: var(--pill-success-text); }
.badge-inactive { background: rgba(148,163,184,.15); color: var(--text-secondary); }

.badge-toggle {
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: opacity .15s;
}
.badge-toggle:hover:not(:disabled) { opacity: 0.75; }
.badge-toggle:disabled { cursor: not-allowed; opacity: 0.6; }

.form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-top: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.lbl {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}

.input {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  padding: 0.5rem 0.7rem;
  font-size: 0.85rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: #2563eb;
  border: none;
  border-radius: 0.5rem;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.55rem 1.1rem;
  cursor: pointer;
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn:hover:not(:disabled) { background: #1d4ed8; }

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg {
  margin-top: 1rem;
  font-size: 0.8rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.5rem;
}
.error-box { background: rgba(239,68,68,.12); color: var(--pill-error-text); border: 1px solid rgba(239,68,68,.35); }

/* ── Popup ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, .65);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  z-index: 500;
}

.modal {
  position: relative;
  width: 100%;
  max-width: 420px;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
  box-sizing: border-box;
}

.modal-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, .6);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: #f1f5f9;
  cursor: pointer;
}
.modal-close svg { width: 16px; height: 16px; }
.modal-close:hover { background: #334155; }
</style>
