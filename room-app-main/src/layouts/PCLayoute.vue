<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import config from "../assets/config.json"
import Booking from '../views/components/BookingDesktop.vue'
import ChangePinDesktop from '../views/components/ChangePinDesktop.vue'
import ThemeToggle from '../views/components/ThemeToggle.vue'
import LanguageToggle from '../views/components/LanguageToggle.vue'

const logo = '/icons/icon-192.svg'

const router    = useRouter()
const route     = useRoute()
const userStore = useUserStore()
const apiBase   = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

const mqttHost   = ref('–')
const mqttStatus = ref<'connecting' | 'connected' | 'disconnected'>('connecting')

let pollTimer: ReturnType<typeof setInterval> | null = null

async function checkMqttStatus() {
  try {
    const res  = await fetch(`${apiBase}/send-mqtt/status`)
    const data = await res.json()
    mqttHost.value   = `${data.broker}:${data.port}`
    mqttStatus.value = data.status === 'ok' ? 'connected' : 'disconnected'
  } catch {
    mqttStatus.value = 'disconnected'
  }
}

const bookingStartTime  = ref('')
const bookingFinishTime = ref('')
const bookingRoomCode   = ref('')
const bookingDate       = ref('')

function showBooking(startTime?: string, finishTime?: string, roomCode?: string, bookingDateStr?: string){
  bookingStartTime.value  = startTime  ?? ''
  bookingFinishTime.value = finishTime ?? ''
  bookingRoomCode.value   = roomCode   ?? ''
  bookingDate.value       = bookingDateStr ?? ''
  showBookingModal.value  = true
}

provide('showBooking', showBooking)

onMounted(async () => {
  if (!userStore.userName) {
    userStore.clearUser()
    router.replace('/login')
    return
  }

  await checkMqttStatus()
  pollTimer = setInterval(checkMqttStatus, 30_000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const showBookingModal = ref(false)
const showChangePinModal = ref(false)

function isActive(name: string) {
  if (name === 'pc-booking') return showBookingModal.value
  if (name === 'pc-change-pin') return showChangePinModal.value
  return route.name === name
}

function logout() {
  userStore.clearUser()
  router.push('/')
}

const menuItems = [
  {
    name: 'pc-home',
    label: 'หน้าหลัก',
    path: '/desktop/overview',
    icon: 'm2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
  },

  {
    name: 'pc-schedule',
    label: 'ตารางการจอง',
    path: '/desktop/schedule',
    icon: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-13.5 3h.008v.008H7.5v-.008ZM7.5 15h.008v.008H7.5V15Zm0-3h.008v.008H7.5V12Zm3 3h.008v.008h-.008V15Zm0-3h.008v.008h-.008V12Zm3 3h.008v.008h-.008V15Zm0-3h.008v.008h-.008V12Zm3 3h.008v.008h-.008V15Zm0-3h.008v.008h-.008V12Z',
  },

  {
    name: 'pc-booking',
    label: 'จองห้อง',
    path: '//booking',
    icon: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5',
  },


  {
    name: 'pc-change-pin',
    label: 'จัดการรหัสพิน',
    path: '/desktop/change-pin',
    icon: 'M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z',
  },
]

function go(item: typeof menuItems[number]) {
  if (item.name === 'pc-booking') {
    //showBookingModal.value = true
    showBooking()
  } else if (item.name === 'pc-change-pin') {
    showChangePinModal.value = true
  } else {
    router.push(item.path)
  }
}

defineExpose({ showBooking })
</script>

<template>
  <div class="pc-layout">
    <!-- Top menu -->
    <header class="topbar">
      <div class="brand">
        <img :src="logo" alt="Logo" class="brand-logo" />
        <span class="brand-title">ระบบบริหารจัดการห้องคอมพิวเตอร์สำนักคอมพิวเตอร์</span>
      </div>

      <nav class="menu">
        <button
          v-for="item in menuItems"
          :key="item.name"
          class="menu-item"
          :class="{ active: isActive(item.name) }"
          @click="go(item)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <LanguageToggle />
      <ThemeToggle />

      <button class="menu-item logout" @click="logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
        </svg>
        <span>ออกจากระบบ</span>
      </button>
    </header>

    <!-- Container -->
    <main class="container" :class="{ 'container--flush': route.path === '/desktop/overview' }">
      <RouterView />
    </main>

    <!-- Booking popup -->
    <Teleport to="body">
      <div v-if="showBookingModal" class="booking-overlay" @click.self="showBookingModal = false">
        <div class="booking-modal booking-modal--reservation">
          <button class="booking-close" aria-label="ปิดหน้าต่างจองห้อง" @click="showBookingModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <Booking
            :start-time="bookingStartTime"
            :finish-time="bookingFinishTime"
            :room-code="bookingRoomCode"
            :booking-date="bookingDate"
            @booked="showBookingModal = false"
          />
        </div>
      </div>
    </Teleport>

    <!-- Change PIN popup -->
    <Teleport to="body">
      <div v-if="showChangePinModal" class="booking-overlay" @click.self="showChangePinModal = false">
        <div class="booking-modal booking-modal--pin">
          <button class="booking-close" aria-label="ปิดหน้าต่างเปลี่ยนรหัสพิน" @click="showChangePinModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <ChangePinDesktop />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.pc-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ── Top menu ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  flex-shrink: 0;
  width: 100%;
  box-sizing: border-box;
  background: var(--brand-primary);
  border-radius: 0 0 0.6rem 0.6rem;
  /* border-bottom: 1px solid #cbd5e1; */
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.6rem 1.5rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}

.brand-logo {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.brand-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--brand-on-primary);
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.menu {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
}

.menu-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: none;
  border-radius: 999px;
  color: var(--brand-on-primary);
  font-family: 'Kanit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  padding: 0.5rem 0.85rem;
  cursor: pointer;
  white-space: nowrap;
  transition: color .15s, background .15s;
}

.menu > .menu-item:not(:last-child)::after {
  content: '|';
  position: absolute;
  right: -0.15rem;
  color: color-mix(in srgb, var(--brand-on-primary) 35%, transparent);
  pointer-events: none;
}

.menu-item svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.menu-item:hover {
  background: var(--brand-control-bg);
  color: var(--brand-on-primary);
}

.menu-item.active {
  background: var(--brand-control-bg-hover);
  color: var(--brand-on-primary);
  font-weight: 700;
}

.menu-item.logout {
  flex-shrink: 0;
  color: color-mix(in srgb, var(--brand-on-primary) 85%, transparent);
}
.menu-item.logout:hover {
  background: var(--status-busy);
  color: var(--brand-on-primary);
}

/* ── Container ── */
.container {
  flex: 1;
  min-width: 0;
  padding: 2.5rem 2rem 1.5rem;
  overflow-y: auto;
}

.container--flush {
  padding: 0;
}

/* ── MQTT badge ── */
.mqtt-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--brand-control-border);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.62rem;
  color: var(--brand-on-primary);
  width: fit-content;
}

.mqtt-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #cbd5e1;
}

.mqtt-badge.connected    .mqtt-dot { background: var(--status-free); box-shadow: 0 0 5px color-mix(in srgb, var(--status-free) 55%, transparent); }
.mqtt-badge.connecting   .mqtt-dot { background: var(--status-pending); }
.mqtt-badge.disconnected .mqtt-dot { background: var(--status-busy); }

.mqtt-host { font-family: monospace; letter-spacing: 0.02em; }

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

.booking-modal--reservation {
  max-width: 540px;
}

.booking-modal--pin {
  max-width: 460px;
}

.booking-modal--reservation,
.booking-modal--pin {
  overflow: visible;
}

.booking-modal--reservation .booking-close,
.booking-modal--pin .booking-close {
  top: 1rem;
  right: 1rem;
  background: transparent;
  border-color: var(--border);
  color: var(--text-secondary);
}

.booking-modal--reservation .booking-close:hover,
.booking-modal--pin .booking-close:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
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
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  color: #f1f5f9;
  cursor: pointer;
  z-index: 1;
}
.booking-close svg { width: 16px; height: 16px; }
.booking-close:hover { background: #334155; }
</style>
