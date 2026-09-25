<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import config from "../assets/config.json"
import type { RoomBinding } from '../types/roomBinding'

const API_BASE = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

interface Room {
  room_no: string
}

const ACCESS_SECONDS = 60 * 60

const route          = useRoute()
const rooms          = ref<Room[]>([])
const roomNo         = ref((route.query.room as string) ?? '')
const pin            = ref('')
const verifyState    = ref<'idle' | 'loading' | 'ok' | 'fail'>('idle')
const verifyMsg      = ref('')
const deviceActive   = ref(false)
const countdown      = ref(0)
let bindings: RoomBinding[] = []
let countdownTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  try {
    const url=`${API_BASE}/room-usage/get_rooms`
    console.log(url);
    const res = await fetch(url)
    rooms.value = await res.json()
  } catch {
    // silent — dropdown just stays empty
  }
})

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})

function pad(n: number) {
  return n.toString().padStart(2, '0')
}

function formatDate(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function formatTime(d: Date) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function addStaffAccess() {
  const now    = new Date()
  const finish = new Date(now.getTime() + 60 * 60 * 1000)
  const res = await fetch(`${API_BASE}/staff_access/add`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_name:     'staff',
      room_no:       roomNo.value,
      created_date:  formatDate(now),
      start_time:    formatTime(now),
      finish_time:   formatTime(finish),
      status_active: 1,
    }),
  })
  return res.json()
}

// function formatCountdown(seconds: number) {
//   return `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`
// }

function stopCountdown() {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  countdown.value = 0
}

function startCountdown() {
  countdown.value = ACCESS_SECONDS
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) turnOff()
  }, 1000)
}

async function sendDeviceCommand(status: 'on' | 'off') {
  await Promise.all(bindings.map(b =>
    fetch(`${API_BASE}/send_2_device/device/command`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        host:    b.ip_address,
        room:    b.room_no,
        device:  b.devices,
        targets: [{ gpio_pin: b.pin, status }],
        qos:     1,
      }),
    })
  ))
}


async function confirmSend(roomCode: string,status: 'on' | 'off' = 'on') {
  // if (!schedule.value) return
  try {
    await fetch(`${API_BASE}/send_2_device/staff_access_get/${encodeURIComponent(roomCode)}?status=${status}`)
  } catch { /* non-critical */ }
}

async function notifyTogglePopup(roomCode: string, status: 'on' | 'off') {
  try {
    const url=`${API_BASE}/send_2_device/toggle_popup/${encodeURIComponent(roomCode)}?status=${status}`
    await fetch(url)
  } catch { /* non-critical */ }
}

async function opendoorHandler(room_no: string) {
  const res = await fetch(`${API_BASE}/room-binding/get_by_room/${encodeURIComponent(room_no)}`)
  bindings = await res.json()
  //console.log("Bindings: ", bindings)
  if (!Array.isArray(bindings) || !bindings.length) return
  await sendDeviceCommand('on')
  await notifyTogglePopup(room_no, 'on')
  deviceActive.value = true
  startCountdown()
}

async function setStatusOff() {
  if (!roomNo.value) return
  verifyState.value = 'loading'
  verifyMsg.value = ''
  try {
    const statusUrl = `${API_BASE}/staff_access/update_status/${encodeURIComponent(roomNo.value)}?status_active=0`
    // const deviceUrl = `${API_BASE}/send_2_device/staff_access_get/${encodeURIComponent(roomNo.value)}?status=off`

    const [statusRes] = await Promise.all([
      fetch(statusUrl, { method: 'GET' }),
      //fetch(deviceUrl, { method: 'GET' }),
      fetch(`${API_BASE}/send_2_device/submit_close/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_no: roomNo.value, status: 'off' }),
      }),
    ])
    if (!statusRes.ok) throw new Error(`HTTP ${statusRes.status}`)

    const bindingsRes = await fetch(`${API_BASE}/room-binding/get_by_room/${encodeURIComponent(roomNo.value)}`)
    bindings = await bindingsRes.json()
    if (Array.isArray(bindings) && bindings.length) await sendDeviceCommand('off')

    verifyState.value = 'ok'
    verifyMsg.value = 'ปิดห้องเรียบร้อยแล้ว'
  } catch (err) {
    verifyState.value = 'fail'
    verifyMsg.value = `Error: ${err}`
  }
}

async function turnOff() {
  if (!bindings.length) return
  await sendDeviceCommand('off')
  await setStatusOff();
  deviceActive.value = false
  stopCountdown()
  verifyMsg.value = 'ปิดห้องเรียบร้อยแล้ว'
  window.close()
}

const PIN_MAX_LENGTH = 6

function pressDigit(digit: string) {
  if (verifyState.value === 'loading') return
  if (pin.value.length >= PIN_MAX_LENGTH) return
  pin.value += digit
}

function backspacePin() {
  if (verifyState.value === 'loading') return
  pin.value = pin.value.slice(0, -1)
}

function clearPin() {
  if (verifyState.value === 'loading') return
  pin.value = ''
}

async function verify() {
  if (!roomNo.value || !pin.value) return
  verifyState.value = 'loading'
  verifyMsg.value   = ''
  try {
    const params = new URLSearchParams({ user_name: 'staff', pwd: pin.value })
    const res  = await fetch(`${API_BASE}/room-usage/verify_access?${params}`)
    const data = await res.json()
    if (data.access === true) {
      await addStaffAccess()
      await opendoorHandler(roomNo.value)
      await confirmSend(roomNo.value)
      verifyState.value = 'ok'
      verifyMsg.value   = 'ยืนยันเรียบร้อยแล้ว'
      pin.value = ''
    } else {
      verifyState.value = 'fail'
      verifyMsg.value   = 'รหัสผ่านไม่ถูกต้อง'
    }
  } catch (err) {
    verifyState.value = 'fail'
    verifyMsg.value   = `Error: ${err}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">เจ้าหน้าที่เข้าถึงห้อง</p>
      
      <p class="sub">ใส่รหัสพินเพื่อเข้าห้อง</p>

      <label class="field-label" for="room-select">ห้อง</label>
      <select
        id="room-select"
        v-model="roomNo"
        class="pwd-input room-input"
        :disabled="verifyState === 'loading'"
      >
        <option value="" disabled>เลือกห้อง</option>
        <option v-for="r in rooms" :key="r.room_no" :value="r.room_no">{{ r.room_no }}</option>
      </select>

      <div class="pin-display" role="status" aria-label="รหัสพินที่กรอก">
        <span
          v-for="i in PIN_MAX_LENGTH"
          :key="i"
          class="pin-dot"
          :class="{ filled: i <= pin.length }"
        ></span>
      </div>

      <div class="keypad">
        <button
          v-for="n in 9"
          :key="n"
          type="button"
          class="key"
          :disabled="verifyState === 'loading'"
          @click="pressDigit(String(n))"
        >{{ n }}</button>
        <button type="button" class="key key-aux" :disabled="verifyState === 'loading'" @click="clearPin">ล้าง</button>
        <button type="button" class="key" :disabled="verifyState === 'loading'" @click="pressDigit('0')">0</button>
        <button type="button" class="key key-aux" aria-label="ลบ" :disabled="verifyState === 'loading'" @click="backspacePin">⌫</button>
      </div>

      <button
        class="btn btn-confirm"
        @click="verify"
        :disabled="!roomNo || !pin || verifyState === 'loading'"
      >
        {{ verifyState === 'loading' ? 'ตรวจสอบ…' : 'ยืนยัน' }}
      </button>

      <div v-if="verifyMsg" class="result" :class="verifyState">
        <span class="dot"></span>{{ verifyMsg }}
      </div>
<!-- 
      <div v-if="deviceActive" class="device-row">
        <span class="countdown">{{ formatCountdown(countdown) }}</span>
        <button class="btn btn-off" @click="turnOff">ปิด ห้อง/อุปกรณ์</button>
      </div> -->
    </div>
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
  align-items: flex-start;
  justify-content: center;
  padding: 1rem;
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
  color: #94a3b8;
  margin-bottom: 1rem;
}

.sub { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.9rem; }
.sub strong { color: #f1f5f9; }

.field-label {
  display: block;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 0.3rem;
}

.room-input {
  width: 100%;
  margin-bottom: 0.6rem;
  appearance: none;
  cursor: pointer;
}

.pwd-input {
  width: 100%;
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

.pin-display {
  display: flex;
  justify-content: center;
  gap: 0.85rem;
  margin: 0.4rem 0 1.1rem;
}
.pin-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid #334155;
  background: transparent;
  transition: background .12s, border-color .12s;
}
.pin-dot.filled {
  background: #3b82f6;
  border-color: #3b82f6;
}

.keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
  margin-bottom: 1rem;
}
.key {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.6rem;
  color: #f1f5f9;
  font-size: 1.3rem;
  font-weight: 600;
  padding: 0.85rem 0;
  cursor: pointer;
  transition: background .12s, border-color .12s;
}
.key:hover:not(:disabled) { background: #263449; border-color: #475569; }
.key:active:not(:disabled) { background: #334155; }
.key:disabled { opacity: 0.4; cursor: not-allowed; }
.key-aux { font-size: 0.85rem; color: #94a3b8; }

.btn-confirm { width: 100%; }

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
.result.ok   { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; }
.result.ok   .dot { background: #22c55e; }
.result.fail { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444; }
.result.fail .dot { background: #ef4444; }

.device-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-top: 0.9rem;
  padding: 0.6rem 0.85rem;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.5rem;
}
.countdown { font-family: monospace; font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
.btn-off { background: #ef4444; }
</style>
