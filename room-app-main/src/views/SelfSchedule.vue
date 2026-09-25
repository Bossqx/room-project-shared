<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '../stores/user'
import { useRouter } from 'vue-router'
import config from "../assets/config.json"


interface Teacher {
  officerid:      string
  officerlogin:   string
  prefixname:     string
  officername:    string
  officersurname: string
}


interface ScheduleItem {
  id:string 
  roomcode:       string
  coursecode:     string
  coursename:     string
  startTime:      string
  finishTime:     string
  teacher:        Teacher[]
  uuid?:          string
  isExist?:       boolean
  source?:        string
}

const userStore      = useUserStore()
const router    = useRouter()
//const route     = useRoute()
const apiBase = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')
const queryDate      = ref(new Date().toISOString().slice(0, 10))
const results        = ref<ScheduleItem[]>([])
const state          = ref<'idle' | 'loading' | 'empty' | 'done' | 'error'>('idle')
const errMsg         = ref('')
const nowMinutes     = ref(0)
const confirmCache   = ref<Record<string, { is_confirm_progress: boolean; usage_status: number }>>({})
const confirmingId   = ref<string | null>(null)
const cancellingId   = ref<string | null>(null)
const cancelMsg      = ref<{ uuid: string; ok: boolean; text: string } | null>(null)

let clockTimer: ReturnType<typeof setInterval> | null = null

function toMinutes(t: string) {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function isActive(item: ScheduleItem) {
  if (!item.startTime || !item.finishTime) return false
  return nowMinutes.value >= toMinutes(item.startTime) && nowMinutes.value <= toMinutes(item.finishTime)
}

function tickClock() {
  const now = new Date()
  nowMinutes.value = now.getHours() * 60 + now.getMinutes()
}

async function checkConfirmStatus(items: ScheduleItem[]) {
  await Promise.all(items.filter(i => i.uuid).map(async i => {
    try {
      const res  = await fetch(`${apiBase}/room-usage/get_is_confirm_progress/?uuid=${i.uuid}`)
      const data = await res.json()
      confirmCache.value = { ...confirmCache.value, [i.uuid!]: data }
    } catch { /* leave uncached */ }
  }))
}

async function confirmClass(item: ScheduleItem) {
  if (!item.uuid) return
  confirmingId.value = item.uuid
  try {

    router.push(`/self-confirm?schedule_id=${item.id}&uuid=${item.uuid}`)
 
  } finally {
    confirmingId.value = null
  }
}

onUnmounted(() => { if (clockTimer) clearInterval(clockTimer) })

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 60_000)
  search()
})

async function cancelNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_cancel/?status=cancel_schedule`)
}

const confirmModal = ref<{
  show: boolean
  item: ScheduleItem | null
  resolve: ((v: boolean) => void) | null
}>({ show: false, item: null, resolve: null })

function askConfirm(item: ScheduleItem): Promise<boolean> {
  return new Promise(resolve => {
    confirmModal.value = { show: true, item, resolve }
  })
}

function modalAnswer(ok: boolean) {
  confirmModal.value.resolve?.(ok)
  confirmModal.value = { show: false, item: null, resolve: null }
}

async function confirmCancel(item: ScheduleItem) {
  if (!item.uuid) return
  const confirmed = await askConfirm(item)
  if (!confirmed) return
  cancellingId.value = item.uuid
  cancelMsg.value    = null
  try {
    const res = await fetch(`${apiBase}/room-cancel/cancel_room`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uuid:         item.uuid,
        request_user: userStore.userName,
        room_no:      item.roomcode,
        created_date: new Date().toISOString(),
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    cancelMsg.value = { uuid: item.uuid, ok: true,  text: 'Class cancelled successfully' }
    await cancelNotify()
  } catch (e) {
    cancelMsg.value   = { uuid: item.uuid, ok: false, text: `Cancel failed: ${e}` }
  } finally {
    cancellingId.value = null
  }
}

async function search() {
  if (!userStore.userName) return
  state.value   = 'loading'
  errMsg.value  = ''
  results.value = []
  try {
    const url = `${apiBase}/schedule/get_rooms_by_user/user/${encodeURIComponent(userStore.userName)}?schedule_date=${queryDate.value}`
    const res  = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: ScheduleItem[] = await res.json()
    results.value = Array.isArray(data) ? data : []
    state.value   = results.value.length ? 'done' : 'empty'
    if (results.value.length) checkConfirmStatus(results.value)
  } catch (e) {
    state.value  = 'error'
    errMsg.value = `Failed to fetch: ${e}`
  }
}

function teacherName(t: Teacher) {
  return `${t.prefixname}${t.officername} ${t.officersurname}`
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div class="card form-card">
      <div class="form-header">
        <div>
          <p class="card-title">My Schedule</p>
          <p class="user-name">{{ userStore.userName }}</p>
        </div>
        <div class="date-wrap">
          <label class="lbl">Date</label>
          <input v-model="queryDate" type="date" class="date-input" @change="search" />
        </div>
      </div>
    </div>

    <!-- States -->
    <div v-if="state === 'error'"    class="msg error-box">{{ errMsg }}</div>
    <div v-else-if="state === 'loading'" class="msg muted">
      <span class="spinner"></span> Loading…
    </div>
    <div v-else-if="state === 'empty'" class="msg muted">
      No schedule found for {{ queryDate }}.
    </div>

    <!-- Results -->
    <div v-if="state === 'done'" class="results">
      <div v-for="item in results" :key="(item.uuid ?? item.coursecode) + item.startTime" class="card result-card">

        <div class="result-header">
          <span class="room-badge">{{ item.roomcode }}</span>
          <span class="time-badge">{{ item.startTime }} – {{ item.finishTime }}</span>
          <span v-if="item.source === 'booking'" class="booking-badge">Booking</span>
          <span v-if="isActive(item)" class="active-badge">Active</span>
        </div>

        <p class="course-code">{{ item.coursecode }}</p>
        <p class="course-name">{{ item.coursename }}</p>

        <div class="divider"></div>

        <div v-for="t in item.teacher" :key="t.officerid" class="teacher-row">
          <svg class="teacher-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
          </svg>
          <span class="teacher-name">{{ teacherName(t) }}</span>
        </div>

        <template v-if="isActive(item) && item.uuid">
          <!-- Already confirmed -->
          <div v-if="confirmCache[item.uuid]?.is_confirm_progress" class="confirmed-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            Class Confirmed
          </div>
          <!-- Confirm button -->
          <button v-else class="btn-confirm"
            :disabled="confirmingId === item.uuid"
            @click="confirmClass(item)">
            <span v-if="confirmingId === item.uuid" class="spinner"></span>
            {{ confirmingId === item.uuid ? 'Confirming…' : 'Confirm Class' }}
          </button>
        </template>

        <!-- Cancel button — visible while class has not yet finished -->
        <template v-if="item.uuid && nowMinutes < toMinutes(item.finishTime)">
          <div v-if="cancelMsg?.uuid === item.uuid" :class="['cancel-msg', cancelMsg.ok ? 'ok' : 'err']">
            {{ cancelMsg.text }}
          </div>
          <button v-else class="btn-cancel"
            :disabled="cancellingId === item.uuid"
            @click="confirmCancel(item)">
            <span v-if="cancellingId === item.uuid" class="spinner"></span>
            {{ cancellingId === item.uuid ? 'Cancelling…' : 'Cancel Class' }}
          </button>
        </template>

      </div>
    </div>

    <!-- Cancel class confirmation -->
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
            <strong>{{ confirmModal.item?.coursecode }}</strong> in room {{ confirmModal.item?.roomcode }}<br/>
            <span class="modal-time">{{ confirmModal.item?.startTime }} – {{ confirmModal.item?.finishTime }}</span>
          </p>
          <div class="modal-actions">
            <button class="modal-btn cancel" @click="modalAnswer(false)">Keep Class</button>
            <button class="modal-btn confirm" @click="modalAnswer(true)">Yes, Cancel</button>
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
 padding: 1.25rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  width: 100%;
  box-sizing: border-box;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.9rem;
  padding: 1.1rem;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.card-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin: 0;
}

.form-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
}

.user-name { font-size: 1.05rem; font-weight: 700; color: var(--accent-link); margin: 0.25rem 0 0; }

.date-wrap { display: flex; flex-direction: column; gap: 0.3rem; }
.lbl       { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
.date-input {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 0.95rem;
  padding: 0.5rem 0.8rem;
  outline: none;
  color-scheme: light;
}
.date-input:focus { border-color: #3b82f6; }

/* Messages */
.msg   { padding: 0.75rem 1rem; border-radius: 0.5rem; font-size: 1rem; display: flex; align-items: center; gap: 0.5rem; }
.muted { color: #64748b; }
.error-box { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,.2);
  border-top-color: var(--accent-link);
  border-radius: 50%;
  animation: spin .6s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Results */
.results { display: flex; flex-direction: column; gap: 0.75rem; }
.result-card { display: flex; flex-direction: column; gap: 0.6rem; }

.result-header { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }

.room-badge {
  font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em;
  background: #1d4ed8; color: #bfdbfe;
  padding: 0.25rem 0.7rem; border-radius: 999px;
}
.booking-badge {
  font-size: 0.65rem; font-weight: 600;
  background: rgba(16,185,129,.15); color: #34d399;
  border: 1px solid #10b981;
  padding: 0.15rem 0.5rem; border-radius: 999px;
}
.time-badge { font-size: 0.95rem; font-weight: 600; color: var(--text-secondary); font-family: monospace; flex: 1; }

.course-code { font-size: 0.9rem; font-weight: 700; color: var(--accent-link); margin: 0; font-family: monospace; }
.course-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0; line-height: 1.4; }

.divider { height: 1px; background: #334155; }

.teacher-row { display: flex; align-items: center; gap: 0.5rem; }
.teacher-icon { width: 16px; height: 16px; color: var(--text-secondary); flex-shrink: 0; }
.teacher-name { font-size: 0.95rem; color: var(--text-secondary); }

.active-badge {
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
  background: rgba(34,197,94,.15); color: var(--pill-success-text);
  border: 1px solid #22c55e;
  padding: 0.2rem 0.65rem; border-radius: 999px;
  animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:.6 } }

.confirmed-badge {
  display: flex; align-items: center; gap: 0.4rem;
  background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e;
  border-radius: 0.5rem; padding: 0.45rem 0.75rem;
  font-size: 0.85rem; font-weight: 600;
}
.confirmed-badge svg { width: 16px; height: 16px; flex-shrink: 0; }

.btn-confirm {
  display: flex; align-items: center; justify-content: center; gap: 0.4rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff; border: none; border-radius: 0.5rem;
  padding: 0.55rem 1rem; font-size: 0.9rem; font-weight: 600;
  cursor: pointer; width: 100%;
}
.btn-confirm:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-cancel {
  display: flex; align-items: center; justify-content: center; gap: 0.4rem;
  background: transparent;
  color: var(--pill-error-text); border: 1px solid #ef4444; border-radius: 0.5rem;
  padding: 0.45rem 1rem; font-size: 0.85rem; font-weight: 600;
  cursor: pointer; width: 100%;
}
.btn-cancel:disabled { opacity: 0.4; cursor: not-allowed; }

.cancel-msg { padding: 0.45rem 0.75rem; border-radius: 0.5rem; font-size: 0.85rem; font-weight: 500; }
.cancel-msg.ok  { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e; }
.cancel-msg.err { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

/* ── Cancel confirmation popup ── */
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
</style>
