<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '../stores/user'
import config from "../assets/config.json"
import type { Teacher, ScheduleItem, ScheduleItemDB } from '../types/schedule'

interface WeekDay {
  date:     string
  schedule: ScheduleItem[]
}

interface WeekDayDB {
  date:     string
  schedule: ScheduleItemDB[]
}

const apiBase = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')
const roomCode    = ref('')
const rooms       = ref<string[]>([])
const queryDate   = ref(new Date().toISOString().slice(0, 10))
const results     = ref<ScheduleItemDB[]>([])
const state       = ref<'idle' | 'loading' | 'empty' | 'done' | 'error'>('idle')
const errMsg      = ref('')
const nowMinutes   = ref(0)

const activeTab   = ref<'current' | 'week'>('current')
const weekResults = ref<WeekDayDB[]>([])
const weekState   = ref<'idle' | 'loading' | 'empty' | 'done' | 'error'>('idle')
const weekErrMsg  = ref('')
const cancellingId = ref<number | null>(null)
const cancelMsg    = ref<{ schedule_id: number; ok: boolean; text: string } | null>(null)
const existCache   = ref<Record<string, boolean>>({})





const confirmModal = ref<{
  show: boolean
  item: ScheduleItem | ScheduleItemDB | null
  resolve: ((v: boolean) => void) | null
}>({ show: false, item: null, resolve: null })

function askConfirm(item: ScheduleItem | ScheduleItemDB): Promise<boolean> {
  return new Promise(resolve => {
    confirmModal.value = { show: true, item, resolve }
  })
}
function modalAnswer(ok: boolean) {
  confirmModal.value.resolve?.(ok)
  confirmModal.value = { show: false, item: null, resolve: null }
}

const userStore = useUserStore()

function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function canCancel(item: ScheduleItem | ScheduleItemDB): boolean {
  if (!item.startTime || !item.finishTime) return false
  if (item.isExist) return false
  if ('schedule_date' in item && item.schedule_date) {
    const todayStr = new Date().toISOString().slice(0, 10)
    if (item.schedule_date.slice(0, 10) !== todayStr) return false
  }
  const isActive  = nowMinutes.value >= toMinutes(item.startTime)
                 && nowMinutes.value <= toMinutes(item.finishTime)
  const pastGrace = nowMinutes.value > toMinutes(item.startTime) + 15
  return isActive && pastGrace
}


let clockTimer: ReturnType<typeof setInterval> | null = null

function tickClock() {
  const now = new Date()
  nowMinutes.value = now.getHours() * 60 + now.getMinutes()
}

onUnmounted(() => { if (clockTimer) clearInterval(clockTimer) })

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 60_000)
  try {
    const res  = await fetch(`${apiBase}/schedule/get_list_current_rooms/`)
    const data = await res.json()
    rooms.value = (Array.isArray(data) ? data : []).map((r: { roomCode: string }) => r.roomCode)
    if (rooms.value.length) {
      roomCode.value = rooms.value[0]
      runSearch()
    }
  } catch { /* rooms stay empty */ }
})

async function search() {
  if (!roomCode.value) return
  state.value  = 'loading'
  errMsg.value = ''
  results.value = []
  try {
    const url=`${apiBase}/schedule/get_schedule_by_criteria_db/${encodeURIComponent(roomCode.value)}?schedule_date=${queryDate.value}`
    const res  = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: ScheduleItemDB[] = await res.json()
    results.value = Array.isArray(data) ? data : []
    state.value   = results.value.length ? 'done' : 'empty'
  } catch (e) {
    state.value  = 'error'
    errMsg.value = `Failed to fetch: ${e}`
  }
}

async function searchWeek() {
  if (!roomCode.value) return
  weekState.value   = 'loading'
  weekErrMsg.value  = ''
  weekResults.value = []
  try {
    const url = `${apiBase}/schedule/get_schedule_by_weekly_db/`

    //console.log(url);
    
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: WeekDayDB[] = await res.json()
    weekResults.value = Array.isArray(data) ? data : []
    weekState.value   = weekResults.value.some(d => d.schedule.length) ? 'done' : 'empty'
  } catch (e) {
    weekState.value  = 'error'
    weekErrMsg.value = `Failed to fetch: ${e}`
  }
}

function selectTab(tab: 'current' | 'week') {
  activeTab.value = tab
  if (tab === 'week' && weekState.value === 'idle') searchWeek()
}

function runSearch() {
  if (activeTab.value === 'week') searchWeek()
  else search()
}

function formatScheduleDate(dateStr?: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('th-TH', { day: 'numeric', month: 'short', year: 'numeric' })
}

function formatDayLabel(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('th-TH', { weekday: 'short', day: 'numeric', month: 'short' })
}

function teacherName(t: Teacher) {
  return `${t.prefixname}${t.officername} ${t.officersurname}`
}

async function sendCancelNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_cancel/?status=cancel_schedule`)
}


async function confirmCancel(item: ScheduleItem | ScheduleItemDB) {
  console.log(item);
  const hasScheduleId = 'schedule_id' in item && item.schedule_id != null
  console.log('has schedule_id:', hasScheduleId);
  if (!item.schedule_id) return
  const confirmed = await askConfirm(item)
  if (!confirmed) return
  cancellingId.value = item.schedule_id
  cancelMsg.value    = null
  try {
    const url=`${apiBase}/room-cancel/cancel_room`
    //console.log(url);
    const payload =JSON.stringify({ 
      uuid:         String(item.schedule_id),
      request_user: userStore.userName,
      room_no:      item.roomcode,
      source_type:item.objective,
      created_date: new Date().toISOString(),
    })
    console.log(payload);
    const res = await fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
    })
    
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await sendCancelNotify()
    cancelMsg.value = { schedule_id: item.schedule_id, ok: true,  text: 'Class cancelled successfully' }
  } catch (e) {
    cancelMsg.value   = { schedule_id: item.schedule_id, ok: false, text: `Cancel failed: ${e}` }
  } finally {
    cancellingId.value = null
  }
}
</script>

<template>
  <div class="page">
    <!-- Query form -->
    <div class="card">
      <p class="card-title">Room Schedule Enquiry</p>

      <div class="form-row">
        <div class="field">
          <label class="lbl">Room Code</label>
          <select v-model="roomCode" class="input">
            <option value="" disabled>Select a room</option>
            <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>


        <button class="btn" @click="runSearch" :disabled="!roomCode || (activeTab === 'current' ? state : weekState) === 'loading'">
          <span v-if="(activeTab === 'current' ? state : weekState) === 'loading'" class="spinner"></span>
          {{ (activeTab === 'current' ? state : weekState) === 'loading' ? 'Searching…' : 'Search' }}
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'current' }" @click="selectTab('current')">Current Schedule</button>
      <button class="tab" :class="{ active: activeTab === 'week' }" @click="selectTab('week')">Week Schedule</button>
    </div>

    <template v-if="activeTab === 'current'">
      <!-- States -->
      <div v-if="state === 'error'"   class="msg error-box">{{ errMsg }}</div>
      <div v-else-if="state === 'empty'" class="msg muted">No schedule found for this room on {{ queryDate }}.</div>

      <!-- Results -->
      <div v-if="state === 'done'" class="results">
        <template v-for="item in results" :key="item.coursecode + item.timeperiodfrom">
        <div
          v-if="!item.uuid || existCache[item.uuid] !== true"
          class="card result-card"
        >

          <div class="result-header">
            <span class="room-badge">{{ item.roomcode }}</span>
            <span class="time-badge">{{ formatScheduleDate(item.schedule_date) }} · {{ item.startTime }} – {{ item.finishTime }}</span>
          </div>

          <p class="course-code">{{ item.coursecode }}</p>
          <p class="course-name">{{ item.coursename }}</p>

          <div class="divider"></div>

          <div v-if="item.teacher_name" class="teacher-row">
            <svg class="teacher-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
            <span class="teacher-name">{{ item.teacher_name }}</span>
          </div>

          <div v-if="cancelMsg && cancelMsg.schedule_id === item.schedule_id"
               class="cancel-msg" :class="cancelMsg.ok ? 'ok' : 'fail'">
            {{ cancelMsg.text }}
          </div>

          <button
            v-if="canCancel(item)"
            class="btn-cancel-class"
            :disabled="cancellingId === item.schedule_id"
            @click="confirmCancel(item)"
          >
            <span v-if="cancellingId === item.schedule_id" class="spinner"></span>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            {{ cancellingId === item.schedule_id ? 'Cancelling…' : 'Cancel Class' }}
          </button>

        </div>
        </template>
      </div>
    </template>

    <template v-else>
      <!-- States -->
      <div v-if="weekState === 'error'"   class="msg error-box">{{ weekErrMsg }}</div>
      <div v-else-if="weekState === 'empty'" class="msg muted">No schedule found for this room this week.</div>

      <!-- Results, grouped by day -->
      <div v-if="weekState === 'done'" class="results">
        <template v-for="day in weekResults" :key="day.date">
          <div v-if="day.schedule.length" class="day-group">
            <p class="day-header">{{ formatDayLabel(day.date) }} · {{ day.date }}</p>

            <div
              v-for="item in day.schedule"
              :key="item.coursecode + item.timeperiodfrom"
              class="card result-card"
            >
              <div class="result-header">
                <span class="room-badge">{{ item.roomcode }}</span>
                <span class="time-badge">{{ formatScheduleDate(item.schedule_date) }} · {{ item.startTime }} – {{ item.finishTime }}</span>
              </div>

              <p class="course-code">{{ item.coursecode }}</p>
              <p class="course-name">{{ item.coursename }}</p>

              <div class="divider"></div>

              <div v-if="item.teacher_name" class="teacher-row">
                <svg class="teacher-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round"
                    d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                </svg>
                <span class="teacher-name">{{ item.teacher_name }}</span>
              </div>

              <div v-if="cancelMsg && cancelMsg.schedule_id === item.schedule_id"
                   class="cancel-msg" :class="cancelMsg.ok ? 'ok' : 'fail'">
                {{ cancelMsg.text }}
              </div>

              <button
                v-if="canCancel(item)"
                class="btn-cancel-class"
                :disabled="cancellingId === item.schedule_id"
                @click="confirmCancel(item)"
              >
                <span v-if="cancellingId === item.schedule_id" class="spinner"></span>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round"
                    d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                {{ cancellingId === item.schedule_id ? 'Cancelling…' : 'Cancel Class' }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </template>
  </div>

  <!-- Confirm cancel modal -->
  <Teleport to="body">
    <div v-if="confirmModal.show" class="modal-overlay" @click.self="modalAnswer(false)">
      <div class="modal">
        <div class="modal-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
        </div>
        <p class="modal-title">Cancel Class?</p>
        <p class="modal-body">
          <strong>{{ confirmModal.item?.coursecode }}</strong> — {{ confirmModal.item?.coursename }}<br/>
          <span class="modal-time">{{ confirmModal.item?.startTime }} – {{ confirmModal.item?.finishTime }}</span>
        </p>
        <div class="modal-actions">
          <button class="modal-btn cancel" @click="modalAnswer(false)">Keep Class</button>
          <button class="modal-btn confirm" @click="modalAnswer(true)">Yes, Cancel</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.page {
  min-height: 150vh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  padding: 11rem 1% 1.25rem;
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

/* Form */
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

/* Messages */
.msg   { padding: 0.65rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; }
.muted { color: #64748b; }
.error-box { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

/* Tabs */
.tabs {
  display: flex;
  gap: 0.5rem;
  width: 98%;
  margin: 0 auto;
}

.tab {
  flex: 1;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  border-radius: 0.5rem;
  padding: 0.6rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: color .15s, border-color .15s, background .15s;
}
.tab.active {
  background: #1d4ed8;
  border-color: var(--accent-link);
  color: #fff;
}

/* Week schedule grouping */
.day-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.day-header {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  margin: 0.25rem 0 0;
}

/* Results */
.results {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 70vh;
  max-height: 70dvh;
  overflow-y: auto;
  padding-right: 0.4rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}
.results::-webkit-scrollbar { width: 6px; }
.results::-webkit-scrollbar-track { background: transparent; }
.results::-webkit-scrollbar-thumb { background: #334155; border-radius: 999px; }

.result-card { display: flex; flex-direction: column; gap: 0.5rem; }

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.room-badge {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  background: #1d4ed8;
  color: #bfdbfe;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
}

.time-badge {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  font-family: monospace;
}

.course-code {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--accent-link);
  margin: 0;
  font-family: monospace;
}

.course-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.4;
}

.divider { height: 1px; background: #334155; }

.teacher-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.teacher-icon { width: 14px; height: 14px; color: var(--text-secondary); flex-shrink: 0; }

.teacher-name {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.btn-cancel-class {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.25rem;
  background: rgba(239,68,68,.1);
  border: 1px solid #ef4444;
  color: var(--pill-error-text);
  border-radius: 0.5rem;
  padding: 0.45rem 0.9rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  justify-content: center;
}
.btn-cancel-class svg { width: 16px; height: 16px; flex-shrink: 0; }
.btn-cancel-class:hover { background: rgba(239,68,68,.2); }
.btn-cancel-class:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Confirm modal ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.6);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 999;
}
.modal {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1.25rem;
  padding: 2rem 1.75rem 1.5rem;
  width: 88%; max-width: 340px;
  display: flex; flex-direction: column; align-items: center; gap: 0.75rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.6);
  animation: pop .2s ease;
}
@keyframes pop {
  from { transform: scale(.85); opacity: 0; }
  to   { transform: scale(1);   opacity: 1; }
}
.modal-icon svg { width: 48px; height: 48px; color: #f97316; }
.modal-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.modal-body  { font-size: 0.875rem; color: var(--text-secondary); text-align: center; margin: 0; line-height: 1.6; }
.modal-body strong { color: var(--text-primary); }
.modal-time  { font-family: monospace; font-size: 0.8rem; color: var(--accent-link); }
.modal-actions { display: flex; gap: 0.75rem; width: 100%; margin-top: 0.5rem; }
.modal-btn { flex: 1; border: none; border-radius: 0.6rem; padding: 0.6rem; font-size: 0.9rem; font-weight: 600; cursor: pointer; }
.modal-btn.cancel  { background: var(--bg-surface); border: 1px solid var(--border); color: var(--text-secondary); }
.modal-btn.confirm { background: #ef4444; color: #fff; }
.modal-btn.confirm:hover { background: #dc2626; }

.cancel-msg { font-size: 0.8rem; font-weight: 600; padding: 0.4rem 0.75rem; border-radius: 0.4rem; }
.cancel-msg.ok   { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e; }
.cancel-msg.fail { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }
</style>
