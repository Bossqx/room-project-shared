<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import config from "../assets/config.json"
import ThemeToggle from '../views/components/ThemeToggle.vue'
import LanguageToggle from '../views/components/LanguageToggle.vue'
import BookingDesktop from '../views/components/BookingDesktop.vue'

const logo = '/icons/icon-192.svg'

const router    = useRouter()
const route     = useRoute()
const userStore = useUserStore()
const apiBase   = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

const mqttHost   = ref('–')
const mqttStatus = ref<'connecting' | 'connected' | 'disconnected'>('connecting')
const showBookingModal = ref(false)
const bookingStartTime = ref('')
const bookingFinishTime = ref('')
const bookingRoomCode = ref('')
const bookingDate = ref('')

function showBooking(startTime?: string, finishTime?: string, roomCode?: string, bookingDateStr?: string) {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  bookingStartTime.value = startTime ?? ''
  bookingFinishTime.value = finishTime ?? ''
  bookingRoomCode.value = roomCode ?? ''
  bookingDate.value = bookingDateStr ?? ''
  showBookingModal.value = true
}

provide('showBooking', showBooking)

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

function isActive(name: string) {
  return route.name === name
}

function logout() {
  userStore.clearUser()
  router.push('/login')
}
</script>

<template>
  <div class="layout">

    <!-- Top header bar -->
    <header class="top-bar">
      <div class="top-brand">
        <img :src="logo" alt="ตราสัญลักษณ์ระบบ" class="top-logo" />
        <span class="top-title">ระบบจองห้องคอมพิวเตอร์</span>
      </div>
      <div class="top-right">
        <!-- <div class="mqtt-badge" :class="mqttStatus">
          <span class="mqtt-dot"></span>
          <span class="mqtt-host">{{ mqttHost }}</span>
        </div> -->
        <LanguageToggle />
        <ThemeToggle />
        <button class="logout-btn" @click="logout" aria-label="ออกจากระบบ">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Page content -->
    <main class="content">
      <RouterView />
    </main>

    <!-- Bottom nav -->
    <nav class="bottom-nav">
      <button class="nav-item" :class="{ active: isActive('/mobile/home') }" @click="router.push('/mobile/home')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
        </svg>
        <span>หน้าหลัก</span>
      </button>

      <button class="nav-item" :class="{ active: isActive('/mobile/booking') }" @click="router.push('/mobile/booking')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
        </svg>
        <span>จองห้อง</span>
      </button>

      <button class="nav-item" :class="{ active: isActive('/mobile/schedule') }" @click="router.push('/mobile/schedule')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
        </svg>
        <span>ตาราง</span>
      </button>

      <button class="nav-item" :class="{ active: isActive('/mobile/change-pin') }" @click="router.push({ path: '/mobile/change-pin', query: { user: userStore.userName } })">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
        </svg>
        <span>รหัสพิน</span>
      </button>

      <button class="nav-item nav-logout" @click="logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
        </svg>
        <span>ออกจากระบบ</span>
      </button>
    </nav>

    <Teleport to="body">
      <div v-if="showBookingModal" class="booking-overlay" @click.self="showBookingModal = false">
        <section class="booking-modal" role="dialog" aria-modal="true" aria-label="จองห้อง">
          <button type="button" class="booking-close" aria-label="ปิดหน้าต่างจองห้อง" @click="showBookingModal = false">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <BookingDesktop
            :start-time="bookingStartTime"
            :finish-time="bookingFinishTime"
            :room-code="bookingRoomCode"
            :booking-date="bookingDate"
            @booked="showBookingModal = false"
          />
        </section>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.top-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 44px;
  background: var(--brand-primary);
  border-bottom: 1px solid var(--brand-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.75rem;
  z-index: 200;
}

.top-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.top-logo {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.top-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--brand-on-primary);
  letter-spacing: 0.03em;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  background: var(--brand-control-bg);
  border: 1px solid var(--brand-control-border);
  border-radius: 999px;
  color: var(--brand-on-primary);
  cursor: pointer;
  transition: color .15s, background .15s, border-color .15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0;
}

.logout-btn svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.logout-btn:hover,
.logout-btn:active {
  background: var(--status-busy-soft);
  border-color: var(--status-busy-text);
  color: var(--status-busy-text);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding-top: 44px;
  padding-bottom: 72px;
}

.booking-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.7rem;
  background: rgb(15 23 42 / 0.65);
  backdrop-filter: blur(3px);
}

.booking-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 1rem;
  box-shadow: 0 25px 60px rgb(0 0 0 / 0.5);
}

.booking-modal :deep(.page) {
  position: static !important;
  inset: auto !important;
  width: auto !important;
  height: auto !important;
  min-height: 0 !important;
}

.booking-close {
  position: absolute;
  top: 0.8rem;
  right: 0.8rem;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #6b7280;
  color: #fff;
  cursor: pointer;
}

.booking-close svg {
  width: 1rem;
  height: 1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.booking-close:hover { background: #4b5563; }
.booking-close:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

/* ── Bottom navigation ── */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: stretch;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color .15s, background .15s;
  -webkit-tap-highlight-color: transparent;
  padding: 0;
}

.nav-item svg {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.nav-item span {
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.nav-item.active {
  color: var(--accent-link);
}

.nav-item.active svg {
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--accent-link) 50%, transparent));
}

.nav-item:not(.nav-logout):active,
.nav-item:not(.nav-logout):hover {
  background: var(--dashboard-accent-soft);
  color: var(--accent-link);
}

.nav-logout { color: var(--text-secondary); }
.nav-logout:hover,
.nav-logout:active {
  background: var(--status-busy-soft);
  color: var(--status-busy-text);
}

/* ── MQTT badge ── */
.mqtt-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.62rem;
  color: var(--text-muted);
}

.mqtt-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--border);
}

.mqtt-badge.connected    .mqtt-dot { background: var(--status-free); box-shadow: 0 0 5px color-mix(in srgb, var(--status-free) 55%, transparent); }
.mqtt-badge.connecting   .mqtt-dot { background: var(--status-pending); }
.mqtt-badge.disconnected .mqtt-dot { background: var(--status-busy); }

.mqtt-host { font-family: monospace; letter-spacing: 0.02em; }

.mqtt-msg {
  background: var(--dashboard-accent-soft);
  color: var(--accent-link);
  border-radius: 999px;
  padding: 0.1rem 0.45rem;
  font-size: 0.6rem;
  white-space: nowrap;
}

.msg-fade-enter-active, .msg-fade-leave-active { transition: opacity 0.3s; }
.msg-fade-enter-from,  .msg-fade-leave-to      { opacity: 0; }
</style>
