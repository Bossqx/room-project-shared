<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import config from "../assets/config.json"
import type { RoomBinding } from '../types/roomBinding'

const API_BASE = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

interface ScheduleInfo {
  id:           string
  subject_code: string
  room_code:    string
  weekday:      string
  start_time:   string
  finish_time:  string
  year_no:      string
  semester:     string
  date:         string
  user_login:   string
  isExist:boolean
}

const route        = useRoute()
const router       = useRouter()
const schedule     = ref<ScheduleInfo | null>(null)
const password     = ref('')
const loadError    = ref('')
const verifyState  = ref<'idle' | 'loading' | 'ok' | 'fail'>('idle')
const verifyMsg    = ref('')
const roomUsageId  = ref<number | null>(null)
const cancelState  = ref<'idle' | 'loading'>('idle')
const showCancel   = ref(false)



onMounted(async () => {
  const id = route.query.schedule_id as string ?? route.params.schedule_id as string
  if (!id) { loadError.value = 'No schedule_id provided.'; return }
  //showCancel.value = route.query.flag === '1'

  try {
    const res = await fetch(`${API_BASE}/schedule/schedule_decode/${encodeURIComponent(id)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    schedule.value = await res.json()
    if (schedule.value) detectAllowCancel(schedule.value)
  } catch (err) {
    loadError.value = `Failed to load schedule: ${err}`
  }
})

function detectAllowCancel(item: ScheduleInfo) {
  const now = new Date()
  const nowMinutes = now.getHours() * 60 + now.getMinutes()

  const toMin = (t: string) => { const [h, m] = t.split(':').map(Number); return h * 60 + m }
  const startMin  = toMin(item.start_time)
  const finishMin = toMin(item.finish_time)

  const isActive  = nowMinutes >= startMin && nowMinutes <= finishMin
  const pastGrace = nowMinutes > startMin + 15

  showCancel.value = isActive && pastGrace && item.isExist === false
}



async function controlDevice(roomNo: string) {
  try {
    const bindings: RoomBinding[] = await fetch(`${API_BASE}/room-binding/get_by_room/${encodeURIComponent(roomNo)}`).then(r => r.json())
    if (!Array.isArray(bindings) || !bindings.length) return
    await Promise.all(bindings.map(b =>
      fetch(`${API_BASE}/send_2_device/device/command`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host:    b.ip_address,
          room:    b.room_no,
          device:  b.devices,
          targets: [{ gpio_pin: b.pin, status: b.active_status }],
          qos:     1,
        }),
      })
    ))
  } catch { /* non-critical */ }
}

async function confirmStaffAccess(roomCode: string,subjectCode: string,userName: string,status: 'on' | 'off' = 'on') {
  try {
    await fetch(`${API_BASE}/send_2_device/staff_access/`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        room_no:      roomCode,
        status:       status,
        subject_code: subjectCode,
        user_name:    userName,
      }),
    })
  } catch { /* non-critical */ }
}


// async function confirmSend(roomCode: string,status: 'on' | 'off' = 'on') {
//   if (!schedule.value) return
//   try {
//     await fetch(`${API_BASE}/send_2_device/staff_access_test/${encodeURIComponent(roomCode)}?status=${status}`)
//   } catch { /* non-critical */ }
// }




async function addRoomUsage() {
  if (!schedule.value) return
  const s = schedule.value
  //const uuid = route.query.uuid as string
  const url=`${API_BASE}/room-usage/add`
  const payload=JSON.stringify({
      user_name:    s.user_login,
      room_no:      s.room_code,
      subject_code: s.subject_code,
      objective:"MIS Schedule",
      weekday:      Number(s.weekday),
      start_time:   s.start_time,
      finish_time:  s.finish_time,
      year_no:      s.year_no,
      semester:     s.semester,
      uuid: route.query.uuid,
      created_date: new Date().toISOString(),
    })
    //console.log(payload);
  const res = await fetch(url, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:payload,
  })
  const data = await res.json()
  if (data.id) roomUsageId.value = data.id
  await confirmStaffAccess(s.room_code,s.subject_code,s.user_login,"on")

}

async function cancelBooking() {
  cancelState.value = 'loading'
  if (roomUsageId.value !== null) {
    await fetch(`${API_BASE}/room-usage/delete/${roomUsageId.value}`, { method: 'DELETE' })
    roomUsageId.value = null
  }
  router.push('/')
}

async function sendCancelNotify() {
  await fetch(`${API_BASE}/send-mqtt/send_refresh_cancel/?status=cancel_schedule`)
}

async function verify() {
  if (!schedule.value || !password.value) return
  verifyState.value = 'loading'
  verifyMsg.value   = ''
  try {
    const params = new URLSearchParams({
      user_name: schedule.value.user_login,
      pwd:       password.value,
    })
    const res  = await fetch(`${API_BASE}/room-usage/verify_access?${params}`)
    const data = await res.json()
    if (data.access === true) {
      await addRoomUsage()
      await sendCancelNotify()
      await controlDevice(schedule.value.room_code)
      //await confirmOpenDoor(schedule.value.room_code)
      verifyState.value = 'ok'
      verifyMsg.value   = 'Access granted'
      await new Promise(resolve => setTimeout(resolve, 300))
      router.push("/home")
    } else {
      verifyState.value = 'fail'
      verifyMsg.value   = 'Incorrect password'
    }
  } catch (err) {
    verifyState.value = 'fail'
    verifyMsg.value   = `Error: ${err}`
  }
}
</script>

<template>
  <div class="page">

    <!-- Loading error -->
    <div v-if="loadError" class="error-box">{{ loadError }}</div>

    <!-- Loading -->
    <div v-else-if="!schedule" class="center-msg">Loading schedule…</div>

    <template v-else>
      <!-- Schedule info card -->
      <div class="card">
        <p class="card-title">Schedule Confirmation</p>

        <div class="info-grid">
          <span class="lbl">Subject</span>
          <span class="val mono">{{ schedule.subject_code }}</span>

          <span class="lbl">Room</span>
          <span class="val mono">{{ schedule.room_code }}</span>

          <span class="lbl">Time</span>
          <span class="val mono">{{ schedule.start_time }} – {{ schedule.finish_time }}</span>

          <span class="lbl">Date</span>
          <span class="val mono">{{ schedule.date }}</span>

          <span class="lbl">Semester</span>
          <span class="val mono">{{ schedule.year_no }} / {{ schedule.semester }}</span>

          <span class="lbl">Instructor</span>
          <span class="val mono">{{ schedule.user_login }}</span>
        </div>
      </div>

      <!-- Password verify card -->
      <div class="card">
        <p class="card-title">Verify Access</p>
        <p class="sub">Enter Pass Code for <strong>{{ schedule.user_login }}</strong></p>

        <div class="pwd-row">
          <input
            v-model="password"
            type="password"
            placeholder="Pass Code"
            class="pwd-input"
            @keyup.enter="verify"
            :disabled="verifyState === 'loading'"
          />
          <button
            class="btn"
            @click="verify"
            :disabled="!password || verifyState === 'loading'"
          >
            {{ verifyState === 'loading' ? 'Checking…' : 'Verify' }}
          </button>
        </div>

        <div v-if="verifyMsg" class="result" :class="verifyState">
          <span class="dot"></span>{{ verifyMsg }}
        </div>
      </div>

      <button
        v-if="showCancel"
        class="btn btn-cancel"
        @click="cancelBooking"
        :disabled="cancelState === 'loading'"
      >
        {{ verifyState === 'ok' ? 'New Booking' : 'New booking' }}
      </button>
    </template>

  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  color-scheme: dark;
  background: #0f172a;
  color: #f1f5f9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 1rem;
  gap: 1rem;
}

.card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 1rem;
  padding: 1.5rem;
  width: 100%;
  max-width: 480px;
}

.card-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin-bottom: 1rem;
}

.info-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.45rem 1rem;
  align-items: baseline;
}
.lbl  { font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; white-space: nowrap; }
.val  { font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }
.mono { font-family: monospace; }

.sub { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.9rem; }
.sub strong { color: #f1f5f9; }

.pwd-row {
  display: flex;
  gap: 0.6rem;
}
.pwd-input {
  flex: 1;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.5rem;
  color: #f1f5f9;
  font-size: 1rem;
  padding: 0.55rem 0.85rem;
  outline: none;
}
.pwd-input:focus { border-color: #3b82f6; }
.pwd-input:disabled { opacity: 0.5; }

.btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.55rem 1.1rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-cancel { background: transparent; border: 1px solid #ef4444; color: #ef4444; width: 100%; max-width: 480px; }

.result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.9rem;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
}
.result .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.result.ok   { background: #052e16; color: #4ade80; border: 1px solid #22c55e; }
.result.ok   .dot { background: #22c55e; }
.result.fail { background: #450a0a; color: #f87171; border: 1px solid #ef4444; }
.result.fail .dot { background: #ef4444; }
.error-box  { background: #450a0a; color: #f87171; border: 1px solid #ef4444; border-radius: 0.5rem; padding: 0.75rem 1rem; max-width: 480px; width: 100%; }
.center-msg { color: #64748b; }
</style>
