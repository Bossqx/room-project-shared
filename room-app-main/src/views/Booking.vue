<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useSemesterStore } from '../stores/semester'
import config from "../assets/config.json"

const router         = useRouter()
const route          = useRoute()
const userStore     = useUserStore()
const semesterStore = useSemesterStore()
const apiBase = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

interface Period {
  period:     number
  startTime:  string
  finishTime: string
}

const rooms   = ref<string[]>([])
const periods = ref<Period[]>([])

const form = ref({
  room_no:      '',
  subject_code: '',
  objective:'',
  booking_date: new Date().toISOString().slice(0, 10),
  start_time:   '',
  finish_time:  '',
})

const bookingDate = ref(new Date().toISOString().slice(0, 10))

const state   = ref<'idle' | 'loading' | 'ok' | 'conflict' | 'error'>('idle')
const message = ref('')
const conflicts = ref<any[]>([])

const weekday = computed(() => {
  if (!bookingDate.value) return 0
  const d = new Date(bookingDate.value)
  return d.getDay() === 0 ? 7 : d.getDay() // ISO: Mon=1 … Sun=7
})

function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function nearestPeriodBy(key: 'startTime' | 'finishTime', target: string): Period | null {
  if (!periods.value.length) return null
  const targetMin = toMinutes(target)
  return periods.value.reduce((best, p) =>
    Math.abs(toMinutes(p[key]) - targetMin) < Math.abs(toMinutes(best[key]) - targetMin) ? p : best
  )
}

onMounted(async () => {
  try {
    const res  = await fetch(`${apiBase}/room-usage/get_rooms`)
    const data = await res.json()
    rooms.value = (Array.isArray(data) ? data : []).map((r: { room_no: string }) => r.room_no)
    if (rooms.value.length) form.value.room_no = rooms.value[0]
  } catch { /* ignore */ }

  try {
    const res  = await fetch(`${apiBase}/room-usage/get_periods`)
    const data = await res.json()
    periods.value = (Array.isArray(data) ? data : []).filter((p: Period) => p.period <= 13)
  } catch { /* ignore */ }

  if (!semesterStore.semester) {
    await semesterStore.fetchActiveSemester(apiBase)
  }

  const qRoomNo     = route.query.room_no as string | undefined
  const qStartTime  = route.query.start_time as string | undefined
  const qFinishTime = route.query.finish_time as string | undefined

  if (qRoomNo && rooms.value.includes(qRoomNo)) {
    form.value.room_no = qRoomNo
  }
  if (qStartTime) {
    const nearest = nearestPeriodBy('startTime', qStartTime)
    if (nearest) form.value.start_time = nearest.startTime
  }
  if (qFinishTime) {
    const nearest = nearestPeriodBy('finishTime', qFinishTime)
    if (nearest) form.value.finish_time = nearest.finishTime
  }
})

async function sendBookingNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_booking/?status=booking_schedule`)
}

async function submit() {
  if (!form.value.room_no || !form.value.subject_code || !form.value.start_time || !form.value.finish_time) return
  state.value     = 'loading'
  message.value   = ''
  conflicts.value = []

  try {
    // ── Step 1: check schedule conflict ──────────────────────────────
    const allowParams = new URLSearchParams({
      booking_date: form.value.booking_date,
      start_time:  form.value.start_time,
      finish_time: form.value.finish_time,
    })
    const allowUrl = `${apiBase}/room-usage/is_allow_booking/${form.value.room_no}?${allowParams.toString()}`
    console.log('Checking schedule conflict:', allowUrl)
    const allowRes  = await fetch(allowUrl)
    const allowData = await allowRes.json()

    if (!allowData.isAllow) {
      state.value     = 'conflict'
      message.value   = 'This time slot conflicts with an existing schedule'
      conflicts.value = allowData.conflicts ?? []
      return
    }

    // ── Step 2: submit booking ────────────────────────────────────────
    const payload = {
      user_name:    userStore.userName,
      room_no:      form.value.room_no,
      subject_code: form.value.subject_code,
      objective:form.value.objective, 
      weekday:      weekday.value,
      start_time:   form.value.start_time,
      finish_time:  form.value.finish_time,
      year_no:      semesterStore.semester?.year_no  ?? '',
      semester:     semesterStore.semester?.semester ?? '',
      uuid:         crypto.randomUUID(),
      created_date: new Date().toISOString(),
      booking_date:form.value.booking_date
    }

    console.log(payload)

    const res  = await fetch(`${apiBase}/room-usage/add`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    })
    const data = await res.json()

    if (data?.error) {
      state.value     = 'conflict'
      message.value   = data.error
      conflicts.value = data.conflicts ?? []
    } else if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    } else {
      state.value   = 'ok'
      message.value = 'จองห้องสำเร็จ'
      form.value.subject_code = ''
      form.value.start_time   = ''
      form.value.finish_time  = ''
      await sendBookingNotify()
    }
  } catch (e) {
    state.value   = 'error'
    message.value = `ไม่สามารถจองห้องได้: ${e}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <p class="card-title">จองห้อง</p>
        <div class="header-actions">
          <button type="button" class="btn-empty-check" @click="router.push('/mobile/empty-rooms')">
            Check Empty Rooms
          </button>
          <input v-model="bookingDate" type="date" class="date-picker" />
        </div>
      </div>

      <!-- Room -->
      <div class="field">
        <label class="lbl">ห้อง</label>
        <select v-model="form.room_no" class="input">
          <option value="" disabled>เลือกห้อง</option>
          <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
        </select>
      </div>

      <!-- Date -->
          <div class="field">
        <label class="lbl">วันที่จอง</label>
         <input v-model="form.booking_date" type="date" class="input" :placeholder="bookingDate"
               @keyup.enter="submit" />
      </div>


      <!-- Subject code -->
      <div class="field">
        <label class="lbl">รหัสวิชา / ชื่อวิชา</label>
        <input v-model="form.subject_code" class="input" placeholder="กรอกรหัสวิชาหรือชื่อวิชา"
               @keyup.enter="submit" />
      </div>

      <!-- Objective -->
      <div class="field">
        <label class="lbl">วัตถุประสงค์</label>
        <textarea v-model="form.objective" class="input textarea" placeholder="กรอกวัตถุประสงค์" rows="3"></textarea>
      </div>

      <!-- Time -->
      <div class="time-row">
        <div class="field">
          <label class="lbl">เวลาเริ่มต้น</label>
          <select class="input" v-model="form.start_time">
            <option value="">— เลือกคาบ —</option>
            <option v-for="p in periods" :key="p.period" :value="p.startTime">
              คาบ {{ p.period }} — {{ p.startTime }}
            </option>
          </select>
        </div>
        <div class="field">
          <label class="lbl">เวลาสิ้นสุด</label>
          <select class="input" v-model="form.finish_time">
            <option value="">— เลือกคาบ —</option>
            <option v-for="p in periods" :key="p.period" :value="p.finishTime">
              คาบ {{ p.period }} — {{ p.finishTime }}
            </option>
          </select>
        </div>
      </div>

      <!-- User (read-only) -->

      <!-- Feedback -->
      <div v-if="state === 'ok'" class="msg ok">{{ message }}</div>
      <div v-else-if="state === 'error'" class="msg error">{{ message }}</div>
      <div v-else-if="state === 'conflict'" class="msg conflict">
        <span class="msg-title">{{ message }}</span>
        <div v-for="c in conflicts" :key="c.id ?? c.start_time" class="conflict-row">
          <span class="conflict-time">{{ c.startTime ?? c.start_time }} – {{ c.finishTime ?? c.finish_time }}</span>
          <span v-if="c.coursecode" class="conflict-course">{{ c.coursecode }} {{ c.coursename }}</span>
          <span v-if="c.teacher?.[0]" class="conflict-teacher">
            {{ c.teacher[0].prefixname }}{{ c.teacher[0].officername }} {{ c.teacher[0].officersurname }}
          </span>
        </div>
      </div>

      <button class="btn" @click="submit"
              :disabled="!form.room_no || !form.subject_code || !form.start_time || !form.finish_time || state === 'loading'">
        <span v-if="state === 'loading'" class="spinner"></span>
        {{ state === 'loading' ? 'กำลังจอง…' : 'จองห้อง' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1.25rem 0.75rem;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-header  { display: flex; align-items: baseline; justify-content: space-between; }
.header-actions { display: flex; align-items: center; gap: 0.6rem; }

.btn-empty-check {
  background: rgba(59,130,246,.1);
  border: 1px solid #3b82f6;
  color: var(--accent-link);
  border-radius: 0.4rem;
  padding: 0.3rem 0.6rem;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s;
}
.btn-empty-check:hover { background: rgba(59,130,246,.2); }

.date-picker {
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-family: monospace;
  outline: none;
  color-scheme: light;
  cursor: pointer;
}

.card-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin: 0;
}

.field { display: flex; flex-direction: column; gap: 0.35rem; }
.lbl   { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }

.time-row { display: flex; gap: 0.75rem; }
.time-row .field { flex: 1; }

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
  width: 100%;
  box-sizing: border-box;
}
.input:focus   { border-color: #3b82f6; }
.input.readonly  { opacity: 0.5; cursor: not-allowed; }
.input.textarea  { resize: vertical; min-height: 80px; line-height: 1.5; }

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.65rem 1rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 0.25rem;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg { padding: 0.55rem 0.75rem; border-radius: 0.5rem; font-size: 0.875rem; }
.msg.ok       { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e; }
.msg.error    { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }
.msg.conflict { background: var(--pill-warning-bg); color: var(--pill-warning-text); border: 1px solid #f97316;
                display: flex; flex-direction: column; gap: 0.3rem; }
.msg-title    { font-weight: 600; }
.conflict-row { display: flex; flex-direction: column; gap: 0.1rem; padding: 0.35rem 0; border-top: 1px solid rgba(249,115,22,.2); }
.conflict-time    { font-family: monospace; font-size: 0.8rem; font-weight: 700; }
.conflict-course  { font-size: 0.78rem; }
.conflict-teacher { font-size: 0.75rem; opacity: 0.75; }
</style>
