<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../../stores/user'
import { useSemesterStore } from '../../stores/semester'
import config from "../../assets/config.json"

const props = defineProps<{
  startTime?:   string
  finishTime?:  string
  roomCode?:    string
  bookingDate?: string
}>()

const emit = defineEmits<{ (e: 'booked'): void }>()

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

function getWeekday(): number {
  //console.log(form.value.booking_date);
  if (!form.value.booking_date) return 0
  const d = new Date(form.value.booking_date)
  return d.getDay() + 1 // Sun=1, Mon=2, … Sat=7
}

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
    //periods.value = Array.isArray(data) ? data : []
    periods.value = (Array.isArray(data) ? data : []).filter((p: Period) => p.period <= 13)

  } catch { /* ignore */ }

  if (!semesterStore.semester) {
    await semesterStore.fetchActiveSemester(apiBase)
  }

  const qRoomNo      = props.roomCode ?? (route.query.room_no as string | undefined)
  const qStartTime   = props.startTime  ?? (route.query.start_time as string | undefined)
  const qFinishTime  = props.finishTime ?? (route.query.finish_time as string | undefined)
  const qBookingDate = props.bookingDate ?? (route.query.booking_date as string | undefined)

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
  if (qBookingDate) {
    form.value.booking_date = qBookingDate
  }
})




async function sendBookingNotify() {
  await fetch(`${apiBase}/send-mqtt/send_refresh_booking/?status=booking_schedule`)
}

async function submit() {
  if (!userStore.isLoggedIn) {
    state.value = 'error'
    message.value = 'กรุณาเข้าสู่ระบบก่อนจองห้อง'
    return
  }
  if (!form.value.room_no || !form.value.subject_code || !form.value.start_time || !form.value.finish_time) return

  if (form.value.subject_code.length > 20) {
    state.value = 'error'
    message.value = 'Subject code must not exceed 20 characters'
    return
  }
  if (form.value.objective.length > 1000) {
    state.value = 'error'
    message.value = 'Objective must not exceed 1000 characters'
    return
  }

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
    const allowUrl = `${apiBase}/schedule/is_allow_booking/${form.value.room_no}?${allowParams.toString()}`
    //console.log('Checking schedule conflict:', allowUrl)
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
      weekday:      getWeekday(),
      start_time:   form.value.start_time,
      finish_time:  form.value.finish_time,
      year_no:      semesterStore.semester?.year_no  ?? '',
      semester:     semesterStore.semester?.semester ?? '',
      uuid:         crypto.randomUUID(),
      created_date: new Date().toISOString(),
      booking_date:form.value.booking_date
    }


   // console.log("Payload ",JSON.stringify(payload));

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
      form.value.objective    = ''
      form.value.start_time   = ''
      form.value.finish_time  = ''
      await sendBookingNotify()
      setTimeout(() => emit('booked'), 1200)
    }
  } catch (e) {
    state.value   = 'error'
    message.value = `ไม่สามารถจองห้องได้: ${e}`
  }
}
</script>

<template>
  <div class="page">
    <form class="card" @submit.prevent="submit">
      <header class="form-header">
        <span class="header-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3.5" y="5.5" width="17" height="15" rx="2.5" />
            <path stroke-linecap="round" d="M7.5 3.5v4M16.5 3.5v4M3.5 10h17M12 13.5v4M10 15.5h4" />
          </svg>
        </span>
        <div>
          <h2>จองห้อง</h2>
          <p>ระบุรายละเอียดและช่วงเวลาที่ต้องการใช้ห้อง</p>
        </div>
      </header>

      <div class="booking-meta">
        <div class="field">
          <label class="lbl" for="booking-room">ห้อง</label>
          <select id="booking-room" v-model="form.room_no" class="input" :disabled="!!props.roomCode">
            <option value="" disabled>เลือกห้อง</option>
            <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>

        <div class="field">
          <label class="lbl" for="booking-date">วันที่จอง</label>
          <input id="booking-date" v-model="form.booking_date" type="date" class="input" :placeholder="bookingDate" />
        </div>
      </div>

      <div class="field">
        <div class="label-row">
          <label class="lbl" for="booking-subject">รหัสวิชา / ชื่อวิชา</label>
          <span class="counter" :class="{ over: form.subject_code.length > 20 }">
            {{ form.subject_code.length }}/20
          </span>
        </div>
        <input
          id="booking-subject"
          v-model="form.subject_code"
          class="input"
          placeholder="เช่น 103101 หรือ การเขียนโปรแกรม"
          maxlength="20"
        />
      </div>

      <div class="field">
        <div class="label-row">
          <label class="lbl" for="booking-objective">วัตถุประสงค์</label>
          <span class="counter" :class="{ over: form.objective.length > 1000 }">
            {{ form.objective.length }}/1000
          </span>
        </div>
        <textarea
          id="booking-objective"
          v-model="form.objective"
          class="input textarea"
          placeholder="อธิบายวัตถุประสงค์การใช้ห้อง"
          rows="3"
          maxlength="1000"
        ></textarea>
      </div>

      <section class="time-section" aria-labelledby="time-section-title">
        <div class="section-heading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 7v5l3 2" />
          </svg>
          <span id="time-section-title">ช่วงเวลาใช้งาน</span>
        </div>
        <div class="time-row">
          <div class="field">
            <label class="lbl" for="booking-start">เริ่มต้น</label>
            <select id="booking-start" class="input" v-model="form.start_time">
              <option value="">เลือกเวลา</option>
              <option v-for="p in periods" :key="p.period" :value="p.startTime">
                คาบ {{ p.period }} — {{ p.startTime }}
              </option>
            </select>
          </div>
          <span class="time-arrow" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M15 8l4 4-4 4" />
            </svg>
          </span>
          <div class="field">
            <label class="lbl" for="booking-finish">สิ้นสุด</label>
            <select id="booking-finish" class="input" v-model="form.finish_time">
              <option value="">เลือกเวลา</option>
              <option v-for="p in periods" :key="p.period" :value="p.finishTime">
                คาบ {{ p.period }} — {{ p.finishTime }}
              </option>
            </select>
          </div>
        </div>
      </section>

      <div v-if="state === 'ok'" class="msg ok" role="status" aria-live="polite">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path stroke-linecap="round" stroke-linejoin="round" d="m8 12 2.5 2.5L16 9" />
        </svg>
        <span>{{ message }}</span>
      </div>
      <div v-else-if="state === 'error'" class="msg error" role="alert">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path stroke-linecap="round" d="M12 7v6M12 17h.01" />
        </svg>
        <span>{{ message }}</span>
      </div>
      <div v-else-if="state === 'conflict'" class="msg conflict" role="alert">
        <span class="msg-title">{{ message }}</span>
        <div v-for="c in conflicts" :key="c.id ?? c.start_time" class="conflict-row">
          <span class="conflict-time">{{ c.startTime ?? c.start_time }} – {{ c.finishTime ?? c.finish_time }}</span>
          <span v-if="c.coursecode" class="conflict-course">{{ c.coursecode }} {{ c.coursename }}</span>
          <span v-if="c.teacher?.[0]" class="conflict-teacher">
            {{ c.teacher[0].prefixname }}{{ c.teacher[0].officername }} {{ c.teacher[0].officersurname }}
          </span>
        </div>
      </div>

      <button
        class="btn"
        type="submit"
        :disabled="!form.room_no || !form.subject_code || !form.start_time || !form.finish_time || state === 'loading'"
      >
        <span v-if="state === 'loading'" class="spinner" aria-hidden="true"></span>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M13 6l6 6-6 6" />
        </svg>
        {{ state === 'loading' ? 'กำลังจอง…' : 'ยืนยันการจอง' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.page {
  width: 100%;
  background: transparent;
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.card {
  background: var(--bg-surface);
  border-radius: 1rem;
  padding: 1.65rem;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  box-shadow: var(--dashboard-shadow);
}

.form-header {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding-right: 2.4rem;
  margin-bottom: 0.15rem;
}

.header-icon {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex: 0 0 auto;
  border-radius: 0.8rem;
  background: var(--dashboard-accent-soft);
  color: var(--accent-link);
}
.header-icon svg { width: 1.4rem; height: 1.4rem; }
.form-header h2 { margin: 0; color: var(--text-primary); font-size: 1.25rem; font-weight: 750; letter-spacing: -0.015em; }
.form-header p { margin: 0.18rem 0 0; color: var(--text-secondary); font-size: 0.82rem; line-height: 1.45; }

.booking-meta {
  display: grid;
  grid-template-columns: 1fr 1.25fr;
  gap: 0.75rem;
  padding: 0.8rem;
  border: 1px solid color-mix(in srgb, var(--accent-link) 20%, var(--border));
  border-radius: 0.75rem;
  background: var(--dashboard-accent-soft);
}

.field { display: flex; flex-direction: column; gap: 0.4rem; min-width: 0; }
.label-row { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.lbl { color: var(--text-primary); font-size: 0.78rem; font-weight: 650; }
.counter { color: var(--text-muted); font-size: 0.68rem; font-variant-numeric: tabular-nums; }
.counter.over { color: var(--status-busy-text); font-weight: 700; }

.time-section {
  padding: 0.8rem;
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--bg-surface-alt) 58%, var(--bg-surface));
}
.section-heading { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.65rem; color: var(--text-secondary); font-size: 0.76rem; font-weight: 700; }
.section-heading svg { width: 1rem; height: 1rem; }
.time-row { display: flex; align-items: flex-end; gap: 0.55rem; }
.time-row .field { flex: 1; }
.time-arrow { display: grid; place-items: center; width: 1.5rem; height: 2.55rem; flex: 0 0 auto; color: var(--text-muted); }
.time-arrow svg { width: 1rem; height: 1rem; }

.input {
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 0.65rem;
  color: var(--text-primary);
  font: inherit;
  font-size: 0.9rem;
  padding: 0.68rem 0.78rem;
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
  color-scheme: inherit;
  width: 100%;
  box-sizing: border-box;
}
.input::placeholder { color: var(--text-muted); opacity: 0.82; }
.input:hover:not(:disabled) { border-color: color-mix(in srgb, var(--accent-link) 45%, var(--border)); }
.input:focus { border-color: var(--accent-link); background: var(--bg-surface); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-link) 16%, transparent); }
.input:disabled { opacity: 0.65; cursor: not-allowed; }
.input.textarea  { resize: vertical; min-height: 80px; line-height: 1.5; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
  border: none;
  border-radius: 0.65rem;
  padding: 0.75rem 1rem;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
}
.btn svg { width: 1rem; height: 1rem; }
.btn:hover:not(:disabled) { background: color-mix(in srgb, var(--brand-primary) 84%, #000); box-shadow: 0 5px 14px color-mix(in srgb, var(--brand-primary) 24%, transparent); }
.btn:active:not(:disabled) { transform: translateY(1px); }
.btn:focus-visible { outline: 3px solid color-mix(in srgb, var(--accent-link) 28%, transparent); outline-offset: 2px; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }

.spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid color-mix(in srgb, var(--brand-on-primary) 36%, transparent);
  border-top-color: var(--brand-on-primary);
  border-radius: 50%;
  animation: spin .65s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg { display: flex; align-items: center; gap: 0.5rem; padding: 0.62rem 0.75rem; border-radius: 0.6rem; font-size: 0.8rem; font-weight: 650; }
.msg > svg { width: 1rem; height: 1rem; flex: 0 0 auto; }
.msg.ok       { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid var(--status-free); }
.msg.error    { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid var(--status-busy); }
.msg.conflict { align-items: stretch; background: var(--pill-warning-bg); color: var(--pill-warning-text); border: 1px solid var(--status-pending); flex-direction: column; gap: 0.3rem; }
.msg-title    { font-weight: 600; }
.conflict-row { display: flex; flex-direction: column; gap: 0.1rem; padding: 0.35rem 0; border-top: 1px solid color-mix(in srgb, var(--status-pending) 24%, transparent); }
.conflict-time    { font-family: monospace; font-size: 0.8rem; font-weight: 700; }
.conflict-course  { font-size: 0.78rem; }
.conflict-teacher { font-size: 0.75rem; opacity: 0.75; }

@media (max-width: 560px) {
  .card { padding: 1.3rem; }
  .form-header { align-items: flex-start; padding-right: 2rem; }
  .booking-meta { grid-template-columns: 1fr; }
  .time-row { display: grid; grid-template-columns: 1fr; }
  .time-arrow { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .btn,
  .input { transition: none; }
  .spinner { animation-duration: 1.2s; }
}
</style>
