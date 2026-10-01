<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

const STATUS_APPROVE = 5
const STATUS_CANCEL  = -1

interface WaitApproveRow {
  id: number
  room_no: string
  subject_code: string
  objective: string
  user_name: string
  booking_date: string
  start_time: string
  finish_time: string
}

const rows       = ref<WaitApproveRow[]>([])
const listState  = ref<'idle' | 'loading' | 'error'>('idle')
const listErrMsg = ref('')

const pageSize    = 10
const currentPage = ref(1)
const searchQuery = ref('')
const roomFilter  = ref('')
const dateFilter  = ref('')

const roomOptions = computed(() => [...new Set(rows.value.map(row => row.room_no).filter(Boolean))]
  .sort((left, right) => left.localeCompare(right, 'th', { numeric: true })))

const filteredRows = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase()

  return rows.value.filter((row) => {
    const matchesQuery = !query || [
      row.id,
      row.room_no,
      row.user_name,
      row.subject_code,
      row.objective,
    ].some(value => String(value ?? '').toLocaleLowerCase().includes(query))
    const matchesRoom = !roomFilter.value || row.room_no === roomFilter.value
    const matchesDate = !dateFilter.value || formatDate(row.booking_date) === dateFilter.value

    return matchesQuery && matchesRoom && matchesDate
  })
})

const hasActiveFilters = computed(() => Boolean(searchQuery.value || roomFilter.value || dateFilter.value))
const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)))
const pagedRows  = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredRows.value.slice(start, start + pageSize)
})

// Keep the page in range as rows are approved/cancelled.
watch(totalPages, (max) => {
  if (currentPage.value > max) currentPage.value = max
})

watch([searchQuery, roomFilter, dateFilter], () => {
  currentPage.value = 1
})

function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
}

function formatDate(iso: string) {
  return iso ? iso.slice(0, 10) : ''
}

function clearFilters() {
  searchQuery.value = ''
  roomFilter.value = ''
  dateFilter.value = ''
}

async function load() {
  listState.value  = 'loading'
  listErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/room-usage/get_schedule_wait_aprove/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    rows.value = Array.isArray(data) ? data : []
    listState.value = 'idle'
  } catch (e) {
    rows.value = []
    listState.value  = 'error'
    listErrMsg.value = `Failed to load bookings waiting for approval: ${e}`
  }
}

const busyId = ref<number | null>(null)

async function setStatus(item: WaitApproveRow, status: number) {
  if (busyId.value !== null) return

  const label = status === STATUS_APPROVE ? 'Approve' : 'Cancel'
  if (!window.confirm(`${label} booking #${item.id} (${item.user_name} — ${item.subject_code})?`)) return

  busyId.value = item.id
  listErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/room-usage/set_status_schedules/${item.id}?usage_status=${status}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    rows.value = rows.value.filter(r => r.id !== item.id)
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to ${label.toLowerCase()} booking #${item.id}: ${e}`
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <p class="card-title">Approve Room Bookings</p>
        <button type="button" class="btn-page" :disabled="listState === 'loading'" @click="load">
          {{ listState === 'loading' ? 'Loading…' : 'Refresh' }}
        </button>
      </div>

      <div v-if="listState === 'error'" class="msg error-box">{{ listErrMsg }}</div>

      <div class="filters" role="search" aria-label="Filter bookings waiting for approval">
        <label class="filter-field filter-search">
          <span>Search</span>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="ID, user, subject or objective"
            autocomplete="off"
          />
        </label>

        <label class="filter-field">
          <span>Room</span>
          <select v-model="roomFilter">
            <option value="">All rooms</option>
            <option v-for="room in roomOptions" :key="room" :value="room">{{ room }}</option>
          </select>
        </label>

        <label class="filter-field">
          <span>Date</span>
          <input v-model="dateFilter" type="date" />
        </label>

        <button type="button" class="btn-clear" :disabled="!hasActiveFilters" @click="clearFilters">
          Clear filters
        </button>
      </div>

      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Room</th>
            <th>User</th>
            <th>Subject</th>
            <th>Objective</th>
            <th>Date</th>
            <th>Start</th>
            <th>Finish</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredRows.length === 0 && listState !== 'loading'">
            <td colspan="9" class="empty">
              {{ rows.length === 0 ? 'No bookings waiting for approval.' : 'No bookings match the selected filters.' }}
            </td>
          </tr>
          <tr v-for="item in pagedRows" :key="item.id">
            <td class="mono">{{ item.id }}</td>
            <td class="mono">{{ item.room_no }}</td>
            <td>{{ item.user_name }}</td>
            <td>{{ item.subject_code }}</td>
            <td>{{ item.objective }}</td>
            <td class="mono">{{ formatDate(item.booking_date) }}</td>
            <td class="mono">{{ item.start_time }}</td>
            <td class="mono">{{ item.finish_time }}</td>
            <td class="actions">
              <button
                type="button"
                class="btn-approve"
                :disabled="busyId !== null"
                @click="setStatus(item, STATUS_APPROVE)"
              >
                Approve
              </button>
              <button
                type="button"
                class="btn-delete"
                :disabled="busyId !== null"
                @click="setStatus(item, STATUS_CANCEL)"
              >
                Cancel
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="filteredRows.length > 0" class="pagination">
        <button
          type="button"
          class="btn-page"
          :disabled="currentPage === 1"
          @click="goToPage(currentPage - 1)"
        >
          ‹ Prev
        </button>
        <span class="page-info">
          Page {{ currentPage }} of {{ totalPages }}
          ({{ filteredRows.length }}<template v-if="hasActiveFilters"> of {{ rows.length }}</template> total)
        </span>
        <button
          type="button"
          class="btn-page"
          :disabled="currentPage === totalPages"
          @click="goToPage(currentPage + 1)"
        >
          Next ›
        </button>
      </div>
    </div>
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
  display: grid;
  grid-template-columns: minmax(16rem, 2fr) minmax(9rem, 0.8fr) minmax(10rem, 0.9fr) auto;
  align-items: end;
  gap: 0.75rem;
  margin-bottom: 0.9rem;
  padding: 0.8rem;
  border-radius: 0.65rem;
  background: var(--bg-page);
}

.filter-field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.32rem;
}

.filter-field > span {
  color: var(--text-secondary);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.filter-field input,
.filter-field select {
  width: 100%;
  min-height: 2.35rem;
  box-sizing: border-box;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg-surface);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.82rem;
  padding: 0.45rem 0.65rem;
}

.filter-field input:focus-visible,
.filter-field select:focus-visible,
.btn-clear:focus-visible {
  border-color: var(--accent-link);
  outline: 2px solid color-mix(in srgb, var(--accent-link) 25%, transparent);
  outline-offset: 1px;
}

.btn-clear {
  min-height: 2.35rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg-surface);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 650;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
  white-space: nowrap;
}

.btn-clear:hover:not(:disabled) { background: var(--bg-surface-alt); }
.btn-clear:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-approve {
  background: rgba(34,197,94,.12);
  color: #16a34a;
  border: 1px solid rgba(34,197,94,.35);
  border-radius: 0.5rem;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.35rem 0.7rem;
  cursor: pointer;
}
.btn-approve:hover:not(:disabled) { background: rgba(34,197,94,.22); }
.btn-approve:disabled { opacity: 0.6; cursor: not-allowed; }

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

.actions {
  display: flex;
  gap: 0.4rem;
  white-space: nowrap;
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

@media (max-width: 900px) {
  .filters { grid-template-columns: minmax(0, 1fr) minmax(8rem, 0.55fr); }
  .filter-search { grid-column: 1 / -1; }
}

@media (max-width: 560px) {
  .page { padding-inline: 0.5rem; }
  .card { width: 100%; padding: 0.85rem; }
  .filters { grid-template-columns: minmax(0, 1fr); }
  .filter-search { grid-column: auto; }
  .btn-clear { width: 100%; }
  .pagination { gap: 0.5rem; }
}
</style>
