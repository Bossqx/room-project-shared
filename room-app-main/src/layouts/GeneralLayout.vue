<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, provide, ref } from 'vue'
import ThemeToggle from '../views/components/ThemeToggle.vue'
import LanguageToggle from '../views/components/LanguageToggle.vue'
import BookingDesktop from '../views/components/BookingDesktop.vue'
import { useUserStore } from '../stores/user'
import { locale } from '../i18n'

const logo = '/icons/icon-192.svg'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const showBookingModal = ref(false)
const bookingStartTime = ref('')
const bookingFinishTime = ref('')
const bookingRoomCode = ref('')
const bookingDate = ref('')

function showBooking(startTime?: string, finishTime?: string, roomCode?: string, bookingDateStr?: string) {
  bookingStartTime.value = startTime ?? ''
  bookingFinishTime.value = finishTime ?? ''
  bookingRoomCode.value = roomCode ?? ''
  bookingDate.value = bookingDateStr ?? ''
  showBookingModal.value = true
}

provide('showBooking', showBooking)

const menuItems = [
  {
    label: 'หน้าหลัก',
    path: '/dashboard-first',
    icon: 'M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5M9 21v-6h6v6',
  },
  {
    label: 'ตารางการจอง',
    path: '/desktop/schedule',
    icon: 'M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1ZM8 12h3M13 12h3M8 16h3M13 16h3',
  },
  {
    label: 'จองห้อง',
    path: '/login',
    authPath: '/desktop/overview',
    icon: 'M7 3v3M17 3v3M4 8h16M6 12h7M6 16h5M16 14h4M18 12v4',
  },
  {
    label: 'จัดการ PIN',
    path: '/login',
    authPath: '/desktop/overview',
    icon: 'M15 7a4 4 0 1 1-2.8 6.8L9 17H7v2H5v2H3v-3.2l5.2-5.2A4 4 0 0 1 15 7Z',
  },
]

const visibleMenuItems = computed(() => userStore.isLoggedIn ? menuItems : [])
const authActionLabel = computed(() => {
  if (locale.value === 'th') return userStore.isLoggedIn ? 'ออกจากระบบ' : 'เข้าสู่ระบบ'
  return userStore.isLoggedIn ? 'Logout' : 'Login'
})

function isActive(path: string) {
  return route.path === path
}

function go(path: string, authPath?: string) {
  router.push(userStore.isLoggedIn && authPath ? authPath : path)
}

function handleAuthAction() {
  if (userStore.isLoggedIn) {
    userStore.clearUser()
    router.push('/')
  } else {
    router.push('/login')
  }
}
</script>

<template>
  <div class="other-layout">
    <header class="topbar">
      <div class="brand">
        <img :src="logo" alt="Logo" class="brand-logo" />
        <span class="brand-title">ระบบบริหารจัดการห้องคอมพิวเตอร์สำนักคอมพิวเตอร์</span>
      </div>

      <nav v-if="visibleMenuItems.length" class="menu" aria-label="เมนูหลัก">
        <button
          v-for="item in visibleMenuItems"
          :key="item.label"
          type="button"
          class="menu-item"
          :class="{ active: isActive(item.path) }"
          :aria-current="isActive(item.path) ? 'page' : undefined"
          @click="go(item.path, item.authPath)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="right-group">
        <LanguageToggle />
        <ThemeToggle />
        <button type="button" class="login-link" @click="handleAuthAction">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
          <span>{{ authActionLabel }}</span>
        </button>
      </div>
    </header>

    <main class="container">
      <RouterView />
    </main>

    <Teleport to="body">
      <div v-if="showBookingModal" class="booking-overlay" @click.self="showBookingModal = false">
        <section class="booking-modal" role="dialog" aria-modal="true" aria-label="จองห้อง">
          <button type="button" class="booking-close" aria-label="ปิดหน้าต่างจองห้อง" @click="showBookingModal = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
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
.other-layout {
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 0.6rem 1.5rem;
  max-width: 100%;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
  flex-shrink: 1;
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
  overflow: hidden;
  text-overflow: ellipsis;
  overflow-wrap: anywhere;
}

.menu {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
  max-width: 100%;
}

.menu-item {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  border: 1px solid transparent;
  border-radius: 0.45rem;
  background: transparent;
  color: var(--brand-on-primary);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 650;
  padding: 0.38rem 0.62rem;
  white-space: nowrap;
  cursor: pointer;
}

.menu-item svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.menu-item:hover,
.menu-item:focus-visible,
.menu-item.active {
  background: var(--brand-control-bg);
  border-color: var(--brand-control-border);
  outline: none;
}

.right-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.login-link {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: var(--brand-control-bg);
  border: 1px solid var(--brand-control-border);
  border-radius: 999px;
  color: var(--brand-on-primary);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s;
}
.login-link:hover { background: var(--brand-control-bg-hover); }
.login-link:focus-visible {
  background: var(--brand-control-bg-hover);
  outline: 2px solid var(--brand-on-primary);
  outline-offset: 2px;
}
.login-link svg { width: 16px; height: 16px; flex-shrink: 0; }

/* ── Container ── */
.container {
  flex: 1;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  padding-top: 0.5rem;
}

.booking-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: rgb(15 23 42 / 0.65);
  backdrop-filter: blur(3px);
}

.booking-modal {
  position: relative;
  width: 100%;
  max-width: 540px;
  max-height: 90vh;
  overflow: visible;
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
  top: 1rem;
  right: 1rem;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.booking-close svg { width: 1rem; height: 1rem; }
.booking-close:hover { background: var(--bg-surface-alt); color: var(--text-primary); }
.booking-close:focus-visible { outline: 2px solid var(--accent-link); outline-offset: 2px; }

@media (max-width: 1180px) {
  .topbar {
    gap: 0.8rem;
    padding-inline: 1rem;
  }

  .brand-title {
    max-width: 18rem;
  }

  .menu {
    justify-content: flex-start;
    overflow-x: auto;
    scrollbar-width: thin;
  }

  .menu-item {
    padding-inline: 0.5rem;
  }

  .right-group {
    gap: 0.5rem;
  }
}

@media (max-width: 820px) {
  .topbar {
    flex-wrap: wrap;
  }

  .brand {
    flex: 1 1 min(100%, 18rem);
  }

  .menu {
    order: 3;
    flex-basis: 100%;
    max-width: 100%;
    padding-bottom: 0.1rem;
  }
}

@media (max-width: 640px) {
  .topbar {
    position: static;
    top: auto;
    z-index: auto;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding: 0.65rem 0.85rem;
  }
  .brand { flex: 1 1 min(100%, 18rem); }
  .brand-title { white-space: normal; }
  .menu {
    order: 3;
    flex-basis: 100%;
    max-width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 0.1rem;
  }
  .menu-item { font-size: 0.78rem; padding: 0.34rem 0.5rem; }
  .container { padding-top: 0.5rem; }
  .booking-overlay { padding: 0.7rem; }
  .booking-modal { max-height: calc(100dvh - 1.4rem); overflow-y: auto; }
}
</style>
