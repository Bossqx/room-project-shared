<script setup lang="ts">
import { ref, computed } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

interface Summary {
  total_bookings: number
  days_used: number
  distinct_teachers: number
  distinct_courses: number
}
interface Occupancy {
  slots_booked: number
  slots_available: number
  occupancy_pct: number
}
interface TeacherRow { teacher: string; sessions: number }
interface CourseRow { coursecode: string; coursename: string; sessions: number }
interface GridRow {
  weekday: number
  period_from: number
  period_to: number
  coursecode: string
  teacher: string
}

const form = ref({
  room_no: '27.03.05',
  date_from: new Date().toISOString().slice(0, 10),
  date_to: new Date().toISOString().slice(0, 10),
})

const summary   = ref<Summary | null>(null)
const occupancy = ref<Occupancy | null>(null)
const teachers  = ref<TeacherRow[]>([])
const courses   = ref<CourseRow[]>([])
const grid      = ref<GridRow[]>([])

const loadState = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const errMsg     = ref('')

const weekdayLabels = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const gridPeriods = computed(() => {
  const periods = new Set<number>()
  grid.value.forEach(row => periods.add(row.period_from))
  return Array.from(periods).sort((a, b) => a - b)
})

function gridCell(period: number, weekday: number) {
  return grid.value.find(row => row.period_from === period && row.weekday === weekday)
}

const maxTeacherSessions = computed(() => Math.max(1, ...teachers.value.map(t => t.sessions)))
const maxCourseSessions  = computed(() => Math.max(1, ...courses.value.map(c => c.sessions)))

async function loadDashboard() {
  if (!form.value.room_no || !form.value.date_from || !form.value.date_to) return
  loadState.value = 'loading'
  errMsg.value    = ''
  try {
    const params = new URLSearchParams({
      room_no:   form.value.room_no,
      date_from: form.value.date_from,
      date_to:   form.value.date_to,
    })
    const [summaryRes, occupancyRes, teachersRes, coursesRes, gridRes] = await Promise.all([
      fetch(`${apiBase}/dashboard/summary/?${params}`),
      fetch(`${apiBase}/dashboard/occupancy/?${params}`),
      fetch(`${apiBase}/dashboard/top_teachers/?${params}&limit=5`),
      fetch(`${apiBase}/dashboard/top_courses/?${params}&limit=5`),
      fetch(`${apiBase}/dashboard/weekly_grid/?${params}`),
    ])
    for (const res of [summaryRes, occupancyRes, teachersRes, coursesRes, gridRes]) {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
    }
    summary.value   = await summaryRes.json()
    occupancy.value = await occupancyRes.json()
    teachers.value  = await teachersRes.json()
    courses.value   = await coursesRes.json()
    grid.value      = await gridRes.json()
    loadState.value = 'done'
  } catch (e) {
    loadState.value = 'error'
    errMsg.value    = `Failed to load dashboard: ${e}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">Room Usage Dashboard</p>
      <p class="hint">Aggregated booking stats for a room within a date range.</p>

      <form class="form" @submit.prevent="loadDashboard">
        <div class="field">
          <label class="lbl">Room Code</label>
          <input v-model="form.room_no" type="text" class="input" required />
        </div>

        <div class="field">
          <label class="lbl">Date From</label>
          <input v-model="form.date_from" type="date" class="input" required />
        </div>

        <div class="field">
          <label class="lbl">Date To</label>
          <input v-model="form.date_to" type="date" class="input" required />
        </div>

        <button class="btn" type="submit" :disabled="loadState === 'loading'">
          <span v-if="loadState === 'loading'" class="spinner"></span>
          {{ loadState === 'loading' ? 'Loading…' : 'Load Dashboard' }}
        </button>
      </form>

      <div v-if="loadState === 'error'" class="msg error-box">{{ errMsg }}</div>
    </div>

    <template v-if="loadState === 'done'">
      <!-- KPI row -->
      <div class="kpi-row">
        <div class="kpi-tile">
          <p class="kpi-value">{{ summary?.total_bookings ?? 0 }}</p>
          <p class="kpi-label">Total Bookings</p>
        </div>
        <div class="kpi-tile">
          <p class="kpi-value">{{ summary?.days_used ?? 0 }}</p>
          <p class="kpi-label">Days Used</p>
        </div>
        <div class="kpi-tile">
          <p class="kpi-value">{{ summary?.distinct_teachers ?? 0 }}</p>
          <p class="kpi-label">Distinct Teachers</p>
        </div>
        <div class="kpi-tile">
          <p class="kpi-value">{{ summary?.distinct_courses ?? 0 }}</p>
          <p class="kpi-label">Distinct Courses</p>
        </div>
      </div>

      <!-- Occupancy meter -->
      <div class="card">
        <p class="card-title">Occupancy</p>
        <div class="meter-row">
          <div class="meter-track">
            <div class="meter-fill" :style="{ width: `${Math.min(100, occupancy?.occupancy_pct ?? 0)}%` }"></div>
          </div>
          <span class="meter-value">{{ occupancy?.occupancy_pct ?? 0 }}%</span>
        </div>
        <p class="hint">
          {{ occupancy?.slots_booked ?? 0 }} of {{ occupancy?.slots_available ?? 0 }} period-slots booked
        </p>
      </div>

      <!-- Top teachers / top courses -->
      <div class="split-row">
        <div class="card">
          <p class="card-title">Top Teachers</p>
          <div v-if="teachers.length === 0" class="empty">No data.</div>
          <div v-else class="bar-list">
            <div v-for="t in teachers" :key="t.teacher" class="bar-row">
              <span class="bar-label">{{ t.teacher }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${(t.sessions / maxTeacherSessions) * 100}%` }"></div>
              </div>
              <span class="bar-value">{{ t.sessions }}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <p class="card-title">Top Courses</p>
          <div v-if="courses.length === 0" class="empty">No data.</div>
          <div v-else class="bar-list">
            <div v-for="c in courses" :key="c.coursecode" class="bar-row">
              <span class="bar-label">
                {{ c.coursecode }}
                <span class="bar-sublabel">{{ c.coursename }}</span>
              </span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${(c.sessions / maxCourseSessions) * 100}%` }"></div>
              </div>
              <span class="bar-value">{{ c.sessions }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Weekly grid -->
      <div class="card">
        <p class="card-title">Weekly Grid</p>
        <div v-if="grid.length === 0" class="empty">No bookings in this range.</div>
        <div v-else class="grid-scroll">
          <table class="grid-table">
            <thead>
              <tr>
                <th>Period</th>
                <th v-for="d in 7" :key="d">{{ weekdayLabels[d] }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="period in gridPeriods" :key="period">
                <td class="period-cell">{{ period }}</td>
                <td v-for="d in 7" :key="d" class="grid-cell" :class="{ occupied: gridCell(period, d) }">
                  <template v-if="gridCell(period, d)">
                    <div class="grid-course">{{ gridCell(period, d)?.coursecode }}</div>
                    <div class="grid-teacher">{{ gridCell(period, d)?.teacher }}</div>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
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
  margin: 0.5rem 0 0;
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

.empty {
  text-align: center;
  color: #64748b;
  padding: 1.25rem 0.6rem;
  font-size: 0.85rem;
}

/* ── KPI row ── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
}

.kpi-tile {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.1rem 1.25rem;
  box-sizing: border-box;
}

.kpi-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.2rem;
  line-height: 1.1;
}

.kpi-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin: 0;
}

/* ── Occupancy meter ── */
.meter-row {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.meter-track {
  flex: 1;
  height: 12px;
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 999px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 999px;
  transition: width .2s;
}

.meter-value {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--accent-link-hover);
  min-width: 3.2rem;
  text-align: right;
}

/* ── Top teachers / courses ── */
.split-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
}
.split-row .card { width: 100%; margin: 0; }

.bar-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(90px, 1fr) minmax(80px, 2fr) 2rem;
  align-items: center;
  gap: 0.6rem;
}

.bar-label {
  font-size: 0.82rem;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-sublabel {
  display: block;
  font-size: 0.7rem;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-track {
  height: 8px;
  background: var(--bg-page);
  border: 1px solid #273549;
  border-radius: 999px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 999px;
}

.bar-value {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--accent-link-hover);
  text-align: right;
}

/* ── Weekly grid ── */
.grid-scroll {
  overflow-x: auto;
}

.grid-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.grid-table th {
  text-align: center;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
  padding: 0.5rem 0.4rem;
  border-bottom: 1px solid var(--border);
}

.grid-table td {
  padding: 0.45rem 0.4rem;
  border-bottom: 1px solid #273549;
  border-left: 1px solid #273549;
  text-align: center;
  vertical-align: top;
  min-width: 88px;
}

.period-cell {
  color: #64748b;
  font-weight: 600;
  text-align: center;
}

.grid-cell.occupied {
  background: rgba(59,130,246,.12);
}

.grid-course {
  font-weight: 600;
  color: var(--accent-link-hover);
}

.grid-teacher {
  font-size: 0.7rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
