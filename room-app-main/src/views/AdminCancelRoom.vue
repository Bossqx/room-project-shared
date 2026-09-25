<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

interface RoomUsageRow {
  id: number
  user_name: string
  subject_code: string
  booking_date: string
  start_time: string
  finish_time: string
}

const filters = ref({
  room_no: '',
  booking_date: '',
  keyword: '',
})

const rows      = ref<RoomUsageRow[]>([])
const listState = ref<'idle' | 'loading' | 'error'>('idle')
const listErrMsg = ref('')
const hasSearched = ref(false)

const pageSize    = 10
const currentPage = ref(1)

const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))
const pagedRows  = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return rows.value.slice(start, start + pageSize)
})

// Keep the page in range if the row count shrinks (e.g. after a delete).
watch(totalPages, (max) => {
  if (currentPage.value > max) currentPage.value = max
})

function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
}

function formatDate(iso: string) {
  return iso ? iso.slice(0, 10) : ''
}

async function search() {
  listState.value  = 'loading'
  listErrMsg.value = ''
  hasSearched.value = true
  currentPage.value = 1
  try {
    const params = new URLSearchParams()
    if (filters.value.room_no)     params.set('room_no', filters.value.room_no)
    if (filters.value.booking_date) params.set('booking_date', filters.value.booking_date)
    if (filters.value.keyword)     params.set('keyword', filters.value.keyword)

    const res = await fetch(`${apiBase}/room-usage/get_room_usage_by_admin/?${params.toString()}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    rows.value = Array.isArray(data) ? data : []
    listState.value = 'idle'
  } catch (e) {
    rows.value = []
    listState.value  = 'error'
    listErrMsg.value = `Failed to load room usage: ${e}`
  }
}

const deletingId    = ref<number | null>(null)
const pendingDelete = ref<RoomUsageRow | null>(null)

function removeRow(item: RoomUsageRow) {
  if (deletingId.value !== null) return
  pendingDelete.value = item
}

function cancelDelete() {
  pendingDelete.value = null
}

async function confirmDelete() {
  const item = pendingDelete.value
  if (!item) return

  deletingId.value = item.id
  try {
    const res = await fetch(`${apiBase}/room-usage/delete_by_admin/${item.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    rows.value = rows.value.filter(r => r.id !== item.id)
    pendingDelete.value = null
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to delete booking #${item.id}: ${e}`
  } finally {
    deletingId.value = null
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <p class="card-title">Cancel Room Bookings</p>
      </div>

      <form class="filters" @submit.prevent="search">
        <div class="field">
          <label class="lbl">Room No</label>
          <input v-model="filters.room_no" type="text" class="input" placeholder="e.g. 27.01.01" />
        </div>
        <div class="field">
          <label class="lbl">Booking Date</label>
          <input v-model="filters.booking_date" type="date" class="input" />
        </div>
        <div class="field">
          <label class="lbl">Keyword</label>
          <input v-model="filters.keyword" type="text" class="input" placeholder="User name or subject" />
        </div>
        <button class="btn" type="submit" :disabled="listState === 'loading'">
          <span v-if="listState === 'loading'" class="spinner"></span>
          {{ listState === 'loading' ? 'Searching…' : 'Search' }}
        </button>
      </form>

      <div v-if="listState === 'error'" class="msg error-box">{{ listErrMsg }}</div>

      <table v-if="hasSearched" class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Subject</th>
            <th>Date</th>
            <th>Start</th>
            <th>Finish</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0 && listState !== 'loading'">
            <td colspan="7" class="empty">No bookings found.</td>
          </tr>
          <tr v-for="item in pagedRows" :key="item.id">
            <td class="mono">{{ item.id }}</td>
            <td>{{ item.user_name }}</td>
            <td>{{ item.subject_code }}</td>
            <td class="mono">{{ formatDate(item.booking_date) }}</td>
            <td class="mono">{{ item.start_time }}</td>
            <td class="mono">{{ item.finish_time }}</td>
            <td>
              <button
                type="button"
                class="btn-delete"
                :disabled="deletingId === item.id"
                @click="removeRow(item)"
              >
                {{ deletingId === item.id ? 'Deleting…' : 'Delete' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="hasSearched && rows.length > 0" class="pagination">
        <button
          type="button"
          class="btn-page"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          ‹ Prev
        </button>
        <span class="page-info">Page {{ currentPage }} of {{ totalPages }} ({{ rows.length }} total)</span>
        <button
          type="button"
          class="btn-page"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          Next ›
        </button>
      </div>

      <p v-if="!hasSearched" class="hint">Enter a filter and click Search to list bookings.</p>
    </div>

    <!-- Delete confirmation popup -->
    <Teleport to="body">
      <div v-if="pendingDelete" class="overlay" @click.self="cancelDelete">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="cancelDelete">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">Delete Booking</p>
          <p class="confirm-text">
            Delete booking #{{ pendingDelete.id }}
            (<strong>{{ pendingDelete.user_name }}</strong> — {{ pendingDelete.subject_code }})?
            This cannot be undone.
          </p>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="cancelDelete" :disabled="deletingId !== null">
              Cancel
            </button>
            <button type="button" class="btn-delete btn-delete-lg" @click="confirmDelete" :disabled="deletingId !== null">
              <span v-if="deletingId !== null" class="spinner spinner-dark"></span>
              {{ deletingId !== null ? 'Deleting…' : 'Delete' }}
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

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.85rem;
  margin-bottom: 1rem;
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
  min-width: 180px;
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
  height: fit-content;
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn:hover:not(:disabled) { background: #1d4ed8; }

.btn-delete {
  background: rgba(239,68,68,.12);
  color: var(--pill-error-text);
  border: 1px solid rgba(239,68,68,.35);
  border-radius: 0.5rem;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.btn-delete:hover:not(:disabled) { background: rgba(239,68,68,.22); }
.btn-delete:disabled { opacity: 0.6; cursor: not-allowed; }

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.msg {
  margin-bottom: 1rem;
  font-size: 0.8rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.5rem;
}
.error-box { background: rgba(239,68,68,.12); color: var(--pill-error-text); border: 1px solid rgba(239,68,68,.35); }

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

.mono { font-family: monospace; }

.empty {
  text-align: center;
  color: #64748b;
  padding: 1.25rem 0.6rem;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}

.page-info {
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.btn-page {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.4rem 0.85rem;
  cursor: pointer;
}
.btn-page:hover:not(:disabled) { background: var(--bg-surface-alt); }
.btn-page:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Delete confirmation popup ── */
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

.confirm-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0.5rem 0 1.25rem;
}
.confirm-text strong { color: var(--text-primary); }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.55rem 1.1rem;
  cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { background: var(--bg-page); }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-delete-lg {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.1rem;
  font-size: 0.85rem;
}

.spinner-dark {
  border: 2px solid rgba(239,68,68,.35);
  border-top-color: var(--pill-error-text);
}
</style>
