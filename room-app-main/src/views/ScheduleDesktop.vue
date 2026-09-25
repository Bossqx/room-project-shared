<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import config from '../assets/config.json'
import SelfConfirmDesktop from './components/SelfConfirmDesktop.vue'


interface Period {
  period:     number
  startTime:  string
  finishTime: string
}

interface Teacher {
  officerid:      string
  officerlogin:   string
  prefixname:     string
  officername:    string
  officersurname: string
}

interface ScheduleItem {
  roomcode:       string
  weekday:        string
  timeperiodfrom: string
  timeperiodto:   string
  coursecode:     string
  coursename:     string
  teacher:        Teacher[]
  startTime:      string
  finishTime:     string
  id?:            string
  uuid?:          string
  isExist:        boolean
}

interface Cell {
  type: 'empty' | 'skip' | 'item'
  item?: ScheduleItem
  span?: number
}

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')
const MIN_PERIOD = 2
const MAX_PERIOD = 14
const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const router    = useRouter()
const route     = useRoute()
const userStore = useUserStore()

const showConfirmModal = ref(false)
const showSearchModal  = ref(false)

const rooms      = ref<string[]>([])
const roomCode   = ref('')
const periods    = ref<Period[]>([])
const anchorDate = ref(new Date().toISOString().slice(0, 10))

const state   = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const errMsg  = ref('')
const weekData = ref<Record<number, ScheduleItem[]>>({})

const nowMinutes    = ref(0)
const cancellingId  = ref<string | null>(null)
const confirmingId  = ref<string | null>(null)
const confirmCache  = ref<Record<string, { is_confirm_progress: boolean; usage_status: number }>>({})

const cancelMsg     = ref<{ uuid: string; ok: boolean; text: string } | null>(null)
let clockTimer: ReturnType<typeof setInterval> | null = null

function tickClock() {
  const now = new Date()
  nowMinutes.value = now.getHours() * 60 + now.getMinutes()
}



function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function canBookPeriod(dateStr: string, period: Period): boolean {
  const slot = new Date(`${dateStr}T${period.startTime}`)
  return slot.getTime() > Date.now()
}

function canConfirm(item?: ScheduleItem): boolean {
  if (!item || !item.startTime || !item.finishTime || !item.id || !item.uuid) return false
  if (item.teacher?.[0]?.officerlogin !== userStore.userName) return false
  return nowMinutes.value >= toMinutes(item.startTime) && nowMinutes.value <= toMinutes(item.finishTime)
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
  const confirmed = await askConfirm(item, 'confirm')
  if (!confirmed) return

  confirmingId.value = item.uuid
  try {
    await router.replace({ query: { ...route.query, schedule_id: item.id, uuid: item.uuid } })
    showConfirmModal.value = true
  } finally {
    confirmingId.value = null
  }
}

function closeConfirmModal() {
  showConfirmModal.value = false
  const { schedule_id, uuid, ...rest } = route.query
  router.replace({ query: rest })
}

const showBooking = inject<(startTime?: string, finishTime?: string) => void>('showBooking')

async function openBooking(item: ScheduleItem) {
  showBooking?.(item.startTime, item.finishTime)
}

async function openBookingForPeriod(period: Period) {
  showBooking?.(period.startTime, period.finishTime)
}

function getCurrentWeekday(): number {
  const day = new Date().getDay()
  let weekday = day === 0 ? 7 : day // ISO: Mon=1 … Sun=7
  weekday = weekday === 7 ? 1 : weekday + 1
  return weekday
}

function canCancel(item?: ScheduleItem): boolean {
  if (!item || parseInt(item.weekday, 10) !== getCurrentWeekday()) return false

  if (!item || !item.startTime || !item.finishTime) return false
  if (item.isExist) return false
  const isActive  = nowMinutes.value >= toMinutes(item.startTime)
                 && nowMinutes.value <= toMinutes(item.finishTime)
  const pastGrace = nowMinutes.value > toMinutes(item.startTime) + 15
  return isActive && pastGrace
}

async function sendCancelNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_cancel/?status=cancel_schedule`)
}



const confirmModal = ref<{
  show: boolean
  item: ScheduleItem | null
  kind: 'cancel' | 'confirm'
  resolve: ((v: boolean) => void) | null
}>({ show: false, item: null, kind: 'cancel', resolve: null })


function askConfirm(item: ScheduleItem, kind: 'cancel' | 'confirm' = 'cancel'): Promise<boolean> {
  return new Promise(resolve => {
    confirmModal.value = { show: true, item, kind, resolve }
  })
}

function modalAnswer(ok: boolean) {
  confirmModal.value.resolve?.(ok)
  confirmModal.value = { show: false, item: null, kind: 'cancel', resolve: null }
}

function modalBooking(ok: boolean) {
  // .value.resolve?.(ok)
  // confirmModal.value = { show: false, item: null, resolve: null }
}



async function confirmCancel(item: ScheduleItem) {
  const itemObj: ScheduleItem = JSON.parse(JSON.stringify(item))
 
  if (itemObj.uuid?.length) {
       const confirmed = await askConfirm(itemObj)
      if (!confirmed) return
       
        cancellingId.value = itemObj.uuid
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
          await sendCancelNotify()
          cancelMsg.value = { uuid: itemObj.uuid, ok: true,  text: 'Class cancelled successfully' }
        } catch (e) {
          cancelMsg.value   = { uuid: itemObj.uuid, ok: false, text: `Cancel failed: ${e}` }
        } finally {
          cancellingId.value = null
        }
  }
 
}

const visiblePeriods = computed(() =>
  periods.value.filter(p => p.period >= MIN_PERIOD && p.period <= MAX_PERIOD).sort((a, b) => a.period - b.period)
)

const weekDates = computed(() => {
  const base = new Date(anchorDate.value)
  const isoDay = base.getDay() === 0 ? 7 : base.getDay() // Mon=1 … Sun=7
  const monday = new Date(base)
  monday.setDate(base.getDate() - (isoDay - 1))
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d.toISOString().slice(0, 10)
  })
})

function buildRow(weekdayNum: number): Cell[] {
  const items = weekData.value[weekdayNum] ?? []
  const cells: Cell[] = visiblePeriods.value.map(() => ({ type: 'empty' }))

  for (const item of items) {
    const from = parseInt(item.timeperiodfrom, 10)
    const to   = parseInt(item.timeperiodto, 10)
    const startIdx = visiblePeriods.value.findIndex(p => p.period === from)
    if (startIdx === -1) continue
    const endIdx = visiblePeriods.value.findIndex(p => p.period === to)
    const span = (endIdx === -1 ? visiblePeriods.value.length - 1 : endIdx) - startIdx + 1

    cells[startIdx] = { type: 'item', item, span }
    for (let k = 1; k < span; k++) {
      if (startIdx + k < cells.length) cells[startIdx + k] = { type: 'skip' }
    }
  }
  return cells
}

const rows = computed(() =>
  Array.from({ length: 7 }, (_, i) => ({
    weekdayNum: i + 1,
    label:      WEEKDAY_LABELS[i],
    date:       weekDates.value[i],
    cells:      buildRow(i + 1),
  }))
)

async function loadRooms() {
  try {
    const res  = await fetch(`${apiBase}/room-usage/get_rooms`)
    const data = await res.json()
    rooms.value = (Array.isArray(data) ? data : []).map((r: { room_no: string }) => r.room_no)
    if (rooms.value.length) roomCode.value = rooms.value[0]
  } catch { /* rooms stay empty */ }
}

async function loadPeriods() {
  try {
    const res  = await fetch(`${apiBase}/room-usage/get_periods`)
    const data = await res.json()
    periods.value = Array.isArray(data) ? data : []
  } catch { /* periods stay empty */ }
}

async function loadWeek() {
  if (!roomCode.value) return
  state.value  = 'loading'
  errMsg.value = ''
  try {
    const results = await Promise.all(
      weekDates.value.map(async (date) => {
        const url = `${apiBase}/schedule/get_schedule_by_criteria/${encodeURIComponent(roomCode.value)}?schedule_date=${date}`
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: ScheduleItem[] = await res.json()
        return Array.isArray(data) ? data : []
      })
    )
    const next: Record<number, ScheduleItem[]> = {}
    results.forEach((items, i) => { next[i + 1] = items })
    weekData.value = next
    state.value = 'done'
    checkConfirmStatus(results.flat())
  } catch (e) {
    state.value  = 'error'
    errMsg.value = `Failed to fetch: ${e}`
  }
}

async function runSearch() {
  await loadWeek()
  showSearchModal.value = false
}

function teacherName(t: Teacher) {
  return `${t.prefixname}${t.officername} ${t.officersurname}`
}

const needsFullscreenGesture = ref(false)

async function requestFullscreen() {
  try {
    await document.documentElement.requestFullscreen()
    needsFullscreenGesture.value = false
  } catch {
    // Browsers reject programmatic fullscreen calls without a user gesture —
    // fall back to a button the user can click.
    needsFullscreenGesture.value = true
  }
}


function tryFullscreenOnFirstInteraction() {
  requestFullscreen()
}

let scheduleStreamSource: EventSource | null = null

function subscribeScheduleStream() {
  const url = `${apiBase}/mqtt-stream/subscribe/`
  scheduleStreamSource = new EventSource(url)
  scheduleStreamSource.onmessage = async (event) => {
    try {
      const parsed = JSON.parse(event.data)
      if (parsed?.status === 'booking_schedule' || parsed?.status === 'cancel_schedule') {
        await loadWeek()
      }
    } catch {
      // ignore malformed SSE payload
    }
  }
  scheduleStreamSource.onerror = () => {
    // browser auto-retries the SSE connection; nothing to do here
  }
}

onMounted(async () => {
  tickClock()
  clockTimer = setInterval(tickClock, 30_000)

  subscribeScheduleStream()

  await Promise.all([loadRooms(), loadPeriods()])
  await loadWeek()
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  scheduleStreamSource?.close()
  document.removeEventListener('click', tryFullscreenOnFirstInteraction)
  document.removeEventListener('keydown', tryFullscreenOnFirstInteraction)
})

</script>

<template>
  <div class="page">
  

    <div class="search-anchor">
      <button type="button" class="btn-open-search" aria-label="Search schedule room/date" title="Search schedule room/date" @click="showSearchModal = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        {{ roomCode || 'Select room' }} — {{ anchorDate }}
      </button>

      <div v-if="showSearchModal" class="search-popover-backdrop" @click="showSearchModal = false"></div>
      <div v-if="showSearchModal" class="search-popover">
        <button class="confirm-close" aria-label="Close" @click="showSearchModal = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>

        <div class="card">
          <p class="card-title">Weekly Room Schedule</p>

          <div class="form-row">
            <div class="field">
              <label class="lbl">Room</label>
              <select v-model="roomCode" class="input">
                <option value="" disabled>Select a room</option>
                <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
              </select>
            </div>

            <div class="field">
              <label class="lbl">Week of</label>
              <input v-model="anchorDate" type="date" class="input" />
            </div>

            <button type="button" class="btn-search" :disabled="!roomCode || state === 'loading'" @click="runSearch">
              <span v-if="state === 'loading'" class="spinner"></span>
              {{ state === 'loading' ? 'Searching…' : 'Search' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="state === 'error'" class="msg error-box">{{ errMsg }}</div>

    <div v-if="state === 'loading'" class="msg muted">Loading schedule…</div>

    <div v-if="state === 'done'" class="table-card">
      <div class="table-scroll">
        <table class="grid">
          <thead>
            <tr>
              <th class="day-head">Day</th>
              <th v-for="p in visiblePeriods" :key="p.period" class="period-head">
                <div class="period-no">P{{ String(p.period).padStart(2, '0') }}</div>
                <div class="period-time">{{ p.startTime }}–{{ p.finishTime }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.weekdayNum">
              <td class="day-cell">
                <div class="day-label">{{ row.label }}</div>
                <div class="day-date">{{ row.date }}</div>
              </td>
              <template v-for="(cell, idx) in row.cells" :key="idx">
                <td
                  v-if="cell.type !== 'skip'"
                  :colspan="cell.span || 1"
                  class="period-cell"
                  :class="{ filled: cell.type === 'item' }"
                >
                  <template v-if="cell.type === 'item' && cell.item">
                    <div class="course-code">{{ cell.item.coursecode }}</div>
                    <div class="course-name">{{ cell.item.coursename }}</div>
                    <div class="course-time">{{ cell.item.startTime }} – {{ cell.item.finishTime }}</div>
                    <div v-if="cell.item.teacher?.[0]" class="course-teacher">
                      {{ teacherName(cell.item.teacher[0]) }}
                    </div>
                    <template v-if="canConfirm(cell.item)">
                      <div
                        v-if="confirmCache[cell.item.uuid!]?.is_confirm_progress"
                        class="confirmed-badge-cell"
                      >
                        Class Confirmed
                      </div>
                      <button
                        v-else
                        class="btn-confirm-cell"
                        :disabled="confirmingId === cell.item.uuid"
                        @click="confirmClass(cell.item)"
                      >
                        {{ confirmingId === cell.item.uuid ? 'Confirming…' : 'Confirm' }}
                      </button>
                    </template>
                    <div
                      v-if="cancelMsg && cancelMsg.uuid === cell.item.uuid"
                      class="cancel-msg-cell"
                      :class="cancelMsg.ok ? 'ok' : 'fail'"
                    >
                      {{ cancelMsg.text }}
                    </div>
                    <button
                      v-if="canCancel(cell.item)"
                      class="btn-cancel-cell"
                      :disabled="cancellingId === cell.item.uuid"
                      @click="confirmCancel(cell.item)"
                    >
                      {{ cancellingId === cell.item.uuid ? 'Cancelling…' : 'Cancel Class' }}
                    </button>
                  
                  </template>
                  <template v-else>
                    <button
                      class="btn-book-empty"
                      :disabled="!canBookPeriod(row.date, visiblePeriods[idx])"
                      @click="openBookingForPeriod(visiblePeriods[idx])"
                    >
                      + Book
                    </button>
                  </template>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Confirm class popup -->
    <Teleport to="body">
      <div v-if="showConfirmModal" class="confirm-overlay" @click.self="closeConfirmModal">
        <div class="confirm-modal">
          <button class="confirm-close" aria-label="Close" @click="closeConfirmModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <SelfConfirmDesktop />
        </div>
      </div>
    </Teleport>

    <!-- Cancel class confirmation -->
    <Teleport to="body">
      <div v-if="confirmModal.show" class="booking-overlay" @click.self="modalAnswer(false)">
        <div class="modal">
          <div class="modal-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
          <p class="modal-title">{{ confirmModal.kind === 'confirm' ? 'Confirm Class?' : 'Cancel Class?' }}</p>
          <p class="modal-body">
            <strong>{{ confirmModal.item?.coursecode }}</strong> — {{ confirmModal.item?.coursename }}<br/>
            <span class="modal-time">{{ confirmModal.item?.startTime }} – {{ confirmModal.item?.finishTime }}</span>
          </p>
          <div class="modal-actions">
            <button class="modal-btn cancel" @click="modalAnswer(false)">{{ confirmModal.kind === 'confirm' ? 'Not Now' : 'Keep Class' }}</button>
            <button class="modal-btn confirm" @click="modalAnswer(true)">{{ confirmModal.kind === 'confirm' ? 'Yes, Confirm' : 'Yes, Cancel' }}</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<style scoped>
.page {
  position: fixed;
  inset: 0;
  width: 100vw;
  height: 100dvh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  padding: 4.5rem 1% 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  box-sizing: border-box;
  z-index: 10;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 0.85rem;
  width: 50%;
  margin: 0 0 0 0.9rem;
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
  min-width: 160px;
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

.btn-search {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
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
.btn-search:disabled { opacity: 0.4; cursor: not-allowed; }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.btn-open-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  align-self: flex-start;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  padding: 0.55rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-open-search svg { width: 16px; height: 16px; flex-shrink: 0; color: var(--accent-link); }
.btn-open-search:hover { border-color: #3b82f6; }

.msg   { padding: 0.65rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; width: 98%; margin: 0 auto; box-sizing: border-box; }
.muted { color: #64748b; }
.error-box { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

.fullscreen-prompt {
  background: var(--pill-amber-bg);
  color: var(--pill-amber-text);
  border: 1px solid #f59e0b;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-fullscreen {
  background: #f59e0b;
  color: #1e293b;
  border: none;
  border-radius: 0.4rem;
  padding: 0.4rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.btn-fullscreen:hover { background: #fbbf24; }

.table-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-scroll {
  overflow: auto;
  flex: 1;
}

.grid {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
}

.day-head,
.period-head {
  background: var(--bg-page);
  border: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  text-align: center;
  font-size: 0.7rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.day-head { width: 90px; }

.period-no  { font-weight: 700; color: var(--accent-link); }
.period-time { font-family: monospace; font-size: 0.65rem; margin-top: 0.15rem; }

.day-cell {
  border: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  text-align: center;
  background: var(--bg-page);
  vertical-align: middle;
}

.day-label { font-weight: 700; font-size: 0.8rem; }
.day-date  { font-family: monospace; font-size: 0.65rem; color: #64748b; margin-top: 0.15rem; }

.period-cell {
  border: 1px solid var(--border);
  padding: 0.4rem 0.5rem;
  vertical-align: top;
  min-width: 90px;
  height: 110px;
}

.period-cell.filled {
  background: rgba(59,130,246,.1);
}

.course-code {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--accent-link);
  font-family: monospace;
}

.course-name {
  font-size: 0.72rem;
  color: var(--text-primary);
  line-height: 1.3;
  margin-top: 0.1rem;
}

.course-time {
  font-size: 0.62rem;
  font-family: monospace;
  color: var(--text-secondary);
  margin-top: 0.2rem;
}

.course-teacher {
  font-size: 0.62rem;
  color: var(--text-secondary);
  margin-top: 0.1rem;
}

.btn-confirm-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  border: none;
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: 0.62rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-confirm-cell:hover:not(:disabled) { opacity: 0.9; }
.btn-confirm-cell:disabled { opacity: 0.4; cursor: not-allowed; }

.confirmed-badge-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: var(--pill-success-bg);
  border: 1px solid #22c55e;
  color: var(--pill-success-text);
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: 0.6rem;
  font-weight: 700;
  text-align: center;
}

.btn-cancel-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: transparent;
  border: 1px solid #ef4444;
  color: var(--pill-error-text);
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: 0.62rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-cancel-cell:hover:not(:disabled) { background: rgba(239,68,68,.1); }
.btn-cancel-cell:disabled { opacity: 0.4; cursor: not-allowed; }

.link-booking-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: transparent;
  border: none;
  color: var(--accent-link);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  cursor: pointer;
  text-align: center;
}
.link-booking-cell:hover { color: var(--accent-link-hover); text-decoration: underline; }

.btn-book-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 40px;
  background: transparent;
  border: 1px dashed var(--border);
  border-radius: 0.35rem;
  color: var(--text-secondary);
  font-size: 0.65rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-book-empty:hover:not(:disabled) {
  border-color: #3b82f6;
  color: var(--accent-link);
  background: rgba(59,130,246,.08);
}
.btn-book-empty:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.cancel-msg-cell {
  margin-top: 0.3rem;
  padding: 0.2rem 0.35rem;
  border-radius: 0.35rem;
  font-size: 0.58rem;
  font-weight: 600;
}
.cancel-msg-cell.ok   { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e; }
.cancel-msg-cell.fail { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }

/* ── Confirm class popup ── */
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, .65);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  z-index: 1000;
}

.confirm-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 1rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
}

.confirm-modal :deep(.page) {
  min-height: 0;
}

.search-anchor {
  position: relative;
  align-self: flex-start;
}

.search-popover-backdrop {
  position: fixed;
  inset: 0;
  z-index: 998;
}

.search-popover {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  z-index: 999;
  width: 340px;
  max-width: 90vw;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
  padding: 1.5rem;
  box-sizing: border-box;
}
.search-popover .card {
  width: 100%;
  margin: 0;
}
.search-popover .form-row {
  flex-direction: column;
  align-items: stretch;
}

.confirm-close {
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
  z-index: 1;
}
.confirm-close svg { width: 16px; height: 16px; }
.confirm-close:hover { background: #334155; }

/* ── Cancel class confirmation ── */
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

/* ── Booking popup ── */
.booking-overlay {
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

.booking-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 1rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
}

.booking-modal :deep(.page) {
  min-height: 0 !important;
  height: auto !important;
  width: auto !important;
  position: static !important;
  inset: auto !important;
}

.booking-close {
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
  z-index: 1;
}
.booking-close svg { width: 16px; height: 16px; }
.booking-close:hover { background: #334155; }

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
