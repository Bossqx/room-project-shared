<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import config from '../assets/config.json'
import { locale } from '../i18n'
import { useSemesterStore } from '../stores/semester'

type RangeKey = 'week' | 'month' | 'semester'
interface Teacher { prefixname?: string; officername?: string; officersurname?: string }
interface ScheduleItem {
  rowId?: number; id?: string | number; roomcode: string; schedule_date: string; startTime: string; finishTime: string
  coursecode?: string; coursename?: string; subject_code?: string; subject_name?: string; objective?: string
  teacher_name?: string | Teacher[]; user_name?: string; user_login?: string; usage_status?: number | string
}
interface RoomStat { room: string; sessions: number; hours: number; share: number }
interface UserStat { name: string; sessions: number; hours: number; share: number }
interface TrendPoint { key: string; label: string; fullLabel: string; sessions: number; hours: number }

const API = (config.apiRoute ?? '/api/').replace(/\/$/, '')
const semesterStore = useSemesterStore()
const schedules = ref<ScheduleItem[]>([])
const loading = ref(true)
const error = ref('')
const now = new Date()
const selectedRange = ref<RangeKey>('week')
const selectedYear = ref(now.getFullYear())
const selectedMonth = ref(now.getMonth())
const selectedUser = ref('')
const rankingView = ref<'users' | 'rooms'>('users')
const rankingDialog = ref<HTMLDialogElement | null>(null)
const updatedAt = ref<Date | null>(null)
const usageStatusCache = ref(new Map<string, number>())
const statusLoading = ref(false)
let statusLoadGeneration = 0

const copy = computed(() => locale.value === 'th' ? {
  title: 'สถิติการใช้ห้อง', subtitle: 'วิเคราะห์ปริมาณการใช้งานและช่วงเวลาที่มีความต้องการสูง',
  week: 'สัปดาห์นี้', month: 'รายเดือน', semester: 'ทั้งภาคเรียน', selectMonth: 'เลือกเดือน', selectYear: 'เลือกปี', selectUser: 'เลือกผู้ใช้งาน', everyUser: 'ผู้ใช้งานทั้งหมด', refresh: 'รีเฟรช', updating: 'กำลังโหลด…', updated: 'อัปเดตล่าสุด',
  sessions: 'รายการจอง', hours: 'ชั่วโมงที่ถูกจอง', rooms: 'ห้องที่มีการใช้', utilization: 'อัตราการใช้ช่วงเปิดบริการ',
  sessionsUnit: 'รายการ', hoursUnit: 'ชม.', roomsUnit: 'ห้อง', trend: 'แนวโน้มการใช้ห้อง', trendHint: 'จำนวนรายการตามช่วงเวลาที่เลือก',
  ranked: 'ห้องที่ถูกใช้มากที่สุด', userRanked: 'ผู้ใช้งานสูงสุด', rankedHint: 'จัดอันดับจากจำนวนชั่วโมงที่ถูกจอง', userRankedHint: 'จัดอันดับจากจำนวนครั้งการจอง', room: 'ห้อง', users: 'ผู้ใช้งาน', share: 'สัดส่วน', viewAll: 'ดูอันดับทั้งหมด', allUsers: 'อันดับผู้ใช้งานทั้งหมด', allRooms: 'อันดับห้องทั้งหมด', rank: 'อันดับ', close: 'ปิด',
  usageOutcome: 'ผลการเข้าใช้งาน', usageOutcomeHint: 'สัดส่วนจากรายการจองทั้งหมดในช่วงที่เลือก', confirmed: 'เข้าใช้งาน', cancelled: 'ยกเลิก', noShow: 'ไม่เข้าใช้งาน', pending: 'รอเข้าใช้งาน', checkingStatus: 'กำลังตรวจสอบสถานะ…',
  summary: 'ข้อมูลสำคัญ', busiestDay: 'วันที่มีการใช้สูงสุด', busiestRoom: 'ห้องยอดนิยม', busiestUser: 'ผู้ใช้งานสูงสุด', busiestTime: 'ช่วงเวลายอดนิยม', average: 'เฉลี่ยต่อวันที่มีตาราง',
  noData: 'ไม่มีข้อมูลตารางในช่วงเวลานี้', loadError: 'ไม่สามารถโหลดข้อมูลสถิติได้', retry: 'ลองอีกครั้ง', openHours: 'คำนวณจากเวลาเปิดบริการ 07:00–19:00',
  currentSemester: 'ภาคการศึกษาปัจจุบัน', allSemester: 'ข้อมูลทั้งหมดในภาคเรียน', chartSessions: 'รายการ',
} : {
  title: 'Room Usage Analytics', subtitle: 'Analyze usage volume and peak demand periods',
  week: 'This week', month: 'Monthly', semester: 'Full semester', selectMonth: 'Select month', selectYear: 'Select year', selectUser: 'Select user', everyUser: 'All users', refresh: 'Refresh', updating: 'Loading…', updated: 'Last updated',
  sessions: 'Bookings', hours: 'Booked hours', rooms: 'Active rooms', utilization: 'Open-hours utilization',
  sessionsUnit: 'entries', hoursUnit: 'hrs', roomsUnit: 'rooms', trend: 'Usage trend', trendHint: 'Bookings within the selected period',
  ranked: 'Most-used rooms', userRanked: 'Top users', rankedHint: 'Ranked by total booked hours', userRankedHint: 'Ranked by number of bookings', room: 'Room', users: 'Users', share: 'Share', viewAll: 'View all rankings', allUsers: 'All user rankings', allRooms: 'All room rankings', rank: 'Rank', close: 'Close',
  usageOutcome: 'Usage outcomes', usageOutcomeHint: 'Share of all bookings in the selected period', confirmed: 'Used', cancelled: 'Cancelled', noShow: 'No-show', pending: 'Awaiting use', checkingStatus: 'Checking statuses…',
  summary: 'Key findings', busiestDay: 'Busiest day', busiestRoom: 'Most popular room', busiestUser: 'Top user', busiestTime: 'Peak period', average: 'Average per active day',
  noData: 'No schedule data for this period', loadError: 'Unable to load analytics data', retry: 'Try again', openHours: 'Based on service hours 07:00–19:00',
  currentSemester: 'Current semester', allSemester: 'All semester data', chartSessions: 'entries',
})

function localDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
function parseDate(value: string) { return new Date(`${value.slice(0, 10)}T00:00:00`) }
function addDays(date: Date, days: number) { const result = new Date(date); result.setDate(result.getDate() + days); return result }
function startOfWeek(date: Date) { const result = new Date(date); const day = result.getDay() || 7; result.setDate(result.getDate() - day + 1); result.setHours(0, 0, 0, 0); return result }
function minutes(value = '') { const [hour = 0, minute = 0] = value.split(':').map(Number); return hour * 60 + minute }
function durationHours(row: ScheduleItem) { return Math.max(0, minutes(row.finishTime) - minutes(row.startTime)) / 60 }
function formatNumber(value: number, maximumFractionDigits = 0) { return new Intl.NumberFormat(locale.value === 'th' ? 'th-TH' : 'en-US', { maximumFractionDigits }).format(value) }
function formatDate(date: Date, options: Intl.DateTimeFormatOptions) { return date.toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-GB', options) }
function rangeLabel(start: Date, end: Date) {
  if (selectedRange.value === 'semester') return semesterStore.semester ? `${copy.value.currentSemester} ${semesterStore.semester.semester}/${semesterStore.semester.year_no}` : copy.value.allSemester
  return `${formatDate(start, { day: 'numeric', month: 'short' })} – ${formatDate(end, { day: 'numeric', month: 'short', year: 'numeric' })}`
}

const rangeBounds = computed(() => {
  if (selectedRange.value === 'week') { const start = startOfWeek(now); return { start, end: addDays(start, 6) } }
  if (selectedRange.value === 'month') return { start: new Date(selectedYear.value, selectedMonth.value, 1), end: new Date(selectedYear.value, selectedMonth.value + 1, 0) }
  const dated = schedules.value.map(row => parseDate(row.schedule_date)).filter(date => !Number.isNaN(date.getTime())).sort((a, b) => a.getTime() - b.getTime())
  return { start: dated[0] ?? now, end: dated[dated.length - 1] ?? now }
})
const selectedRangeLabel = computed(() => rangeLabel(rangeBounds.value.start, rangeBounds.value.end))
const monthOptions = computed(() => Array.from({ length: 12 }, (_, index) => ({
  value: index,
  label: new Date(2024, index, 1).toLocaleDateString(locale.value === 'th' ? 'th-TH' : 'en-GB', { month: 'long' }),
})))
const yearOptions = computed(() => {
  const years = new Set(schedules.value.map(row => parseDate(row.schedule_date).getFullYear()).filter(year => Number.isFinite(year)))
  years.add(now.getFullYear())
  return [...years].sort((a, b) => b - a)
})
function selectCalendarMonth() { selectedRange.value = 'month' }
const dateFilteredSchedules = computed(() => schedules.value.filter(row => {
  const date = parseDate(row.schedule_date)
  return date >= rangeBounds.value.start && date <= rangeBounds.value.end
}))
const userOptions = computed(() => [...new Set(dateFilteredSchedules.value.map(ownerName).filter(Boolean))]
  .sort((a, b) => a.localeCompare(b, locale.value === 'th' ? 'th' : 'en', { sensitivity: 'base' })))
const filteredSchedules = computed(() => selectedUser.value
  ? dateFilteredSchedules.value.filter(row => ownerName(row) === selectedUser.value)
  : dateFilteredSchedules.value)
const totalHours = computed(() => filteredSchedules.value.reduce((sum, row) => sum + durationHours(row), 0))
const activeRooms = computed(() => new Set(filteredSchedules.value.map(row => row.roomcode).filter(Boolean)).size)
const calendarDays = computed(() => Math.max(1, Math.round((rangeBounds.value.end.getTime() - rangeBounds.value.start.getTime()) / 86_400_000) + 1))
const utilization = computed(() => activeRooms.value ? Math.min(100, totalHours.value / (activeRooms.value * calendarDays.value * 12) * 100) : 0)

const roomStats = computed<RoomStat[]>(() => {
  const map = new Map<string, { sessions: number; hours: number }>()
  filteredSchedules.value.forEach(row => {
    const current = map.get(row.roomcode) ?? { sessions: 0, hours: 0 }
    current.sessions += 1; current.hours += durationHours(row); map.set(row.roomcode, current)
  })
  const total = [...map.values()].reduce((sum, row) => sum + row.hours, 0)
  return [...map].map(([room, value]) => ({ room, ...value, share: total ? value.hours / total * 100 : 0 })).sort((a, b) => b.hours - a.hours || b.sessions - a.sessions)
})
const maxRoomHours = computed(() => Math.max(1, ...roomStats.value.map(row => row.hours)))

function ownerName(row: ScheduleItem) {
  if (Array.isArray(row.teacher_name)) {
    const teacher = row.teacher_name[0]
    if (teacher) return `${teacher.prefixname ?? ''}${teacher.officername ?? ''} ${teacher.officersurname ?? ''}`.trim()
  }
  if (typeof row.teacher_name === 'string' && row.teacher_name.trim()) return row.teacher_name.trim()
  return row.user_name?.trim() || row.user_login?.trim() || ''
}
watch(userOptions, users => {
  if (selectedUser.value && !users.includes(selectedUser.value)) selectedUser.value = ''
})
const userStats = computed<UserStat[]>(() => {
  const users = new Map<string, { sessions: number; hours: number }>()
  filteredSchedules.value.forEach(row => {
    const name = ownerName(row)
    if (!name) return
    const current = users.get(name) ?? { sessions: 0, hours: 0 }
    current.sessions += 1
    current.hours += durationHours(row)
    users.set(name, current)
  })
  const total = [...users.values()].reduce((sum, row) => sum + row.sessions, 0)
  return [...users].map(([name, value]) => ({ name, ...value, share: total ? value.sessions / total * 100 : 0 })).sort((a, b) => b.sessions - a.sessions || b.hours - a.hours)
})
const maxUserSessions = computed(() => Math.max(1, ...userStats.value.map(row => row.sessions)))

function openRankings(view: 'users' | 'rooms') { rankingView.value = view; rankingDialog.value?.showModal() }
function closeRankings() { rankingDialog.value?.close() }

const dailyPoints = computed<TrendPoint[]>(() => {
  const points: TrendPoint[] = []
  for (let date = new Date(rangeBounds.value.start); date <= rangeBounds.value.end; date = addDays(date, 1)) {
    const key = localDate(date)
    const rows = filteredSchedules.value.filter(row => row.schedule_date.slice(0, 10) === key)
    points.push({ key, label: formatDate(date, { day: 'numeric', month: selectedRange.value === 'month' ? undefined : 'short' }), fullLabel: formatDate(date, { weekday: 'short', day: 'numeric', month: 'short' }), sessions: rows.length, hours: rows.reduce((sum, row) => sum + durationHours(row), 0) })
  }
  return points
})
const trendPoints = computed<TrendPoint[]>(() => {
  if (selectedRange.value !== 'semester') return dailyPoints.value
  const weeks = new Map<string, TrendPoint>()
  filteredSchedules.value.forEach(row => {
    const start = startOfWeek(parseDate(row.schedule_date)); const key = localDate(start)
    const point = weeks.get(key) ?? { key, label: formatDate(start, { day: 'numeric', month: 'short' }), fullLabel: `${formatDate(start, { day: 'numeric', month: 'short' })} – ${formatDate(addDays(start, 6), { day: 'numeric', month: 'short' })}`, sessions: 0, hours: 0 }
    point.sessions += 1; point.hours += durationHours(row); weeks.set(key, point)
  })
  return [...weeks.values()].sort((a, b) => a.key.localeCompare(b.key))
})
const maxTrend = computed(() => Math.max(1, ...trendPoints.value.map(point => point.sessions)))

function scheduleKey(row: ScheduleItem) { return String(row.rowId ?? row.id ?? '') }
function scheduleEnd(row: ScheduleItem) {
  const time = (row.finishTime || '00:00').replace('.', ':')
  return new Date(`${row.schedule_date.slice(0, 10)}T${time.slice(0, 5)}:00`)
}
async function loadUsageStatuses(rows: ScheduleItem[]) {
  const generation = ++statusLoadGeneration
  const cache = new Map(usageStatusCache.value)
  const pendingRows = rows.filter(row => {
    const key = scheduleKey(row)
    if (!key || cache.has(key)) return false
    if (row.usage_status !== undefined && row.usage_status !== null) { cache.set(key, Number(row.usage_status) || 0); return false }
    return true
  })
  if (!pendingRows.length) { usageStatusCache.value = cache; statusLoading.value = false; return }
  statusLoading.value = true
  let cursor = 0
  const worker = async () => {
    while (cursor < pendingRows.length && generation === statusLoadGeneration) {
      const row = pendingRows[cursor++]
      const key = scheduleKey(row)
      try {
        const response = await fetch(`${API}/schedule/check_usage_status/?schedule_id=${encodeURIComponent(key)}`)
        if (!response.ok) continue
        const payload = await response.json() as { usage_status?: number | string }
        cache.set(key, Number(payload.usage_status) || 0)
      } catch { /* A missing status remains uncached and can be retried on refresh. */ }
    }
  }
  await Promise.all(Array.from({ length: Math.min(12, pendingRows.length) }, worker))
  if (generation === statusLoadGeneration) { usageStatusCache.value = cache; statusLoading.value = false }
}

const usageOutcomes = computed(() => {
  const result = { total: filteredSchedules.value.length, confirmed: 0, cancelled: 0, noShow: 0, pending: 0 }
  filteredSchedules.value.forEach(row => {
    const status = usageStatusCache.value.get(scheduleKey(row)) ?? (Number(row.usage_status) || 0)
    if (status === 3) result.confirmed += 1
    else if (status === 4 || status === 5) result.cancelled += 1
    else if (scheduleEnd(row).getTime() < Date.now()) result.noShow += 1
    else result.pending += 1
  })
  return result
})
function outcomePercent(count: number) { return usageOutcomes.value.total ? count / usageOutcomes.value.total * 100 : 0 }

watch(filteredSchedules, rows => { loadUsageStatuses(rows) }, { immediate: true })

async function load() {
  loading.value = true; error.value = ''
  try {
    const response = await fetch(`${API}/schedule/get_schedule_from_json/`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    schedules.value = Array.isArray(payload) ? payload : []
    updatedAt.value = new Date()
  } catch { error.value = copy.value.loadError }
  finally { loading.value = false }
}

const updatedLabel = computed(() => updatedAt.value?.toLocaleTimeString(locale.value === 'th' ? 'th-TH' : 'en-GB', { hour: '2-digit', minute: '2-digit' }) ?? '—')
onMounted(() => { load(); semesterStore.fetchActiveSemester(API) })
</script>

<template>
  <div class="analytics-dashboard">
    <header class="page-header">
      <div><h1>{{ copy.title }}</h1><p>{{ copy.subtitle }}</p></div>
      <div class="header-controls">
        <div class="range-tabs" role="group" aria-label="ช่วงเวลาสถิติ">
          <button v-for="range in (['week','month','semester'] as RangeKey[])" :key="range" type="button" :class="{ active: selectedRange === range }" @click="selectedRange = range">{{ copy[range] }}</button>
        </div>
        <div class="date-filters">
          <label class="user-filter"><span>{{ copy.selectUser }}</span><select v-model="selectedUser" :aria-label="copy.selectUser"><option value="">{{ copy.everyUser }}</option><option v-for="user in userOptions" :key="user" :value="user">{{ user }}</option></select></label>
          <label><span>{{ copy.selectMonth }}</span><select v-model.number="selectedMonth" @change="selectCalendarMonth"><option v-for="item in monthOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
          <label><span>{{ copy.selectYear }}</span><select v-model.number="selectedYear" @change="selectCalendarMonth"><option v-for="year in yearOptions" :key="year" :value="year">{{ locale === 'th' ? year + 543 : year }}</option></select></label>
        </div>
        <button class="refresh" type="button" :disabled="loading" @click="load"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 0 0-15.5-2M4 4v5h5M4 13a8 8 0 0 0 15.5 2M20 20v-5h-5" /></svg>{{ loading ? copy.updating : copy.refresh }}</button>
      </div>
    </header>

    <div class="period-line"><strong>{{ selectedRangeLabel }}</strong><span>{{ copy.updated }} {{ updatedLabel }}</span></div>
    <div v-if="error" class="error" role="alert"><span>{{ error }}</span><button type="button" @click="load">{{ copy.retry }}</button></div>

    <section class="metric-strip" aria-label="สรุปสถิติ">
      <div><span>{{ copy.sessions }}</span><strong>{{ formatNumber(filteredSchedules.length) }}</strong><small>{{ copy.sessionsUnit }}</small></div>
      <div><span>{{ copy.hours }}</span><strong>{{ formatNumber(totalHours, 1) }}</strong><small>{{ copy.hoursUnit }}</small></div>
      <div><span>{{ copy.rooms }}</span><strong>{{ formatNumber(activeRooms) }}</strong><small>{{ copy.roomsUnit }}</small></div>
      <div><span>{{ copy.utilization }}</span><strong>{{ formatNumber(utilization, 1) }}%</strong><small>{{ copy.openHours }}</small></div>
    </section>

    <main v-if="!loading && filteredSchedules.length" class="analytics-grid">
      <section class="trend-panel panel">
        <header><div><h2>{{ copy.trend }}</h2><p>{{ copy.trendHint }}</p></div><strong>{{ formatNumber(filteredSchedules.length) }} <small>{{ copy.chartSessions }}</small></strong></header>
        <div class="trend-chart" :class="`range-${selectedRange}`">
          <div v-for="point in trendPoints" :key="point.key" class="trend-column" :title="`${point.fullLabel}: ${point.sessions} ${copy.sessionsUnit}`">
            <span v-if="selectedRange !== 'month' || point.sessions" class="bar-value">{{ point.sessions }}</span>
            <div class="bar-track"><i :style="{ height: `${Math.max(point.sessions ? 8 : 0, point.sessions / maxTrend * 100)}%` }"></i></div>
            <small>{{ point.label }}</small>
          </div>
        </div>
      </section>

      <section class="ranking-panel panel">
        <header><div><h2>{{ copy.userRanked }}</h2><p>{{ copy.userRankedHint }}</p></div><button class="view-all" type="button" @click="openRankings('users')">{{ copy.viewAll }}</button></header>
        <div class="ranking-list">
          <div v-for="(row, index) in userStats.slice(0, 5)" :key="row.name" class="rank-row">
            <b>{{ index + 1 }}</b><div class="rank-detail"><div><strong :title="row.name">{{ row.name }}</strong><span>{{ formatNumber(row.sessions) }} {{ copy.sessionsUnit }} · {{ formatNumber(row.hours, 1) }} {{ copy.hoursUnit }}</span></div><div class="rank-track"><i :style="{ width: `${row.sessions / maxUserSessions * 100}%` }"></i></div></div><em>{{ formatNumber(row.share, 1) }}%</em>
          </div>
        </div>
      </section>

      <section class="usage-outcome-panel panel">
        <header><div><h2>{{ copy.usageOutcome }}</h2><p>{{ statusLoading ? copy.checkingStatus : copy.usageOutcomeHint }}</p></div></header>
        <div class="outcome-grid" :class="{ checking: statusLoading }">
          <article class="outcome-card total"><span><i></i>{{ copy.sessions }}</span><strong>{{ formatNumber(usageOutcomes.total) }}</strong><small>100% · {{ copy.sessionsUnit }}</small></article>
          <article class="outcome-card confirmed"><span><i></i>{{ copy.confirmed }}</span><strong>{{ statusLoading ? '…' : `${formatNumber(outcomePercent(usageOutcomes.confirmed), 1)}%` }}</strong><small>{{ formatNumber(usageOutcomes.confirmed) }} {{ copy.sessionsUnit }}</small></article>
          <article class="outcome-card cancelled"><span><i></i>{{ copy.cancelled }}</span><strong>{{ statusLoading ? '…' : `${formatNumber(outcomePercent(usageOutcomes.cancelled), 1)}%` }}</strong><small>{{ formatNumber(usageOutcomes.cancelled) }} {{ copy.sessionsUnit }}</small></article>
          <article class="outcome-card no-show"><span><i></i>{{ copy.noShow }}</span><strong>{{ statusLoading ? '…' : `${formatNumber(outcomePercent(usageOutcomes.noShow), 1)}%` }}</strong><small>{{ formatNumber(usageOutcomes.noShow) }} {{ copy.sessionsUnit }}</small></article>
          <article class="outcome-card pending"><span><i></i>{{ copy.pending }}</span><strong>{{ statusLoading ? '…' : `${formatNumber(outcomePercent(usageOutcomes.pending), 1)}%` }}</strong><small>{{ formatNumber(usageOutcomes.pending) }} {{ copy.sessionsUnit }}</small></article>
        </div>
      </section>

      <section class="ranking-panel room-ranking-panel panel">
        <header><div><h2>{{ copy.ranked }}</h2><p>{{ copy.rankedHint }}</p></div><button class="view-all" type="button" @click="openRankings('rooms')">{{ copy.viewAll }}</button></header>
        <div class="ranking-list">
          <div v-for="(row, index) in roomStats.slice(0, 5)" :key="row.room" class="rank-row">
            <b>{{ index + 1 }}</b><div class="rank-detail"><div><strong>{{ row.room }}</strong><span>{{ formatNumber(row.sessions) }} {{ copy.sessionsUnit }} · {{ formatNumber(row.hours, 1) }} {{ copy.hoursUnit }}</span></div><div class="rank-track"><i :style="{ width: `${row.hours / maxRoomHours * 100}%` }"></i></div></div><em>{{ formatNumber(row.share, 1) }}%</em>
          </div>
        </div>
      </section>
    </main>

    <div v-else-if="loading" class="loading-grid" aria-label="กำลังโหลด"><i v-for="n in 4" :key="n"></i></div>
    <div v-else class="empty-state">{{ copy.noData }}</div>

    <dialog ref="rankingDialog" class="ranking-dialog" @click.self="closeRankings">
      <header><div><h2>{{ rankingView === 'users' ? copy.allUsers : copy.allRooms }}</h2><p>{{ selectedRangeLabel }}</p></div><button type="button" :aria-label="copy.close" @click="closeRankings"><svg viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18" /></svg></button></header>
      <div class="all-ranking-table-wrap">
        <table><thead><tr><th>{{ copy.rank }}</th><th>{{ rankingView === 'users' ? copy.users : copy.room }}</th><th>{{ copy.sessions }}</th><th>{{ copy.hours }}</th><th>{{ copy.share }}</th></tr></thead>
          <tbody v-if="rankingView === 'users'"><tr v-for="(row, index) in userStats" :key="row.name"><td><b>{{ index + 1 }}</b></td><td><strong>{{ row.name }}</strong></td><td>{{ formatNumber(row.sessions) }}</td><td>{{ formatNumber(row.hours, 1) }} {{ copy.hoursUnit }}</td><td>{{ formatNumber(row.share, 1) }}%</td></tr></tbody>
          <tbody v-else><tr v-for="(row, index) in roomStats" :key="row.room"><td><b>{{ index + 1 }}</b></td><td><strong>{{ row.room }}</strong></td><td>{{ formatNumber(row.sessions) }}</td><td>{{ formatNumber(row.hours, 1) }} {{ copy.hoursUnit }}</td><td>{{ formatNumber(row.share, 1) }}%</td></tr></tbody>
        </table>
      </div>
      <footer><button type="button" @click="closeRankings">{{ copy.close }}</button></footer>
    </dialog>
  </div>
</template>

<style scoped>
.analytics-dashboard{height:calc(100vh - 4rem);min-height:650px;display:grid;grid-template-rows:auto auto auto minmax(0,1fr);gap:12px;color:var(--dashboard-text);font-family:'Kanit',sans-serif}.page-header,.header-controls,.period-line,.panel>header,.rank-detail>div:first-child{display:flex;align-items:center}.page-header{justify-content:space-between;gap:24px}.page-header h1{margin:0;font-size:1.75rem;line-height:1.2;letter-spacing:-.025em}.page-header p{margin:4px 0 0;color:var(--dashboard-text-secondary);font-size:.8rem}.header-controls{gap:9px}.range-tabs{display:flex;padding:3px;border:1px solid var(--dashboard-border);border-radius:10px;background:var(--dashboard-surface)}.range-tabs button{padding:7px 11px;border:0;border-radius:7px;background:transparent;color:var(--dashboard-text-secondary);font:inherit;font-size:.7rem;cursor:pointer}.range-tabs button.active{background:var(--dashboard-accent);color:var(--brand-on-primary);font-weight:600}.refresh{display:flex;align-items:center;gap:6px;padding:9px 11px;border:1px solid var(--dashboard-border);border-radius:9px;background:var(--dashboard-surface);color:var(--dashboard-accent);font:inherit;font-size:.7rem;font-weight:600;cursor:pointer}.refresh:disabled{opacity:.6}.refresh svg{width:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round}.period-line{justify-content:space-between;color:var(--dashboard-text-muted);font-size:.65rem}.period-line strong{color:var(--dashboard-text-secondary);font-weight:500}.error{display:flex;justify-content:space-between;padding:8px 11px;border:1px solid var(--dashboard-error-border);border-radius:8px;background:var(--dashboard-error-bg);color:var(--dashboard-error-text);font-size:.7rem}.error button{border:0;background:transparent;color:inherit;font:inherit;font-weight:700;cursor:pointer}.metric-strip{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--dashboard-border);border-radius:13px;background:var(--dashboard-surface);box-shadow:0 4px 14px rgb(15 23 42/.06)}.metric-strip>div{position:relative;padding:12px 17px}.metric-strip>div+div:before{content:'';position:absolute;left:0;top:12px;bottom:12px;width:1px;background:var(--dashboard-border-soft)}.metric-strip span,.metric-strip small{display:block;color:var(--dashboard-text-muted)}.metric-strip span{font-size:.68rem}.metric-strip strong{display:inline-block;margin-top:3px;font-size:1.55rem;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}.metric-strip small{min-height:1em;margin-top:3px;font-size:.55rem}.analytics-grid{min-height:0;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(340px,.8fr);grid-template-rows:minmax(0,1.1fr) minmax(180px,.9fr);gap:12px}.panel{min-height:0;overflow:hidden;border:1px solid var(--dashboard-border);border-radius:13px;background:var(--dashboard-surface)}.panel>header{min-height:48px;justify-content:space-between;padding:8px 13px;border-bottom:1px solid var(--dashboard-border-soft)}.panel h2{margin:0;font-size:.86rem}.panel header p{margin:2px 0 0;color:var(--dashboard-text-muted);font-size:.59rem}.panel>header>strong{font-size:1.2rem}.panel>header>strong small{color:var(--dashboard-text-muted);font-size:.55rem;font-weight:400}.trend-panel{display:flex;flex-direction:column}.trend-chart{min-height:0;flex:1;display:flex;align-items:stretch;gap:8px;padding:18px 14px 10px}.trend-column{min-width:0;flex:1;display:grid;grid-template-rows:16px minmax(50px,1fr) 16px;align-items:end;text-align:center}.bar-value{color:var(--dashboard-text-secondary);font-size:.55rem;font-variant-numeric:tabular-nums}.bar-track{height:100%;display:flex;align-items:flex-end;justify-content:center;border-bottom:1px solid var(--dashboard-border)}.bar-track i{display:block;width:min(28px,65%);min-height:0;border-radius:4px 4px 1px 1px;background:var(--dashboard-accent);transition:height .25s ease-out}.trend-column small{padding-top:4px;overflow:hidden;color:var(--dashboard-text-muted);font-size:.52rem;white-space:nowrap}.range-month.trend-chart{gap:2px;padding-inline:9px}.range-month .trend-column small{font-size:.42rem}.range-month .trend-column:nth-child(even) small{visibility:hidden}.range-semester.trend-chart{gap:4px}.ranking-panel{display:flex;flex-direction:column}.ranking-list{min-height:0;overflow:auto;padding:5px 12px}.rank-row{display:grid;grid-template-columns:22px minmax(0,1fr) 42px;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--dashboard-border-soft)}.rank-row:last-child{border-bottom:0}.rank-row>b{width:20px;height:20px;display:grid;place-items:center;border-radius:6px;background:var(--dashboard-surface-muted);color:var(--dashboard-text-secondary);font-size:.58rem}.rank-detail{min-width:0}.rank-detail>div:first-child{justify-content:space-between;gap:8px}.rank-detail strong{font-size:.68rem}.rank-detail span{overflow:hidden;color:var(--dashboard-text-muted);font-size:.53rem;text-overflow:ellipsis;white-space:nowrap}.rank-track,.demand-track{overflow:hidden;background:var(--dashboard-surface-muted)}.rank-track{height:4px;margin-top:5px;border-radius:2px}.rank-track i{display:block;height:100%;border-radius:inherit;background:var(--dashboard-accent)}.rank-row>em{color:var(--dashboard-text-secondary);font-size:.58rem;font-style:normal;text-align:right}.demand-panel{display:flex;flex-direction:column}.demand-list{display:grid;gap:10px;padding:12px 14px}.demand-row{display:grid;grid-template-columns:90px minmax(0,1fr) 55px;align-items:center;gap:10px}.demand-row>div:first-child strong,.demand-row>div:first-child small{display:block}.demand-row>div:first-child strong{font-size:.67rem}.demand-row>div:first-child small{color:var(--dashboard-text-muted);font-size:.52rem}.demand-track{height:9px;border-radius:3px}.demand-track i{display:block;height:100%;border-radius:inherit;background:var(--chart-blue)}.demand-track i.afternoon{background:var(--chart-aqua)}.demand-track i.evening{background:var(--chart-orange)}.demand-row>span{text-align:right}.demand-row>span strong,.demand-row>span small{display:block}.demand-row>span strong{font-size:.72rem}.demand-row>span small{color:var(--dashboard-text-muted);font-size:.5rem}.insights-panel{display:flex;flex-direction:column}.insights-panel dl{min-height:0;display:grid;grid-template-columns:1fr 1fr;margin:0}.insights-panel dl>div{display:flex;flex-direction:column;justify-content:center;padding:9px 12px;border-bottom:1px solid var(--dashboard-border-soft)}.insights-panel dl>div:nth-child(odd){border-right:1px solid var(--dashboard-border-soft)}.insights-panel dl>div:nth-child(n+3){border-bottom:0}.insights-panel dt{display:flex;align-items:center;gap:5px;color:var(--dashboard-text-muted);font-size:.55rem}.insights-panel dt svg{width:13px;fill:none;stroke:var(--dashboard-accent);stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.insights-panel dd{margin:4px 0 0;font-size:.72rem;font-weight:600}.insights-panel dd small{display:block;margin-top:1px;color:var(--dashboard-text-muted);font-size:.52rem;font-weight:400}.loading-grid{min-height:0;display:grid;grid-template-columns:1.5fr .8fr;grid-template-rows:1fr .8fr;gap:12px}.loading-grid i{border-radius:13px;background:var(--dashboard-surface);animation:pulse 1s infinite alternate}@keyframes pulse{to{opacity:.45}}.empty-state{min-height:260px;display:grid;place-items:center;border:1px solid var(--dashboard-border);border-radius:13px;background:var(--dashboard-surface);color:var(--dashboard-text-muted);font-size:.76rem}.analytics-dashboard :focus-visible{outline:3px solid color-mix(in srgb,var(--dashboard-accent) 35%,transparent);outline-offset:2px}.analytics-dashboard ::selection{background:var(--dashboard-accent);color:var(--brand-on-primary)}.analytics-dashboard *{scrollbar-width:thin;scrollbar-color:var(--dashboard-border-muted) transparent}@media(max-width:1150px){.analytics-dashboard{height:auto;min-height:calc(100vh - 4rem)}.analytics-grid{grid-template-columns:1fr;grid-template-rows:320px 330px auto auto}.ranking-panel{max-height:330px}}@media(max-width:760px){.page-header{align-items:flex-start;flex-direction:column}.header-controls{width:100%;flex-wrap:wrap}.range-tabs{flex:1}.range-tabs button{flex:1}.metric-strip{grid-template-columns:1fr 1fr}.metric-strip>div:nth-child(3):before{top:0;right:12px;bottom:auto;width:auto;height:1px}.analytics-grid{grid-template-rows:290px 330px auto auto}.trend-chart{gap:3px;padding-inline:8px}.trend-column small{font-size:.44rem}.demand-row{grid-template-columns:82px minmax(0,1fr) 48px}}
</style>

<style scoped>
.ranking-tabs button{font-size:.67rem}.view-all{font-size:.68rem}.ranking-dialog h2{font-size:1.12rem}.ranking-dialog header p{font-size:.77rem}.ranking-dialog th{font-size:.77rem}.ranking-dialog td{font-size:.78rem}.ranking-dialog td:first-child b{font-size:.7rem}.ranking-dialog>footer button{font-size:.77rem}
</style>

<style scoped>
/* Readability scale: approximately +2px across the analytics surface. */
.date-filters{display:flex;gap:6px}.date-filters label{position:relative;min-width:0}.date-filters label>span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}.date-filters select{height:35px;max-width:100%;padding:0 27px 0 9px;border:1px solid var(--dashboard-border);border-radius:8px;background:var(--dashboard-surface);color:var(--dashboard-text);font:inherit;font-size:.78rem;cursor:pointer}.date-filters .user-filter select{width:190px}.date-filters select:focus{border-color:var(--dashboard-accent)}
.usage-outcome-panel{display:flex;flex-direction:column}.outcome-grid{min-height:0;flex:1;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;padding:10px}.outcome-card{min-width:0;display:flex;flex-direction:column;justify-content:center;padding:10px;border:1px solid var(--dashboard-border-soft);border-radius:10px;background:var(--dashboard-surface-raised)}.outcome-card>span{display:flex;align-items:center;gap:5px;color:var(--dashboard-text-secondary);font-size:.68rem;white-space:nowrap}.outcome-card>span i{width:7px;height:7px;flex:0 0 7px;border-radius:50%;background:var(--dashboard-accent)}.outcome-card>strong{margin-top:5px;font-size:1.2rem;line-height:1;font-variant-numeric:tabular-nums}.outcome-card>small{margin-top:4px;color:var(--dashboard-text-muted);font-size:.58rem}.outcome-card.confirmed>span i{background:var(--status-free)}.outcome-card.cancelled>span i{background:var(--status-busy)}.outcome-card.no-show>span i{background:var(--status-unknown)}.outcome-card.pending>span i{background:var(--status-pending)}.outcome-grid.checking .outcome-card:not(.total){opacity:.72}
.page-header h1{font-size:1.9rem}.page-header p{font-size:.92rem}.range-tabs button,.refresh{font-size:.82rem}.period-line{font-size:.77rem}.error{font-size:.82rem}.metric-strip span{font-size:.8rem}.metric-strip strong{font-size:1.68rem}.metric-strip small{font-size:.67rem}.panel h2{font-size:1rem}.panel header p{font-size:.71rem}.panel>header>strong{font-size:1.32rem}.panel>header>strong small{font-size:.67rem}.bar-value{font-size:.67rem}.trend-column small{font-size:.64rem}.range-month .trend-column small{font-size:.54rem}.rank-row>b{font-size:.7rem}.rank-detail strong{font-size:.8rem}.rank-detail span{font-size:.65rem}.rank-row>em{font-size:.7rem}.demand-row>div:first-child strong{font-size:.79rem}.demand-row>div:first-child small{font-size:.64rem}.demand-row>span strong{font-size:.84rem}.demand-row>span small{font-size:.62rem}.insights-panel dt{font-size:.67rem}.insights-panel dd{font-size:.84rem}.insights-panel dd small{font-size:.64rem}.empty-state{font-size:.88rem}.ranking-tabs button{font-size:.67rem}.view-all{font-size:.68rem}.ranking-dialog h2{font-size:1.12rem}.ranking-dialog header p{font-size:.77rem}.ranking-dialog th{font-size:.77rem}.ranking-dialog td{font-size:.78rem}.ranking-dialog td:first-child b{font-size:.7rem}.ranking-dialog>footer button{font-size:.77rem}
@media(max-width:760px){.date-filters{width:100%}.date-filters label{flex:1}.date-filters .user-filter{flex:1.5}.date-filters select,.date-filters .user-filter select{width:100%}.outcome-grid{grid-template-columns:repeat(2,1fr)}.outcome-card.total{grid-column:1/-1}}
</style>

<style scoped>
.ranking-actions{display:flex;align-items:center;gap:7px}.ranking-tabs{display:flex;padding:2px;border:1px solid var(--dashboard-border);border-radius:7px;background:var(--dashboard-surface-muted)}.ranking-tabs button{padding:4px 7px;border:0;border-radius:5px;background:transparent;color:var(--dashboard-text-secondary);font:inherit;font-size:.67rem;cursor:pointer}.ranking-tabs button.active{background:var(--dashboard-surface);color:var(--dashboard-accent);font-weight:600}.view-all{padding:5px 7px;border:0;background:transparent;color:var(--dashboard-accent);font:inherit;font-size:.68rem;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:3px}.rank-detail strong{max-width:48%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ranking-dialog{width:min(760px,calc(100vw - 32px));max-height:min(78vh,680px);padding:0;border:1px solid var(--dashboard-border);border-radius:14px;background:var(--dashboard-surface);color:var(--dashboard-text);box-shadow:0 24px 70px rgb(15 23 42/.3);font-family:'Kanit',sans-serif}.ranking-dialog::backdrop{background:rgb(15 23 42/.5)}.ranking-dialog>header{display:flex;align-items:center;justify-content:space-between;padding:15px 18px;border-bottom:1px solid var(--dashboard-border)}.ranking-dialog h2{margin:0;font-size:1.12rem}.ranking-dialog header p{margin:2px 0 0;color:var(--dashboard-text-muted);font-size:.77rem}.ranking-dialog header button{width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--dashboard-border);border-radius:8px;background:var(--dashboard-surface-muted);color:var(--dashboard-text);cursor:pointer}.ranking-dialog header svg{width:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round}.all-ranking-table-wrap{max-height:55vh;overflow:auto}.ranking-dialog table{width:100%;border-collapse:collapse}.ranking-dialog th{position:sticky;top:0;padding:9px 12px;background:var(--dashboard-surface-muted);color:var(--dashboard-text-secondary);font-size:.77rem;font-weight:600;text-align:left}.ranking-dialog td{padding:9px 12px;border-bottom:1px solid var(--dashboard-border-soft);font-size:.78rem}.ranking-dialog th:first-child,.ranking-dialog td:first-child{width:54px;text-align:center}.ranking-dialog th:nth-child(n+3),.ranking-dialog td:nth-child(n+3){text-align:right}.ranking-dialog td:first-child b{width:22px;height:22px;display:inline-grid;place-items:center;border-radius:6px;background:var(--dashboard-accent-soft);color:var(--dashboard-accent);font-size:.7rem}.ranking-dialog tbody tr:nth-child(even){background:color-mix(in srgb,var(--dashboard-surface-muted) 42%,transparent)}.ranking-dialog>footer{display:flex;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--dashboard-border)}.ranking-dialog>footer button{padding:7px 14px;border:0;border-radius:8px;background:var(--dashboard-accent);color:var(--brand-on-primary);font:inherit;font-size:.77rem;font-weight:600;cursor:pointer}@media(max-width:760px){.ranking-panel>header{align-items:flex-start;flex-direction:column}.ranking-actions{width:100%;justify-content:space-between}.ranking-dialog th:nth-child(4),.ranking-dialog td:nth-child(4){display:none}.ranking-dialog th,.ranking-dialog td{padding-inline:8px}}
</style>

<style scoped>
/* Visual polish pass for the analytics workspace. */
.analytics-dashboard{gap:14px}.page-header{min-height:74px}.page-header h1{font-size:2.15rem;letter-spacing:-.035em}.page-header p{max-width:560px;margin-top:6px;color:var(--dashboard-text-secondary);font-size:.9rem}.header-controls{align-self:flex-start;padding-top:5px}.range-tabs{padding:4px;border-color:var(--dashboard-border-soft);box-shadow:0 3px 10px rgb(15 23 42/.05)}.range-tabs button{min-height:36px;padding-inline:14px}.range-tabs button.active{box-shadow:0 3px 8px color-mix(in srgb,var(--dashboard-accent) 26%,transparent)}.date-filters select,.refresh{height:44px;min-height:44px}.date-filters select{padding-inline:12px 32px;box-shadow:0 3px 10px rgb(15 23 42/.04)}.refresh{padding-inline:14px;box-shadow:0 3px 10px rgb(15 23 42/.04)}.period-line{padding-inline:2px}.metric-strip{overflow:hidden;border:0;box-shadow:0 7px 22px rgb(15 23 42/.08)}.metric-strip>div{min-height:72px;padding:15px 20px}.metric-strip>div+div:before{top:16px;bottom:16px}.metric-strip span{font-weight:500}.metric-strip strong{margin-top:5px;font-size:1.85rem}.metric-strip small{margin-top:5px}.analytics-grid{grid-template-columns:minmax(0,1.55fr) minmax(390px,.85fr);grid-template-rows:minmax(0,1fr) minmax(210px,.72fr);gap:14px}.panel{border:0;box-shadow:0 7px 22px rgb(15 23 42/.07)}.panel>header{min-height:61px;padding:11px 17px;border-color:var(--dashboard-border-soft)}.panel h2{font-size:1.08rem;letter-spacing:-.015em}.panel header p{margin-top:3px;font-size:.72rem}.panel>header>strong{font-size:1.45rem}.trend-chart{position:relative;gap:12px;padding:24px 20px 12px;background-image:repeating-linear-gradient(to top,transparent 0,transparent calc(25% - 1px),color-mix(in srgb,var(--dashboard-border) 46%,transparent) 25%);background-size:100% 100%}.trend-column{grid-template-rows:20px minmax(80px,1fr) 22px}.bar-value{font-size:.72rem;font-weight:600}.bar-track{border-bottom-color:var(--dashboard-border-muted)}.bar-track i{width:min(46px,70%);border-radius:7px 7px 2px 2px;background:var(--dashboard-accent);box-shadow:0 5px 12px color-mix(in srgb,var(--dashboard-accent) 22%,transparent)}.trend-column:hover .bar-track i{background:var(--dashboard-accent-strong)}.trend-column small{padding-top:7px;font-size:.66rem}.ranking-list{padding:4px 16px 8px}.rank-row{grid-template-columns:28px minmax(0,1fr) 50px;gap:10px;padding:10px 0}.rank-row>b{width:24px;height:24px;border-radius:7px;font-size:.7rem}.rank-detail strong{max-width:52%;font-size:.82rem}.rank-detail span{font-size:.66rem}.rank-track{height:5px;margin-top:7px}.rank-track i{background:var(--dashboard-accent)}.rank-row>em{font-size:.7rem;font-weight:600}.view-all{padding:7px 4px;font-size:.72rem}.usage-outcome-panel>header{min-height:56px}.outcome-grid{gap:10px;padding:12px}.outcome-card{min-height:94px;padding:13px 14px;border:0;background:var(--dashboard-surface-muted)}.outcome-card.total{background:var(--dashboard-accent-soft)}.outcome-card.confirmed{background:var(--status-free-soft)}.outcome-card.cancelled{background:var(--status-busy-soft)}.outcome-card.no-show{background:var(--status-unknown-soft)}.outcome-card.pending{background:var(--status-pending-soft)}.outcome-card>span{font-size:.72rem;font-weight:500}.outcome-card>span i{width:8px;height:8px;flex-basis:8px}.outcome-card>strong{margin-top:9px;font-size:1.5rem}.outcome-card>small{margin-top:5px;font-size:.65rem}.room-ranking-panel .ranking-list{padding-bottom:10px}
@media(max-width:1350px){.analytics-grid{grid-template-columns:minmax(0,1.35fr) minmax(350px,.9fr)}.header-controls{flex-wrap:wrap;justify-content:flex-end}.outcome-grid{grid-template-columns:repeat(3,1fr)}.outcome-card.total{grid-row:span 2}.analytics-dashboard{height:auto}}
@media(max-width:760px){.page-header h1{font-size:1.8rem}.header-controls{padding-top:0}.date-filters select,.refresh{height:40px;min-height:40px}.metric-strip>div{min-height:78px;padding:14px}.analytics-grid{grid-template-columns:minmax(0,1fr);grid-template-rows:320px auto auto auto}.trend-chart{padding-inline:10px;gap:4px}.bar-track i{width:min(34px,70%)}.outcome-grid{grid-template-columns:repeat(2,1fr)}.outcome-card.total{grid-row:auto;grid-column:1/-1}}
@media(max-width:480px){
  .analytics-dashboard,.page-header,.page-header>div,.header-controls,.range-tabs,.date-filters,.metric-strip,.analytics-grid{min-width:0;max-width:100%}
  .page-header{min-height:0;gap:14px}
  .page-header h1{font-size:1.55rem;line-height:1.25;white-space:normal}
  .page-header p{font-size:.78rem;line-height:1.5}
  .header-controls{display:grid;grid-template-columns:minmax(0,1fr);gap:8px;width:100%}
  .range-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));width:100%;box-sizing:border-box}
  .range-tabs button{min-width:0;min-height:34px;padding-inline:4px;font-size:.68rem;white-space:nowrap}
  .date-filters{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));width:100%}
  .date-filters label,.date-filters select{min-width:0;width:100%}
  .date-filters .user-filter{grid-column:1/-1}
  .refresh{width:100%;justify-content:center}
  .period-line{align-items:flex-start;flex-direction:column;gap:3px}
  .metric-strip>div{min-width:0;padding:12px 10px}
  .metric-strip span{font-size:.72rem;line-height:1.35}
  .metric-strip strong{font-size:1.52rem}
  .metric-strip small{font-size:.61rem;line-height:1.35}
  .panel>header{gap:8px;padding-inline:12px}
  .panel h2{font-size:.96rem}
  .panel header p{font-size:.66rem;line-height:1.4}
  .ranking-list{padding-inline:12px}
  .rank-row{grid-template-columns:26px minmax(0,1fr) 44px;gap:7px}
  .rank-detail strong{max-width:55%;font-size:.75rem}
  .rank-detail span{font-size:.6rem}
  .outcome-grid{gap:7px;padding:9px}
  .outcome-card{min-height:86px;padding:11px}
}
</style>
