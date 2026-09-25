<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import config from '../assets/config.json'

const router = useRouter()

interface EmptyRange {
  roomcode:   string
  startTime:  string
  finishTime: string
}

const apiBase = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

const ALL_ROOMS = ''

const rooms     = ref<string[]>([])
const roomCode  = ref(ALL_ROOMS)
const queryDate = ref(new Date().toISOString().slice(0, 10))

const results = ref<EmptyRange[]>([])
const state   = ref<'idle' | 'loading' | 'empty' | 'done' | 'error'>('idle')
const errMsg  = ref('')

const grouped = computed(() => {
  const byRoom = new Map<string, EmptyRange[]>()
  for (const item of results.value) {
    if (!byRoom.has(item.roomcode)) byRoom.set(item.roomcode, [])
    byRoom.get(item.roomcode)!.push(item)
  }
  return [...byRoom.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([roomcode, ranges]) => ({ roomcode, ranges }))
})

async function loadRooms() {
  try {
    const res  = await fetch(`${apiBase}/room-usage/get_rooms`)
    const data = await res.json()
    rooms.value = (Array.isArray(data) ? data : []).map((r: { room_no: string }) => r.room_no)
  } catch { /* rooms stay empty */ }
}

async function search() {
  state.value   = 'loading'
  errMsg.value  = ''
  results.value = []
  try {
    const url = `${apiBase}/schedule/get_empty_rooms_db/${encodeURIComponent(roomCode.value)}?schedule_date=${queryDate.value}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: EmptyRange[] = await res.json()
    results.value = Array.isArray(data) ? data : []
    state.value   = results.value.length ? 'done' : 'empty'
  } catch (e) {
    state.value  = 'error'
    errMsg.value = `Failed to fetch: ${e}`
  }
}

onMounted(async () => {
  await loadRooms()
  search()
})

function goBook(range: EmptyRange) {
  router.push({
    path: '/booking',
    query: {
      room_no:     range.roomcode,
      start_time:  range.startTime,
      finish_time: range.finishTime,
    },
  })
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">Empty Room Enquiry</p>

      <div class="form-row">
        <div class="field">
          <label class="lbl">Room</label>
          <select v-model="roomCode" class="input">
            <option :value="ALL_ROOMS">All Rooms</option>
            <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>

        <div class="field">
          <label class="lbl">Date</label>
          <input v-model="queryDate" type="date" class="input" />
        </div>

        <button class="btn" @click="search" :disabled="state === 'loading'">
          <span v-if="state === 'loading'" class="spinner"></span>
          {{ state === 'loading' ? 'Searching…' : 'Search' }}
        </button>
      </div>
    </div>

    <div v-if="state === 'error'" class="msg error-box">{{ errMsg }}</div>
    <div v-else-if="state === 'empty'" class="msg muted">No empty rooms found for {{ queryDate }}.</div>

    <div v-if="state === 'done'" class="results">
      <div v-for="group in grouped" :key="group.roomcode" class="card room-card">
        <div class="room-header">
          <span class="room-badge">{{ group.roomcode }}</span>
        </div>
        <div class="ranges">
          <button
            v-for="(r, i) in group.ranges"
            :key="i"
            type="button"
            class="time-badge"
            @click="goBook(r)"
          >
            {{ queryDate }} · {{ r.startTime }} – {{ r.finishTime }}
          </button>
        </div>
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
  gap: 0.6rem;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 0.85rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
}

.card-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin: 0 0 1rem;
}

.form-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
  min-width: 140px;
}

.lbl {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}

.input {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.95rem;
  padding: 0.55rem 0.75rem;
  outline: none;
  transition: border-color .15s;
  color-scheme: light;
}
.input:focus { border-color: #3b82f6; }

.btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.55rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  height: fit-content;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.spinner {
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg   { padding: 0.65rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; width: 98%; margin: 0 auto; box-sizing: border-box; }
.muted { color: #64748b; }
.error-box { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

.results { display: flex; flex-direction: column; gap: 0.6rem; }

.room-card { display: flex; flex-direction: column; gap: 0.5rem; }

.room-header { display: flex; align-items: center; }

.room-badge {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  background: #1d4ed8;
  color: #bfdbfe;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
}

.ranges { display: flex; flex-wrap: wrap; gap: 0.5rem; }

.time-badge {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--pill-success-text);
  font-family: monospace;
  background: rgba(74, 222, 128, .1);
  border: 1px solid #22c55e;
  padding: 0.25rem 0.6rem;
  border-radius: 0.4rem;
  cursor: pointer;
  transition: background .15s;
  -webkit-tap-highlight-color: transparent;
}
.time-badge:hover,
.time-badge:active {
  background: rgba(74, 222, 128, .25);
}
</style>
