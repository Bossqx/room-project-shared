<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import config from "../assets/config.json"
import type { RoomBinding } from '../types/roomBinding'

interface Room {
  room_no: string
}

const API_BASE = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

const route     = useRoute()
const roomNo    = ref('')
const rowId     = (route.query.rowId as string) ?? ''
const objective = (route.query.objective as string) ?? ''
const state     = ref<'idle' | 'loading' | 'ok' | 'fail'>('idle')
const message   = ref('')
const rooms     = ref<Room[]>([])

async function setStatusOff() {
  if (!roomNo.value) return
  state.value = 'loading'
  message.value = ''
  try {
    const statusUrl = `${API_BASE}/staff_access/update_status/${encodeURIComponent(roomNo.value)}?status_active=0`
    const deviceUrl = `${API_BASE}/send_2_device/staff_access_get/${encodeURIComponent(roomNo.value)}?status=off`
    const submitUrl = objective === 'schedule'
      ? `${config.apiRoute}room-usage/set_status_schedules/${rowId}?usage_status=4`
      : `${config.apiRoute}room-usage/set_status_booking/${rowId}?usage_status=4`

    const [statusRes] = await Promise.all([
      fetch(statusUrl, { method: 'GET' }),
      fetch(deviceUrl, { method: 'GET' }),
      //close popup wait
      fetch(`${API_BASE}/send_2_device/submit_close/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_no: roomNo.value, status: 'off' }),
      }),
      ...(rowId ? [fetch(submitUrl)] : []),
    ])
    if (!statusRes.ok) throw new Error(`HTTP ${statusRes.status}`)

    const bindingsRes = await fetch(`${API_BASE}/room-binding/get_by_room/${encodeURIComponent(roomNo.value)}`)
    const bindings: RoomBinding[] = await bindingsRes.json()
    if (Array.isArray(bindings) && bindings.length) {
   
       sendDeviceCommand(bindings, 'off')
      // await notifyTogglePopup(roomNo.value, 'off')
    }

    await notifyTogglePopup(roomNo.value, 'off')

    state.value = 'ok'
    message.value = 'ปิดห้องเรียบร้อยแล้ว'
  } catch (err) {
    state.value = 'fail'
    message.value = `Error: ${err}`
  }
}

async function notifyTogglePopup(roomCode: string, status: 'on' | 'off') {
  try {
    await fetch(`${API_BASE}/send_2_device/toggle_popup/${encodeURIComponent(roomCode)}?status=${status}`)
  } catch { /* non-critical */ }
}

async function sendDeviceCommand(bindings: RoomBinding[], status: 'on' | 'off') {
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

onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/room-usage/get_rooms`)
    rooms.value = await res.json()
  } catch {
    // silent — dropdown just stays empty
  }

  roomNo.value = (route.query.room as string) ?? ''
  if (!roomNo.value) {
    state.value = 'fail'
    message.value = 'No room provided.'
  }
})
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">ปิดห้อง</p>
      <p class="sub">ห้อง <strong>{{ roomNo || '-' }}</strong></p>

      <button
        v-if="state !== 'ok'"
        class="btn"
        @click="setStatusOff"
        :disabled="!roomNo || state === 'loading'"
      >
        {{ state === 'loading' ? 'กำลังปิดห้อง…' : 'ปิดห้อง' }}
      </button>

      <p v-if="message" class="msg" :class="state">{{ message }}</p>
    </div>
  </div>
</template>

<style scoped>
:global(html),
:global(body) {
  background: #0f172a;
  margin: 0;
}

.page {
  width: 100%;
  min-height: 100vh;
  min-height: 100dvh;
  color-scheme: dark;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.card {
  background: #1e293b;
  min-height: 100vh;
  min-height: 100dvh;
  width: 100%;
  max-width: none;
  border: none;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem 1.5rem;
  text-align: center;
  box-sizing: border-box;
}

.card-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #94a3b8;
  margin-bottom: 1rem;
}

.sub { font-size: 0.85rem; font-weight: 600; color: #94a3b8; margin-bottom: 1rem; }
.sub strong { color: #f1f5f9; }

.btn {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.65rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  width: 150px;
  align-self: center;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.msg { margin-top: 1rem; font-size: 1rem; font-weight: 600; }
.msg.ok   { color: #4ade80; }
.msg.fail { color: #f87171; }

@media (max-width: 600px) {
  .card-title { font-size: 1rem; margin-bottom: 1.5rem; }
  .sub { font-size: 1.2rem; margin-bottom: 1.5rem; }
  .btn { padding: 1.1rem 1.5rem; font-size: 1.3rem; }
  .msg { font-size: 1.2rem; }
}
</style>
