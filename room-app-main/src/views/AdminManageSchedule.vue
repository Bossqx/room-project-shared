<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

interface ScheduleItem {
  id: number
  roomcode: string
  weekday: number | string
  coursecode: string
  coursename: string
  teacher_name: string
  schedule_date: string
  startTime: string
  finishTime: string
  objective?: string
  source?: string
}

const form = ref({
  room_code: '27.03.05',
  start_date: new Date().toISOString().slice(0, 10),
  finish_date: new Date().toISOString().slice(0, 10),
})

const results   = ref<ScheduleItem[]>([])
const queryState = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const errMsg      = ref('')

const pageSize    = 10
const currentPage = ref(1)

const totalPages = computed(() => Math.max(1, Math.ceil(results.value.length / pageSize)))

const pagedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return results.value.slice(start, start + pageSize)
})

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(1, page), totalPages.value)
}

async function querySchedule() {
  if (!form.value.room_code || !form.value.start_date || !form.value.finish_date) return
  queryState.value = 'loading'
  errMsg.value     = ''
  try {
    const params = new URLSearchParams({
      room_code:   form.value.room_code,
      start_date:  form.value.start_date,
      finish_date: form.value.finish_date,
    })
    const res = await fetch(`${apiBase}/schedule/get_schedule_by_date_range_db/?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    results.value    = await res.json()
    queryState.value = 'done'
    currentPage.value = 1
  } catch (e) {
    results.value    = []
    queryState.value = 'error'
    errMsg.value     = `Failed to query schedule: ${e}`
  }
}

const removingId  = ref<number | null>(null)
const confirmItem = ref<ScheduleItem | null>(null)

function askRemove(item: ScheduleItem) {
  confirmItem.value = item
}

function cancelRemove() {
  confirmItem.value = null
}

async function confirmRemove() {
  const item = confirmItem.value
  if (!item || removingId.value !== null) return
  removingId.value = item.id
  try {
    const endpoint = item.source === 'booking' ? 'remove_booking' : 'remove_schedule'
    const res = await fetch(`${apiBase}/schedule/${endpoint}/${item.id}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    results.value = results.value.filter(r => r.id !== item.id)
    confirmItem.value = null
  } catch (e) {
    errMsg.value = `Failed to remove item: ${e}`
  } finally {
    removingId.value = null
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">Query Schedule</p>
      <p class="hint">Fetch stored schedule/booking records for a room within a date range.</p>

      <form class="form" @submit.prevent="querySchedule">
        <div class="field">
          <label class="lbl">Room Code</label>
          <input v-model="form.room_code" type="text" class="input" required />
        </div>

        <div class="field">
          <label class="lbl">Start Date</label>
          <input v-model="form.start_date" type="date" class="input" required />
        </div>

        <div class="field">
          <label class="lbl">Finish Date</label>
          <input v-model="form.finish_date" type="date" class="input" required />
        </div>

        <button class="btn" type="submit" :disabled="queryState === 'loading'">
          <span v-if="queryState === 'loading'" class="spinner"></span>
          {{ queryState === 'loading' ? 'Searching…' : 'Search' }}
        </button>
      </form>

      <div v-if="queryState === 'error'" class="msg error-box">{{ errMsg }}</div>
    </div>

    <div class="card">
      <p class="card-title">Results</p>

      <table class="table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Weekday</th>
            <th>Time</th>
            <th>Course</th>
            <th>Teacher</th>
            <th>Source</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="queryState !== 'done' || results.length === 0">
            <td colspan="7" class="empty">
              {{ queryState === 'loading' ? 'Loading…' : 'No results yet — run a search.' }}
            </td>
          </tr>
          <tr v-for="item in pagedResults" :key="item.id">
            <td>{{ item.schedule_date }}</td>
            <td>{{ item.weekday }}</td>
            <td>{{ item.startTime }} – {{ item.finishTime }}</td>
            <td>
              <div class="course-code">{{ item.coursecode }}</div>
              <div class="course-name">{{ item.coursename }}</div>
            </td>
            <td>{{ item.teacher_name }}</td>
            <td>{{ item.source ?? item.objective ?? '-' }}</td>
            <td>
              <button
                type="button"
                class="btn-remove"
                :disabled="removingId !== null"
                @click="askRemove(item)"
              >
                {{ removingId === item.id ? 'Removing…' : 'Remove' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="queryState === 'done' && results.length > 0" class="pagination">
        <span class="pagination-info">
          Page {{ currentPage }} of {{ totalPages }} · {{ results.length }} result{{ results.length === 1 ? '' : 's' }}
        </span>
        <div class="pagination-controls">
          <button type="button" class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
            Prev
          </button>
          <button type="button" class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm remove popup -->
    <Teleport to="body">
      <div v-if="confirmItem" class="overlay" @click.self="cancelRemove">
        <div class="confirm-modal">
          <p class="confirm-title">Remove this record?</p>
          <p class="confirm-body">
            {{ confirmItem.coursecode }} — {{ confirmItem.coursename }}<br />
            {{ confirmItem.schedule_date }} · {{ confirmItem.startTime }}–{{ confirmItem.finishTime }}
          </p>
          <div class="confirm-actions">
            <button type="button" class="btn-cancel" :disabled="removingId !== null" @click="cancelRemove">
              Cancel
            </button>
            <button type="button" class="btn-remove" :disabled="removingId !== null" @click="confirmRemove">
              {{ removingId === confirmItem.id ? 'Removing…' : 'Remove' }}
            </button>
          </div>
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

.card-title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-link-hover);
  margin: 0 0 0.4rem;
}

.hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0 0 1rem;
}

.form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.85rem;
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

.btn-remove {
  background: rgba(239,68,68,.12);
  border: 1px solid rgba(239,68,68,.35);
  border-radius: 0.5rem;
  color: var(--pill-error-text);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
  white-space: nowrap;
}
.btn-remove:hover:not(:disabled) { background: rgba(239,68,68,.22); }
.btn-remove:disabled { opacity: 0.6; cursor: not-allowed; }

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
  vertical-align: top;
}

.course-code { font-weight: 600; }
.course-name { font-size: 0.78rem; color: var(--text-secondary); }

.empty {
  text-align: center;
  color: #64748b;
  padding: 1.25rem 0.6rem;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.6rem;
  margin-top: 0.9rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--border);
}

.pagination-info {
  font-size: 0.78rem;
  color: #64748b;
}

.pagination-controls {
  display: flex;
  gap: 0.5rem;
}

.page-btn {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
}
.page-btn:hover:not(:disabled) { background: var(--bg-surface-alt); }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Confirm popup ── */
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

.confirm-modal {
  width: 100%;
  max-width: 380px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
  box-sizing: border-box;
}

.confirm-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.6rem;
}

.confirm-body {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0 0 1.25rem;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  cursor: pointer;
}
.btn-cancel:hover:not(:disabled) { background: var(--bg-surface-alt); }
.btn-cancel:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
