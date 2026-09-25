<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import config from '../assets/config.json'
import SelfConfirmDesktop from './components/SelfConfirmDesktop.vue'
import { locale } from '../i18n'


interface Period {
  period:     number
  startTime:  string
  finishTime: string
  labelSTime?: string
  labelFTime?: string
}

interface Teacher {
  officerid:      string
  officerlogin:   string
  prefixname:     string
  officername:    string
  officersurname: string
}

interface ScheduleItem {
  schedule_id:string;
  roomcode:       string;
  weekday:        string;
  timeperiodfrom: string;
  timeperiodto:   string;
  coursecode:     string;
  coursename:     string;
  teacher?:       Teacher[];
  teacher_name?:  string;
  // MIS rows come back with `userCode`, booking rows with `user_code` —
  // the two branches of get_schedule_by_criteria_db spell it differently.
  userCode?:      string;
  user_code?:       string;
  schedule_date?: string;
  startTime:      string;
  finishTime:     string;
  id?:            string;
  uuid?:          string;
  isExist:        boolean;
  usage_status:number; 
  objective:string; 

}

interface Cell {
  type: 'empty' | 'skip' | 'item'
  item?: ScheduleItem
  span?: number
}

// get_schedule_from_json/ returns every room's schedule as a flat JSON
// snapshot — no weekday/period-column fields, and teacher_name comes back as
// either a plain string (MIS rows) or a Teacher[] (ad-hoc booking rows).
interface FullCalendarTeacher {
  officerid?:      string
  officerlogin?:   string
  prefixname?:     string
  officername?:    string
  officersurname?: string
}

interface FullCalendarItem {
  rowId:          number
  roomcode:       string
  coursecode:     string
  coursename:     string
  schedule_date:  string
  startTime:      string
  finishTime:     string
  userCode?:      string
  teacher_name?:  string | FullCalendarTeacher[]
}

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')
const MIN_PERIOD = 1
const MAX_PERIOD = 14
const WEEKDAY_LABELS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const WEEKDAY_LABELS_TH = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']

function weekdayLabel(index: number): string {
  return (locale.value === 'en' ? WEEKDAY_LABELS_EN : WEEKDAY_LABELS_TH)[index]
}

const router    = useRouter()
const route     = useRoute()
const userStore = useUserStore()

const showConfirmModal = ref(false)

const rooms      = ref<string[]>([])
const roomCode   = ref('')
const periods    = ref<Period[]>([])
const anchorDate = ref(new Date().toISOString().slice(0, 10))

// 'room' = existing single-room period grid; 'full' = all-rooms week agenda
const viewMode      = ref<'room' | 'full' | 'week'>('room')
const fullItems     = ref<FullCalendarItem[]>([])
const fullState     = ref<'idle' | 'loading' | 'error'>('idle')
const fullErrMsg    = ref('')
const fullLoaded    = ref(false)
const fullFloor     = ref('all')
const fullRoomQuery = ref('')
const expandedWeeklyItemId = ref<number | null>(null)

const state   = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const errMsg  = ref('')
const weekItems = ref<ScheduleItem[]>([])

const nowMinutes    = ref(0)
const cancellingId  = ref<string | null>(null)
const confirmingId  = ref<string | null>(null)
const confirmCache  = ref<Record<string, { is_confirm_progress: boolean; usage_status: number }>>({})

const cancelMsg     = ref<{ uuid: string; ok: boolean; text: string } | null>(null)
const deletingId    = ref<string | null>(null)
const deleteMsg     = ref<{ schedule_id: string; ok: boolean; text: string } | null>(null)
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

function isPastPeriod(dateStr: string, period: Period): boolean {
  const slotEnd = new Date(`${dateStr}T${period.finishTime}`)
  return slotEnd.getTime() <= Date.now()
}

function isActiveItem(item?: ScheduleItem, dateStr?: string): boolean {
  if (!item || !item.startTime || !item.finishTime) return false
  if (dateStr && dateStr !== new Date().toISOString().slice(0, 10)) return false
  return nowMinutes.value >= toMinutes(item.startTime) && nowMinutes.value <= toMinutes(item.finishTime)
}

function usageStatusLabel(item?: ScheduleItem): string {
  const status = Number(item?.usage_status)
  if (status === 3) return locale.value === 'en' ? 'In Use' : 'ยืนยันแล้ว'
  if (status === 4) return locale.value === 'en' ? 'Closed' : 'ปิดการใช้งานแล้ว'
  return ''
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

const showBooking = inject<(startTime?: string, finishTime?: string, roomCode?: string, bookingDate?: string) => void>('showBooking')

async function openBooking(item: ScheduleItem) {
  showBooking?.(item.startTime, item.finishTime, roomCode.value)
}

async function openBookingForPeriod(period: Period, dateStr: string) {
  showBooking?.(period.startTime, period.finishTime, roomCode.value, dateStr)
}

function openFullBooking(period: Period, room: string) {
  showBooking?.(period.startTime, period.finishTime, room, anchorDate.value)
}

function getCurrentWeekday(): number {
  const day = new Date().getDay()
  let weekday = day === 0 ? 7 : day // ISO: Mon=1 … Sun=7
  weekday = weekday === 7 ? 1 : weekday + 1
  return weekday
}

function canCancel(item?: ScheduleItem, dateStr?: string): boolean {
  if (!item || parseInt(item.weekday, 10) !== getCurrentWeekday()) return false

  if (!item.startTime || !item.finishTime) return false
  if (item.isExist) return false
  const status = Number(item.usage_status)
  if (status === 3 || status === 4) return false
  // isActiveItem also rejects the cell when its column date isn't today. The
  // weekday check above passes on the matching column of *any* week the grid
  // is anchored to, so without this a future week's slot looks cancellable.
  if (!isActiveItem(item, dateStr)) return false
  const pastGrace = nowMinutes.value > toMinutes(item.startTime) + 15
  return pastGrace
}

async function sendCancelNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_cancel/?status=cancel_schedule`)
}

// Owner of the slot, whichever spelling the API used for this row.
function itemOwner(item?: ScheduleItem): string {
  return (item?.userCode ?? item?.user_code ?? '').trim()
}

// Deletable when the signed-in user owns the slot and it hasn't happened yet.
// ISO yyyy-mm-dd strings compare lexicographically the same way they compare
// chronologically, so a plain >= is enough here.
function canDelete(item?: ScheduleItem, dateStr?: string): boolean {
  if (!item || !item.schedule_id) return false
  if (!userStore.userName || itemOwner(item) !== userStore.userName) return false
  const slotDate = (dateStr ?? item.schedule_date ?? '').slice(0, 10)
  if (!slotDate) return false
  return slotDate >= new Date().toISOString().slice(0, 10)
}

async function deleteSchedule(item: ScheduleItem) {
  if (!item.schedule_id) return
  const confirmed = await askConfirm(item, 'delete')
  if (!confirmed) return

  deletingId.value = item.schedule_id
  deleteMsg.value  = null
  try {
    const params = new URLSearchParams({
      schedule_id: String(item.schedule_id),
      // 'MIS Schedule' / 'booking' — delete_schedule_by_id normalizes both, and
      // passing the row's own source keeps bookings off the schedules table.
      source_type: item.objective,
    })
    const res = await fetch(`${apiBase}/schedule/delete_schedule_by_id/?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    // Broadcast on the same topic the cancel flow uses, so every open grid
    // reloads; this client also reloads directly rather than waiting on SSE.
    await sendCancelNotify()
    await loadWeek()
    deleteMsg.value = { schedule_id: item.schedule_id, ok: true, text: 'ลบตารางสำเร็จ' }
  } catch (e) {
    deleteMsg.value = { schedule_id: item.schedule_id, ok: false, text: `ไม่สามารถลบตารางได้: ${e}` }
  } finally {
    deletingId.value = null
  }
}



const confirmModal = ref<{
  show: boolean
  item: ScheduleItem | null
  kind: 'cancel' | 'confirm' | 'delete'
  resolve: ((v: boolean) => void) | null
}>({ show: false, item: null, kind: 'cancel', resolve: null })


// One entry per modal kind — keeps the three labels for a given action side by
// side instead of spread across three nested ternaries in the template.
const MODAL_WORDING = {
  cancel:  { title: 'ยืนยันการยกเลิกการใช้ห้องหรือไม่', dismiss: 'ไม่ยกเลิก', confirm: 'ยืนยันการยกเลิก' },
  confirm: { title: 'ยืนยันการเข้าใช้งานหรือไม่', dismiss: 'ไว้ภายหลัง', confirm: 'ยืนยันการเข้าใช้' },
  delete:  { title: 'ยืนยันการลบตารางหรือไม่', dismiss: 'ไม่ลบ', confirm: 'ยืนยันการลบ' },
} as const

const modalWording = computed(() => MODAL_WORDING[confirmModal.value.kind])

function askConfirm(item: ScheduleItem, kind: 'cancel' | 'confirm' | 'delete' = 'cancel'): Promise<boolean> {
  return new Promise(resolve => {
    confirmModal.value = { show: true, item, kind, resolve }
  })
}

function modalAnswer(ok: boolean) {
  confirmModal.value.resolve?.(ok)
  confirmModal.value = { show: false, item: null, kind: 'cancel', resolve: null }
}




async function confirmCancel(item: ScheduleItem) {
  const itemObj: ScheduleItem = JSON.parse(JSON.stringify(item))

  if (itemObj.schedule_id && !isNaN(Number(itemObj.schedule_id))) {
      //console.log(itemObj.schedule_id);

       const confirmed = await askConfirm(itemObj)
      if (!confirmed) return
       
        cancellingId.value = itemObj.schedule_id
        cancelMsg.value    = null
        try {
          const url=`${apiBase}/room-cancel/cancel_room`;
          //console.log(url);
          const payload=JSON.stringify({
              uuid:         String(item.schedule_id),
              request_user: userStore.userName,
              room_no:      item.roomcode,
              source_type: item.objective,
              created_date: new Date().toISOString(),
            });
            console.log(payload);
          const res = await fetch(url, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:payload ,
          })
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          await sendCancelNotify()
          cancelMsg.value = { uuid: itemObj.schedule_id, ok: true,  text: 'ยกเลิกการใช้ห้องสำเร็จ' }
        } catch (e) {
          cancelMsg.value   = { uuid: itemObj.schedule_id, ok: false, text: `ไม่สามารถยกเลิกได้: ${e}` }
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

const weekRangeLabel = computed(() => {
  const [start, , , , , , end] = weekDates.value
  const format = (value: string) => new Intl.DateTimeFormat(locale.value === 'en' ? 'en-GB' : 'th-TH', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
  return `${format(start)} – ${format(end)}`
})

const selectedDateLabel = computed(() => new Intl.DateTimeFormat(locale.value === 'en' ? 'en-GB' : 'th-TH', {
  weekday: 'long',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
}).format(new Date(`${anchorDate.value}T00:00:00`)))

function isToday(dateStr: string): boolean {
  return dateStr === new Date().toISOString().slice(0, 10)
}

function matchesWeekday(itemWeekday: string, weekdayNum: number): boolean {
  const shifted = weekdayNum === 7 ? 1 : weekdayNum + 1
  return parseInt(itemWeekday, 10) === shifted
}

function buildRow(weekdayNum: number): Cell[] {
  const items = weekItems.value.filter(item => matchesWeekday(item.weekday, weekdayNum))
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
    label:      weekdayLabel(i),
    date:       weekDates.value[i],
    cells:      buildRow(i + 1),
  }))
)

function fullCalendarTeacherLabel(item: FullCalendarItem): string {
  const t = item.teacher_name
  if (Array.isArray(t)) {
    const first = t[0]
    return first ? `${first.prefixname ?? ''}${first.officername ?? ''} ${first.officersurname ?? ''}`.trim() : ''
  }
  return t ?? ''
}

// Full dataset is a one-time snapshot spanning many months, so it's fetched
// once and cached — switching weeks just re-filters it client-side below.
async function loadFullCalendar() {
  if (fullLoaded.value) return
  fullState.value  = 'loading'
  fullErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/schedule/get_schedule_from_json/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    fullItems.value = Array.isArray(data) ? data : []
    fullLoaded.value = true
    fullState.value  = 'idle'
  } catch (e) {
    fullState.value  = 'error'
    fullErrMsg.value = `ไม่สามารถโหลดปฏิทินรวมได้: ${e}`
  }
}

async function setViewMode(mode: 'room' | 'full' | 'week') {
  viewMode.value = mode
  if (mode === 'full' || mode === 'week') await loadFullCalendar()
}

interface FullGridCell {
  type: 'empty' | 'skip' | 'item'
  items?: FullCalendarItem[]
  span?: number
}

function roomFloor(room: string): string {
  const segment = room.split('.')[1]
  if (!segment) return locale.value === 'en' ? 'Unspecified' : 'ไม่ระบุชั้น'
  const numeric = Number(segment)
  return Number.isFinite(numeric) ? String(numeric) : segment
}

const fullDayItems = computed(() => fullItems.value
  .filter(item => (item.schedule_date || '').slice(0, 10) === anchorDate.value)
  .sort((a, b) => a.startTime.localeCompare(b.startTime)))

const fullRoomCodes = computed(() => Array.from(new Set([
  ...rooms.value,
  ...fullDayItems.value.map(item => item.roomcode),
])).filter(Boolean).sort((a, b) => a.localeCompare(b, undefined, { numeric: true })))

const fullFloors = computed(() => Array.from(new Set(fullRoomCodes.value.map(roomFloor)))
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true })))

const selectableFullRooms = computed(() => fullRoomCodes.value.filter(room =>
  fullFloor.value === 'all' || roomFloor(room) === fullFloor.value))

function buildFullRoomCells(room: string): FullGridCell[] {
  const cells: FullGridCell[] = visiblePeriods.value.map(() => ({ type: 'empty' }))
  const items = fullDayItems.value.filter(item => item.roomcode === room)

  for (const item of items) {
    const startIdx = visiblePeriods.value.findIndex(period => period.finishTime > item.startTime)
    if (startIdx < 0) continue
    let endIdx = visiblePeriods.value.length - 1
    for (let i = startIdx; i < visiblePeriods.value.length; i++) {
      if (visiblePeriods.value[i].startTime >= item.finishTime) {
        endIdx = i - 1
        break
      }
    }
    const span = Math.max(1, endIdx - startIdx + 1)
    const existing = cells[startIdx]
    if (existing.type === 'item') {
      existing.items?.push(item)
      continue
    }
    if (existing.type === 'skip') continue
    cells[startIdx] = { type: 'item', items: [item], span }
    for (let offset = 1; offset < span; offset++) {
      if (startIdx + offset < cells.length) cells[startIdx + offset] = { type: 'skip' }
    }
  }
  return cells
}

const fullRoomGroups = computed(() => {
  const filteredRooms = fullRoomCodes.value.filter(room => {
    const matchesFloor = fullFloor.value === 'all' || roomFloor(room) === fullFloor.value
    const matchesQuery = !fullRoomQuery.value || room === fullRoomQuery.value
    return matchesFloor && matchesQuery
  })
  const groups = new Map<string, Array<{ room: string; cells: FullGridCell[] }>>()
  for (const room of filteredRooms) {
    const floor = roomFloor(room)
    if (!groups.has(floor)) groups.set(floor, [])
    groups.get(floor)!.push({ room, cells: buildFullRoomCells(room) })
  }
  return Array.from(groups, ([floor, roomRows]) => ({ floor, roomRows }))
})

const weeklyItems = computed(() => fullItems.value.filter(item =>
  weekDates.value.includes((item.schedule_date || '').slice(0, 10))))

const weeklyRoomCodes = computed(() => Array.from(new Set([
  ...rooms.value,
  ...weeklyItems.value.map(item => item.roomcode),
])).filter(Boolean).sort((a, b) => a.localeCompare(b, undefined, { numeric: true })))

const weeklyRoomGroups = computed(() => {
  const filteredRooms = weeklyRoomCodes.value.filter(room => {
    const matchesFloor = fullFloor.value === 'all' || roomFloor(room) === fullFloor.value
    const matchesRoom = !fullRoomQuery.value || room === fullRoomQuery.value
    return matchesFloor && matchesRoom
  })

  const groups = new Map<string, Array<{
    room: string
    days: Array<{ date: string; items: FullCalendarItem[] }>
  }>>()

  for (const room of filteredRooms) {
    const floor = roomFloor(room)
    if (!groups.has(floor)) groups.set(floor, [])
    groups.get(floor)!.push({
      room,
      days: weekDates.value.map(date => ({
        date,
        items: weeklyItems.value
          .filter(item => item.roomcode === room && (item.schedule_date || '').slice(0, 10) === date)
          .sort((a, b) => a.startTime.localeCompare(b.startTime)),
      })),
    })
  }

  return Array.from(groups, ([floor, roomRows]) => ({ floor, roomRows }))
    .sort((a, b) => a.floor.localeCompare(b.floor, undefined, { numeric: true }))
})

function weeklyDateLabel(date: string): string {
  return new Intl.DateTimeFormat(locale.value === 'en' ? 'en-GB' : 'th-TH', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(`${date}T00:00:00`))
}

function isFullItemPast(item: FullCalendarItem): boolean {
  const date = (item.schedule_date || '').slice(0, 10)
  return new Date(`${date}T${item.finishTime}`).getTime() <= Date.now()
}

function toggleWeeklyItem(rowId: number) {
  expandedWeeklyItemId.value = expandedWeeklyItemId.value === rowId ? null : rowId
}

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
    const url = `${apiBase}/schedule/get_schedule_by_criteria_db/${encodeURIComponent(roomCode.value)}?schedule_date=${anchorDate.value}&source_type=all`
    //console.log("GET week schedule",url);
    const res = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data: ScheduleItem[] = await res.json()
    const items = Array.isArray(data) ? data : []

    weekItems.value = items
    state.value = 'done'
    checkConfirmStatus(items)
  } catch (e) {
    state.value  = 'error'
    errMsg.value = `ไม่สามารถโหลดข้อมูลได้: ${e}`
  }
}

// Shifts anchorDate by whole weeks — the calendar data re-filters reactively, so
// this needs no refetch; it only refetches the DB-backed room grid.
function shiftWeek(deltaDays: number) {
  const d = new Date(anchorDate.value)
  d.setDate(d.getDate() + deltaDays)
  anchorDate.value = d.toISOString().slice(0, 10)
  if (viewMode.value === 'room') loadWeek()
}

function selectToday() {
  anchorDate.value = new Date().toISOString().slice(0, 10)
  if (viewMode.value === 'room') loadWeek()
}

function refreshSelectedWeek() {
  if (viewMode.value === 'room') loadWeek()
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
      } else if (typeof parsed?.topic === 'string' && parsed.topic.startsWith('submit_close/')) {
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
    <section class="schedule-toolbar" aria-labelledby="schedule-page-title">
      <div class="schedule-toolbar-top">
        <div class="schedule-heading">
          <h1 id="schedule-page-title">ตารางการจองห้อง</h1>
          <p>{{ viewMode === 'room'
            ? 'เลือกห้องเพื่อดูช่วงเวลาว่างและจองได้ทันที'
            : viewMode === 'full'
              ? 'เปรียบเทียบตารางและช่วงเวลาว่างของทุกห้องในวันที่เลือก'
              : 'ดูตารางทุกห้องครบทั้ง 7 วันภายในสัปดาห์เดียวกัน' }}</p>
        </div>

        <div class="view-toggle" aria-label="รูปแบบการแสดงตาราง">
          <button type="button" class="btn-mode" :class="{ active: viewMode === 'room' }" @click="setViewMode('room')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 5h6v6H4zM14 5h6v6h-6zM4 15h6v4H4zM14 15h6v4h-6z" />
            </svg>
            ดูตามห้อง
          </button>
          <button type="button" class="btn-mode" :class="{ active: viewMode === 'full' }" @click="setViewMode('full')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 3v3M18 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" />
            </svg>
            ตารางรวม
          </button>
          <button type="button" class="btn-mode" :class="{ active: viewMode === 'week' }" @click="setViewMode('week')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 6h16M4 11h16M4 16h16M8 3v18M16 3v18" />
            </svg>
            ทั้งสัปดาห์
          </button>
        </div>
      </div>

      <div class="schedule-filters">
        <label v-if="viewMode === 'room'" class="filter-field room-filter">
          <span>ห้อง</span>
          <select v-model="roomCode" class="filter-control" @change="loadWeek">
            <option value="" disabled>เลือกห้อง</option>
            <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
          </select>
        </label>

        <label v-if="viewMode !== 'room'" class="filter-field floor-filter">
          <span>ชั้น</span>
          <select v-model="fullFloor" class="filter-control" @change="fullRoomQuery = ''">
            <option value="all">ทุกชั้น</option>
            <option v-for="floor in fullFloors" :key="floor" :value="floor">
              {{ floor === 'ไม่ระบุชั้น' || floor === 'Unspecified' ? floor : `${locale === 'en' ? 'Floor' : 'ชั้น'} ${floor}` }}
            </option>
          </select>
        </label>

        <label v-if="viewMode !== 'room'" class="filter-field search-room-filter">
          <span>ห้อง</span>
          <select v-model="fullRoomQuery" class="filter-control">
            <option value="">ทุกห้อง</option>
            <option v-for="room in selectableFullRooms" :key="room" :value="room">{{ room }}</option>
          </select>
        </label>

        <div class="week-picker-group">
          <span class="filter-label">{{ viewMode === 'full' ? 'วันที่' : 'สัปดาห์' }}</span>
          <div class="week-picker">
            <button type="button" class="btn-week-nav" :aria-label="viewMode === 'full' ? 'วันก่อนหน้า' : 'สัปดาห์ก่อนหน้า'" :title="viewMode === 'full' ? 'วันก่อนหน้า' : 'สัปดาห์ก่อนหน้า'" @click="shiftWeek(viewMode === 'full' ? -1 : -7)">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
            </button>
            <label class="date-control">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3v3M18 3v3M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z" /></svg>
              <input v-model="anchorDate" type="date" aria-label="เลือกวันที่" @change="refreshSelectedWeek" />
            </label>
            <button type="button" class="btn-week-nav" :aria-label="viewMode === 'full' ? 'วันถัดไป' : 'สัปดาห์ถัดไป'" :title="viewMode === 'full' ? 'วันถัดไป' : 'สัปดาห์ถัดไป'" @click="shiftWeek(viewMode === 'full' ? 1 : 7)">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            </button>
          </div>
        </div>

        <button type="button" class="btn-today" @click="selectToday">วันนี้</button>
        <div class="week-summary" aria-live="polite">
          <span>{{ viewMode === 'room' ? (roomCode || 'เลือกห้อง') : 'ทุกห้อง' }}</span>
          <strong>{{ viewMode === 'full' ? selectedDateLabel : weekRangeLabel }}</strong>
        </div>
      </div>
    </section>

    <div v-if="viewMode === 'room' && state === 'error'" class="msg error-box">{{ errMsg }}</div>

    <div v-if="viewMode === 'room' && state === 'loading'" class="msg muted">กำลังโหลดตาราง…</div>

    <div v-if="viewMode === 'room' && state === 'done'" class="table-card">
      <div class="table-scroll">
        <table class="grid">
          <thead>
            <tr>
              <th class="day-head">{{ locale === 'en' ? 'Day' : 'วัน' }}</th>
              <th v-for="p in visiblePeriods" :key="p.period" class="period-head">
                <div class="period-no">{{ locale === 'en' ? `Period ${p.period}` : `คาบ ${p.period}` }}</div>
                <div class="period-time">{{ p.labelSTime ?? p.startTime }}–{{ p.labelFTime ?? p.finishTime }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.weekdayNum">
              <td class="day-cell" :class="{ today: isToday(row.date) }">
                <div class="day-label">{{ row.label }}</div>
                <div class="day-date">{{ row.date }}</div>
              </td>
              <template v-for="(cell, idx) in row.cells" :key="idx">
                <td
                  v-if="cell.type !== 'skip'"
                  :colspan="cell.span || 1"
                  class="period-cell"
                  :class="{ filled: cell.type === 'item', active: cell.type === 'item' && isActiveItem(cell.item, row.date) }"
                >
                  <template v-if="cell.type === 'item' && cell.item">
                    <div class="course-code" translate="no">{{ cell.item.coursecode }}</div>
                    <div class="course-name" translate="no">{{ cell.item.coursename }}</div>
                    <!-- <div class="course-time">{{ cell.item.startTime }} – {{ cell.item.finishTime }}</div> -->
                    <div v-if="cell.item.teacher_name" class="course-teacher" translate="no">
                        {{ cell.item.teacher_name}}
                    </div>
                    <div
                      v-if="usageStatusLabel(cell.item)"
                      class="usage-status-badge"
                      :class="{ closed: Number(cell.item.usage_status) === 4 }"
                    >
                      สถานะ {{ usageStatusLabel(cell.item) }}
                    </div>
                    <template v-if="canConfirm(cell.item)">
                      <div
                        v-if="confirmCache[cell.item.uuid!]?.is_confirm_progress"
                        class="confirmed-badge-cell"
                      >
                        ยืนยันการเข้าใช้แล้ว
                      </div>
                      <button
                        v-else
                        class="btn-confirm-cell"
                        :disabled="confirmingId === cell.item.uuid"
                        @click="confirmClass(cell.item)"
                      >
                        {{ confirmingId === cell.item.uuid ? 'กำลังยืนยัน…' : 'ยืนยันเข้าใช้' }}
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
                      v-if="canCancel(cell.item, row.date)"
                      class="btn-cancel-cell"
                      :disabled="cancellingId === cell.item.uuid"
                      @click="confirmCancel(cell.item)"
                    >
                      {{ cancellingId === cell.item.uuid ? 'กำลังยกเลิก…' : 'ยกเลิกการใช้ห้อง' }}
                    </button>
                    <div
                      v-if="deleteMsg && deleteMsg.schedule_id === cell.item.schedule_id"
                      class="cancel-msg-cell"
                      :class="deleteMsg.ok ? 'ok' : 'fail'"
                    >
                      {{ deleteMsg.text }}
                    </div>
                    <button
                      v-if="canDelete(cell.item, row.date)"
                      class="btn-delete-cell"
                      :disabled="deletingId === cell.item.schedule_id"
                      @click="deleteSchedule(cell.item)"
                    >
                      {{ deletingId === cell.item.schedule_id ? 'กำลังลบ…' : 'ลบตาราง' }}
                    </button>
                  
                  </template>
                  <template v-else>
                    <button
                      class="btn-book-empty"
                      :disabled="!canBookPeriod(row.date, visiblePeriods[idx])"
                      :aria-label="isPastPeriod(row.date, visiblePeriods[idx])
                        ? (locale === 'en' ? `Expired, period ${visiblePeriods[idx].period}` : `หมดเวลา คาบ ${visiblePeriods[idx].period}`)
                        : (locale === 'en' ? `Book available room, period ${visiblePeriods[idx].period}` : `จองห้องว่าง คาบ ${visiblePeriods[idx].period}`)"
                      @click="openBookingForPeriod(visiblePeriods[idx], row.date)"
                    >
                      {{ isPastPeriod(row.date, visiblePeriods[idx]) ? (locale === 'en' ? 'Expired' : 'หมดเวลา') : (locale === 'en' ? 'Available' : 'ว่าง') }}
                    </button>
                  </template>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="viewMode !== 'room' && fullState === 'error'" class="msg error-box">{{ fullErrMsg }}</div>

    <div v-if="viewMode !== 'room' && fullState === 'loading'" class="msg muted">กำลังโหลดปฏิทินรวม…</div>

    <section v-if="viewMode === 'full' && fullState !== 'loading'" class="full-daily-card" aria-labelledby="full-daily-title">
      <div class="full-daily-summary">
        <div>
          <h2 id="full-daily-title">ตารางทุกห้องประจำวัน</h2>
          <p>{{ selectedDateLabel }} · {{ fullDayItems.length }} รายการ</p>
        </div>
        <div class="schedule-legend" aria-label="คำอธิบายสถานะ">
          <span><i class="legend-dot occupied"></i>มีตาราง</span>
          <span><i class="legend-dot available"></i>ว่าง</span>
          <span><i class="legend-dot expired"></i>หมดเวลา</span>
        </div>
      </div>

      <div v-if="fullRoomGroups.length === 0" class="full-empty-state">
        ไม่พบห้องที่ตรงกับตัวกรอง
      </div>

      <div v-else class="full-grid-scroll">
        <table class="full-grid-table">
          <thead>
            <tr>
              <th class="full-room-head">ห้อง</th>
              <th v-for="period in visiblePeriods" :key="period.period" class="full-period-head">
                <strong>{{ locale === 'en' ? `Period ${period.period}` : `คาบ ${period.period}` }}</strong>
                <span>{{ period.labelSTime ?? period.startTime }}–{{ period.labelFTime ?? period.finishTime }}</span>
              </th>
            </tr>
          </thead>
          <tbody v-for="group in fullRoomGroups" :key="group.floor">
            <tr class="floor-row">
              <th :colspan="visiblePeriods.length + 1">
                {{ group.floor === 'ไม่ระบุชั้น' || group.floor === 'Unspecified' ? group.floor : `${locale === 'en' ? 'Floor' : 'ชั้น'} ${group.floor}` }}
                <span>{{ group.roomRows.length }} ห้อง</span>
              </th>
            </tr>
            <tr v-for="row in group.roomRows" :key="row.room" class="full-room-row">
              <th class="full-room-cell" scope="row">{{ row.room }}</th>
              <template v-for="(cell, index) in row.cells" :key="index">
                <td v-if="cell.type !== 'skip'" :colspan="cell.span || 1" class="full-grid-cell" :class="{ occupied: cell.type === 'item' }">
                  <template v-if="cell.type === 'item' && cell.items?.length">
                    <div class="full-schedule-block">
                      <div class="full-schedule-top">
                        <strong translate="no">{{ cell.items[0].coursecode }}</strong>
                        <span>{{ cell.items[0].startTime }}–{{ cell.items[0].finishTime }}</span>
                      </div>
                      <div class="full-schedule-name" translate="no">{{ cell.items[0].coursename }}</div>
                      <div v-if="fullCalendarTeacherLabel(cell.items[0])" class="full-schedule-teacher" translate="no">
                        {{ fullCalendarTeacherLabel(cell.items[0]) }}
                      </div>
                      <span v-if="cell.items.length > 1" class="full-overlap-count">+{{ cell.items.length - 1 }}</span>
                    </div>
                  </template>
                  <button
                    v-else
                    type="button"
                    class="full-empty-slot"
                    :class="{ expired: isPastPeriod(anchorDate, visiblePeriods[index]) }"
                    :disabled="!canBookPeriod(anchorDate, visiblePeriods[index])"
                    @click="openFullBooking(visiblePeriods[index], row.room)"
                  >
                    {{ isPastPeriod(anchorDate, visiblePeriods[index]) ? (locale === 'en' ? 'Expired' : 'หมดเวลา') : (locale === 'en' ? 'Available' : 'ว่าง') }}
                  </button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="viewMode === 'week' && fullState !== 'loading'" class="weekly-overview" aria-labelledby="weekly-overview-title">
      <div class="weekly-overview-heading">
        <div>
          <h2 id="weekly-overview-title">ตารางทุกห้องประจำสัปดาห์</h2>
          <p>{{ weekRangeLabel }}</p>
        </div>
        <span>{{ weeklyItems.length }} รายการ</span>
      </div>

      <div v-if="weeklyRoomGroups.length === 0" class="full-empty-state">
        ไม่พบห้องที่ตรงกับตัวกรอง
      </div>

      <div v-else class="weekly-grid-scroll">
        <table class="weekly-grid-table">
          <thead>
            <tr>
              <th class="weekly-room-head">ห้อง</th>
              <th
                v-for="(date, index) in weekDates"
                :key="date"
                class="weekly-day-head"
                :class="{ today: isToday(date) }"
              >
                <strong>{{ weekdayLabel(index) }}</strong>
                <span>{{ weeklyDateLabel(date) }}</span>
              </th>
            </tr>
          </thead>
          <tbody v-for="group in weeklyRoomGroups" :key="group.floor">
            <tr class="weekly-floor-row">
              <th :colspan="weekDates.length + 1">
                {{ group.floor === 'ไม่ระบุชั้น' || group.floor === 'Unspecified' ? group.floor : `${locale === 'en' ? 'Floor' : 'ชั้น'} ${group.floor}` }}
                <span>{{ group.roomRows.length }} ห้อง</span>
              </th>
            </tr>
            <tr v-for="row in group.roomRows" :key="row.room" class="weekly-room-row">
              <th class="weekly-room-cell" scope="row" translate="no">{{ row.room }}</th>
              <td
                v-for="day in row.days"
                :key="day.date"
                class="weekly-day-cell"
                :class="{ today: isToday(day.date) }"
              >
                <span v-if="day.items.length === 0" class="weekly-all-day-empty">ว่างทั้งวัน</span>
                <template v-else>
                  <button
                    v-for="item in day.items"
                    :key="item.rowId"
                    type="button"
                    class="weekly-entry"
                    :class="{
                      past: isFullItemPast(item),
                      expanded: expandedWeeklyItemId === item.rowId,
                    }"
                    :aria-expanded="expandedWeeklyItemId === item.rowId"
                    @click="toggleWeeklyItem(item.rowId)"
                  >
                    <span class="weekly-entry-time">{{ item.startTime }}–{{ item.finishTime }}</span>
                    <strong class="weekly-entry-code" translate="no">{{ item.coursecode }}</strong>
                    <span class="weekly-entry-name" translate="no">{{ item.coursename }}</span>
                    <span
                      v-if="expandedWeeklyItemId === item.rowId && fullCalendarTeacherLabel(item)"
                      class="weekly-entry-teacher"
                      translate="no"
                    >{{ fullCalendarTeacherLabel(item) }}</span>
                  </button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Confirm class popup -->
    <Teleport to="body">
      <div v-if="showConfirmModal" class="confirm-overlay" @click.self="closeConfirmModal">
        <div class="confirm-modal">
          <button class="confirm-close" aria-label="ปิดหน้าต่างยืนยัน" @click="closeConfirmModal">
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
          <p class="modal-title">{{ modalWording.title }}</p>
          <p class="modal-body">
            <strong>{{ confirmModal.item?.coursecode }}</strong> — {{ confirmModal.item?.coursename }}<br/>
            <span class="modal-time">{{ confirmModal.item?.startTime }} – {{ confirmModal.item?.finishTime }}</span>
          </p>
          <div class="modal-actions">
            <button class="modal-btn cancel" @click="modalAnswer(false)">{{ modalWording.dismiss }}</button>
            <button class="modal-btn confirm" @click="modalAnswer(true)">{{ modalWording.confirm }}</button>
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
  padding: 4.25rem 1% 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow: hidden;
  box-sizing: border-box;
  z-index: 10;
}

.schedule-toolbar {
  width: 98%;
  margin: 0 auto;
  padding: 0.8rem 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  box-sizing: border-box;
}

.schedule-toolbar-top,
.schedule-filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.schedule-toolbar-top {
  padding-bottom: 0.7rem;
  border-bottom: 1px solid var(--border);
}

.schedule-heading h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: calc(1.18rem - 1px);
  font-weight: 750;
  letter-spacing: -0.01em;
}

.schedule-heading p {
  margin: 0.2rem 0 0;
  color: var(--text-secondary);
  font-size: calc(0.88rem - 1px);
}

.schedule-filters {
  justify-content: flex-start;
  padding-top: 0.7rem;
}

.filter-field,
.week-picker-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-field > span,
.filter-label {
  color: var(--text-secondary);
  font-size: calc(0.82rem - 1px);
  font-weight: 650;
  white-space: nowrap;
}

.filter-control,
.date-control {
  min-height: 34px;
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font: inherit;
  font-size: calc(0.9rem - 1px);
}

.filter-control {
  min-width: 9rem;
  padding: 0.35rem 2rem 0.35rem 0.65rem;
  cursor: pointer;
}

.week-picker {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.date-control {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0 0.55rem;
}

.date-control svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: var(--accent-link);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.date-control input {
  min-width: 8.2rem;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary);
  color-scheme: inherit;
  font: inherit;
  font-size: calc(0.88rem - 1px);
  cursor: pointer;
}

.btn-today {
  min-height: 34px;
  padding: 0.35rem 0.8rem;
  border: 1px solid color-mix(in srgb, var(--accent-link) 35%, var(--border));
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--accent-link) 10%, var(--bg-surface));
  color: var(--accent-link);
  font: inherit;
  font-size: calc(0.86rem - 1px);
  font-weight: 700;
  cursor: pointer;
}

.btn-today:hover {
  background: color-mix(in srgb, var(--accent-link) 16%, var(--bg-surface));
}

.week-summary {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 34px;
  margin-left: auto;
  color: var(--text-secondary);
  font-size: calc(0.82rem - 1px);
  white-space: nowrap;
}

.week-summary span {
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-link) 10%, var(--bg-surface));
  color: var(--accent-link);
  font-weight: 750;
}

.week-summary strong {
  color: var(--text-primary);
  font-size: calc(0.86rem - 1px);
  font-weight: 650;
}

.schedule-toolbar :is(button, select, input):focus-visible {
  outline: 2px solid var(--accent-link);
  outline-offset: 2px;
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
  color: var(--text-muted);
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
  color: var(--text-muted);
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
  color-scheme: inherit;
}
.input:focus { border-color: var(--accent-link); }

.btn-search {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
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
  min-height: 34px;
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.btn-open-search svg { width: 16px; height: 16px; flex-shrink: 0; color: var(--accent-link); }
.btn-open-search:hover { border-color: var(--accent-link); }

.view-toggle {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  padding: 0.2rem;
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.65rem;
}
.btn-mode {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 0.45rem;
  color: var(--text-secondary);
  min-height: 34px;
  padding: 0.35rem 0.8rem;
  font-size: calc(0.88rem - 1px);
  font-weight: 600;
  cursor: pointer;
}
.btn-mode svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.btn-mode:first-child svg { fill: currentColor; stroke: none; }
.btn-mode:hover { color: var(--text-primary); background: var(--bg-surface); }
.btn-mode.active {
  background: var(--brand-primary);
  border-color: var(--brand-primary);
  color: var(--brand-on-primary);
}

.msg   { padding: 0.65rem 1rem; border-radius: 0.5rem; font-size: 0.875rem; width: 98%; margin: 0 auto; box-sizing: border-box; }
.muted { color: var(--text-muted); }
.error-box { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid var(--status-busy); }

.fullscreen-prompt {
  background: var(--pill-amber-bg);
  color: var(--pill-amber-text);
  border: 1px solid var(--status-pending);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-fullscreen {
  background: var(--status-pending);
  color: #1e293b;
  border: none;
  border-radius: 0.4rem;
  padding: 0.4rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}
.btn-fullscreen:hover { filter: brightness(1.08); }

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
  min-height: 0;
}

/* ── Full calendar — all rooms, week agenda ── */
.week-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  width: 98%;
  margin: 0 auto;
}

.btn-week-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-primary);
  cursor: pointer;
}
.btn-week-nav svg { width: 16px; height: 16px; }
.btn-week-nav:hover { border-color: var(--accent-link); color: var(--accent-link); }

.week-nav-label {
  font-family: monospace;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.full-calendar {
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(7, minmax(150px, 1fr));
  gap: 0.6rem;
  align-items: start;
  overflow: auto;
  padding-bottom: 0.25rem;
}

.weekly-overview {
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  overflow: hidden;
}

.weekly-overview-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.62rem 0.82rem;
  border-bottom: 1px solid var(--border);
}

.weekly-overview-heading h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.98rem;
}

.weekly-overview-heading p {
  margin: 0.12rem 0 0;
  color: var(--text-secondary);
  font-size: 0.74rem;
}

.weekly-overview-heading > span {
  padding: 0.22rem 0.58rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent-link) 10%, var(--bg-surface));
  color: var(--accent-link);
  font-size: 0.72rem;
  font-weight: 750;
  white-space: nowrap;
}

.weekly-grid-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

.weekly-grid-table {
  width: 100%;
  min-width: 1350px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  color: var(--text-primary);
}

.weekly-grid-table th,
.weekly-grid-table td {
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.weekly-grid-table thead th {
  position: sticky;
  top: 0;
  z-index: 5;
  height: 58px;
  padding: 0.45rem 0.55rem;
  background: var(--bg-page);
  text-align: center;
}

.weekly-room-head,
.weekly-room-cell {
  position: sticky;
  left: 0;
  width: 118px;
  min-width: 118px;
  max-width: 118px;
}

.weekly-grid-table thead .weekly-room-head {
  z-index: 7;
  background: var(--bg-page);
}

.weekly-day-head {
  width: 176px;
}

.weekly-day-head strong,
.weekly-day-head span {
  display: block;
}

.weekly-day-head strong {
  font-size: 0.84rem;
}

.weekly-day-head span {
  margin-top: 0.08rem;
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 550;
}

.weekly-day-head.today {
  color: var(--accent-link);
  background: color-mix(in srgb, var(--accent-link) 13%, var(--bg-page));
  box-shadow: inset 0 -3px 0 var(--accent-link);
}

.weekly-floor-row th {
  position: sticky;
  top: 58px;
  z-index: 4;
  padding: 0.36rem 0.75rem;
  background: color-mix(in srgb, var(--accent-link) 8%, var(--bg-page));
  color: var(--text-primary);
  font-size: 0.76rem;
  text-align: left;
}

.weekly-floor-row span {
  margin-left: 0.45rem;
  color: var(--text-secondary);
  font-size: 0.68rem;
  font-weight: 550;
}

.weekly-room-cell {
  z-index: 3;
  padding: 0.7rem 0.6rem;
  background: var(--weekly-row-bg);
  color: var(--accent-link);
  font-family: monospace;
  font-size: 0.82rem;
  text-align: center;
  vertical-align: top;
}

.weekly-room-row {
  --weekly-row-bg: var(--bg-surface);
}

.weekly-room-row:nth-child(odd) {
  --weekly-row-bg: color-mix(in srgb, var(--accent-link) 3%, var(--bg-surface));
}

.weekly-room-row:hover {
  --weekly-row-bg: color-mix(in srgb, var(--accent-link) 6%, var(--bg-surface));
}

.weekly-day-cell {
  min-height: 74px;
  padding: 0.42rem;
  background: var(--weekly-row-bg);
  vertical-align: top;
}

.weekly-day-cell.today {
  background: color-mix(in srgb, var(--accent-link) 7%, var(--weekly-row-bg));
}

.weekly-all-day-empty {
  display: block;
  padding: 0.65rem 0.3rem;
  color: var(--text-secondary);
  font-size: 0.72rem;
  text-align: center;
}

.weekly-entry {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.08rem 0.35rem;
  margin: 0 0 0.34rem;
  padding: 0.42rem 0.48rem;
  border: 1px solid color-mix(in srgb, var(--accent-link) 25%, var(--border));
  border-left: 3px solid var(--accent-link);
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--accent-link) 8%, var(--bg-surface));
  color: var(--text-primary);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease, box-shadow 150ms ease;
}

.weekly-entry:last-child {
  margin-bottom: 0;
}

.weekly-entry:hover,
.weekly-entry:focus-visible,
.weekly-entry.expanded {
  border-color: color-mix(in srgb, var(--accent-link) 55%, var(--border));
  background: color-mix(in srgb, var(--accent-link) 13%, var(--bg-surface));
  box-shadow: 0 2px 7px rgba(15, 23, 42, 0.08);
  outline: none;
}

.weekly-entry.past {
  opacity: 0.45;
  filter: saturate(0.45);
}

.weekly-entry-time {
  grid-column: 1;
  color: var(--text-secondary);
  font-family: monospace;
  font-size: 0.68rem;
  font-weight: 650;
}

.weekly-entry-code {
  grid-column: 2;
  grid-row: 1;
  color: var(--accent-link);
  font-family: monospace;
  font-size: 0.68rem;
  white-space: nowrap;
}

.weekly-entry-name {
  grid-column: 1 / -1;
  display: -webkit-box;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 0.72rem;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.weekly-entry.expanded .weekly-entry-name {
  display: block;
  overflow: visible;
}

.weekly-entry-teacher {
  grid-column: 1 / -1;
  margin-top: 0.18rem;
  padding-top: 0.28rem;
  border-top: 1px dashed color-mix(in srgb, var(--accent-link) 25%, var(--border));
  color: var(--text-secondary);
  font-size: 0.68rem;
  line-height: 1.35;
}

.full-daily-card {
  width: 98%;
  margin: 0 auto;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  box-sizing: border-box;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.full-daily-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid var(--border);
}

.full-daily-summary h2 {
  margin: 0;
  font-size: 0.98rem;
  color: var(--text-primary);
}

.full-daily-summary p {
  margin: 0.12rem 0 0;
  color: var(--text-secondary);
  font-size: 0.76rem;
}

.schedule-legend {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  color: var(--text-secondary);
  font-size: 0.74rem;
  white-space: nowrap;
}

.schedule-legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
}

.legend-dot {
  width: 0.58rem;
  height: 0.58rem;
  border-radius: 0.18rem;
  border: 1px solid var(--border);
}

.legend-dot.occupied { background: var(--dashboard-accent-soft); border-color: var(--accent-link); }
.legend-dot.available { background: var(--bg-surface); border-color: var(--border); }
.legend-dot.expired { background: var(--bg-surface-alt); border-color: var(--border); }

.full-grid-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-color: var(--text-muted) transparent;
  scrollbar-width: thin;
}

.full-grid-table {
  width: max(100%, 1420px);
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

.full-grid-table thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  height: 48px;
  padding: 0.35rem 0.45rem;
  background: var(--bg-page);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
  text-align: center;
  box-sizing: border-box;
}

.full-room-head,
.full-room-cell {
  position: sticky;
  left: 0;
  width: 112px;
  min-width: 112px;
  max-width: 112px;
}

.full-room-head { z-index: 6 !important; }

.full-period-head strong {
  display: block;
  color: var(--accent-link);
  font-size: 0.73rem;
}

.full-period-head span {
  display: block;
  margin-top: 0.12rem;
  color: var(--text-secondary);
  font-size: 0.66rem;
  font-variant-numeric: tabular-nums;
}

.floor-row th {
  position: sticky;
  top: 48px;
  z-index: 3;
  padding: 0.38rem 0.75rem;
  background: color-mix(in srgb, var(--accent-link) 9%, var(--bg-surface));
  border-bottom: 1px solid color-mix(in srgb, var(--accent-link) 22%, var(--border));
  color: var(--text-primary);
  font-size: 0.76rem;
  text-align: left;
}

.floor-row th span {
  margin-left: 0.45rem;
  color: var(--text-secondary);
  font-size: 0.68rem;
  font-weight: 500;
}

.full-room-row { height: 76px; }

.full-room-cell {
  z-index: 2;
  padding: 0.45rem;
  background: var(--bg-page);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  color: var(--text-primary);
  font-size: 0.76rem;
  font-weight: 750;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.full-grid-cell {
  height: 76px;
  padding: 0.24rem;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  box-sizing: border-box;
}

.full-grid-cell.occupied {
  background: color-mix(in srgb, var(--accent-link) 8%, var(--bg-surface));
}

.full-schedule-block {
  position: relative;
  height: 100%;
  padding: 0.4rem 0.5rem;
  border-radius: 0.45rem;
  background: color-mix(in srgb, var(--accent-link) 11%, var(--bg-surface));
  border: 1px solid color-mix(in srgb, var(--accent-link) 42%, var(--border));
  box-sizing: border-box;
  overflow: hidden;
}

.full-schedule-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.full-schedule-top strong {
  color: var(--accent-link);
  font-size: 0.72rem;
}

.full-schedule-top span {
  color: var(--text-secondary);
  font-size: 0.64rem;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.full-schedule-name {
  margin-top: 0.12rem;
  color: var(--text-primary);
  font-size: 0.71rem;
  font-weight: 650;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.full-schedule-teacher {
  margin-top: 0.12rem;
  color: var(--text-secondary);
  font-size: 0.64rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.full-overlap-count {
  position: absolute;
  right: 0.35rem;
  bottom: 0.28rem;
  padding: 0.05rem 0.32rem;
  border-radius: 999px;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
  font-size: 0.6rem;
  font-weight: 750;
}

.full-empty-slot {
  width: 100%;
  height: 100%;
  border: 1px dashed color-mix(in srgb, var(--accent-link) 28%, var(--border));
  border-radius: 0.42rem;
  background: transparent;
  color: var(--accent-link);
  font: inherit;
  font-size: 0.68rem;
  font-weight: 650;
  cursor: pointer;
}

.full-empty-slot:hover:not(:disabled) {
  border-color: var(--accent-link);
  background: color-mix(in srgb, var(--accent-link) 8%, var(--bg-surface));
}

.full-empty-slot.expired,
.full-empty-slot:disabled {
  border-color: var(--border);
  color: var(--text-secondary);
  background: color-mix(in srgb, var(--text-secondary) 5%, var(--bg-surface));
  opacity: 0.55;
  cursor: not-allowed;
}

.full-empty-state {
  display: grid;
  place-items: center;
  flex: 1;
  min-height: 12rem;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.search-room-filter .filter-control {
  min-width: 8rem;
  max-width: 10rem;
  padding-right: 0.65rem;
}

.grid {
  border-collapse: collapse;
  width: 100%;
  height: 100%;
  table-layout: fixed;
}

.grid thead {
  height: 48px;
}

.grid tbody tr {
  height: calc((100% - 48px) / 7);
}

.day-head,
.period-head {
  background: var(--bg-page);
  border: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  text-align: center;
  font-size: calc(0.8rem - 1px);
  color: var(--text-secondary);
  white-space: nowrap;
}

.day-head { width: 90px; }

.period-no  { font-weight: 700; color: var(--accent-link); }
.period-time { font-family: monospace; font-size: calc(0.75rem - 1px); margin-top: 0.15rem; }

.day-cell {
  border: 1px solid var(--border);
  padding: 0.5rem 0.6rem;
  text-align: center;
  background: var(--bg-page);
  vertical-align: middle;
}

.day-cell.today {
  background: color-mix(in srgb, var(--accent-link) 10%, var(--bg-page));
  box-shadow: inset 3px 0 0 var(--accent-link);
}

.day-cell.today .day-label {
  color: var(--accent-link);
}

.day-label { font-weight: 700; font-size: calc(0.9rem - 1px); }
.day-date  { font-family: monospace; font-size: calc(0.75rem - 1px); color: var(--text-muted); margin-top: 0.15rem; }

.period-cell {
  border: 1px solid var(--border);
  padding: 0.4rem 0.5rem;
  vertical-align: top;
  min-width: 90px;
  height: auto;
}

.period-cell.filled {
  background: var(--dashboard-accent-soft);
}

.period-cell.active {
  background: var(--status-free-soft);
  border-color: var(--status-free);
  box-shadow: inset 0 0 0 1px var(--status-free);
}

.course-code {
  font-size: calc(0.8rem - 1px);
  font-weight: 700;
  color: var(--accent-link);
  font-family: monospace;
}

.course-name {
  font-size: calc(0.82rem - 1px);
  color: var(--text-primary);
  line-height: 1.3;
  margin-top: 0.1rem;
}

.course-time {
  font-size: calc(0.72rem - 1px);
  font-family: monospace;
  color: var(--text-secondary);
  margin-top: 0.2rem;
}

.course-teacher {
  font-size: calc(0.72rem - 1px);
  color: var(--text-secondary);
  margin-top: 0.1rem;
}

.btn-confirm-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
  border: none;
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: calc(0.72rem - 1px);
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
  border: 1px solid var(--status-free);
  color: var(--pill-success-text);
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: calc(0.7rem - 1px);
  font-weight: 700;
  text-align: center;
}

.usage-status-badge {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: var(--pill-success-bg);
  border: 1px solid var(--status-free);
  color: var(--pill-success-text);
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: calc(0.75rem - 1px);
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 2px;
  text-align: center;
}
.usage-status-badge.closed {
  background: var(--pill-error-bg);
  border-color: var(--status-busy);
  color: var(--pill-error-text);
}

.btn-cancel-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: transparent;
  border: 1px solid var(--status-busy);
  color: var(--pill-error-text);
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: calc(0.72rem - 1px);
  font-weight: 700;
  cursor: pointer;
}
.btn-cancel-cell:hover:not(:disabled) { background: var(--status-busy-soft); }
.btn-cancel-cell:disabled { opacity: 0.4; cursor: not-allowed; }

/* Solid fill, unlike the outlined Cancel button — deletion is irreversible. */
.btn-delete-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: #b91c1c;
  border: 1px solid #b91c1c;
  color: #ffffff;
  border-radius: 0.35rem;
  padding: 0.25rem 0.4rem;
  font-size: calc(0.72rem - 1px);
  font-weight: 700;
  cursor: pointer;
}
.btn-delete-cell:hover:not(:disabled) { background: #991b1b; }
.btn-delete-cell:disabled { opacity: 0.4; cursor: not-allowed; }

.link-booking-cell {
  display: block;
  width: 100%;
  margin-top: 0.3rem;
  background: transparent;
  border: none;
  color: var(--accent-link);
  font-size: calc(0.7rem - 1px);
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
  min-height: 32px;
  background: transparent;
  border: 1px dashed var(--border);
  border-radius: 0.35rem;
  color: var(--text-secondary);
  font-size: calc(0.77rem - 1px);
  font-weight: 600;
  cursor: pointer;
}
.btn-book-empty:hover:not(:disabled) {
  border-color: var(--accent-link);
  color: var(--accent-link);
  background: var(--dashboard-accent-soft);
}
.btn-book-empty:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.cancel-msg-cell {
  margin-top: 0.3rem;
  padding: 0.2rem 0.35rem;
  border-radius: 0.35rem;
  font-size: calc(0.68rem - 1px);
  font-weight: 600;
}
.cancel-msg-cell.ok   { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid var(--status-free); }
.cancel-msg-cell.fail { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid var(--status-busy); }

@media (max-height: 820px) {
  .page {
    padding-top: 4rem;
    padding-bottom: 0.5rem;
    gap: 0.35rem;
  }

  .schedule-toolbar {
    padding: 0.55rem 0.75rem;
  }

  .schedule-toolbar-top {
    padding-bottom: 0.45rem;
  }

  .schedule-filters {
    padding-top: 0.45rem;
  }

  .schedule-heading p {
    display: none;
  }

  .grid thead {
    height: 42px;
  }

  .grid tbody tr {
    height: calc((100% - 42px) / 7);
  }

  .day-head,
  .period-head,
  .day-cell,
  .period-cell {
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
  }

  .course-name,
  .course-teacher {
    line-height: 1.15;
  }
}

@media (max-width: 1100px) {
  .schedule-toolbar-top,
  .schedule-filters {
    gap: 0.65rem;
  }

  .schedule-filters {
    flex-wrap: wrap;
  }

  .week-summary {
    margin-left: 0;
  }
}

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

.anchor-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  align-self: flex-start;
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
