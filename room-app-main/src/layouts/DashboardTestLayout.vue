<script setup lang="ts">
import { computed, provide, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import ThemeToggle from "../views/components/ThemeToggle.vue";
import LanguageToggle from "../views/components/LanguageToggle.vue";
import BookingDesktop from "../views/components/BookingDesktop.vue";
import { useUserStore } from "../stores/user";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const drawerOpen = ref(false);
const showBookingModal = ref(false);
const bookingStartTime = ref("");
const bookingFinishTime = ref("");
const bookingRoomCode = ref("");
const bookingDate = ref("");
const logo = "/icons/logo.png";

function showBooking(startTime?: string, finishTime?: string, roomCode?: string, bookingDateStr?: string) {
  if (!userStore.isLoggedIn) {
    router.push("/login");
    return;
  }
  bookingStartTime.value = startTime ?? "";
  bookingFinishTime.value = finishTime ?? "";
  bookingRoomCode.value = roomCode ?? "";
  bookingDate.value = bookingDateStr ?? "";
  showBookingModal.value = true;
}

provide("showBooking", showBooking);

const menuItems = [
  {
    label: "หน้าหลัก",
    path: "/dashboard-test",
    icon: "M3 10.5 12 3l9 7.5M5 9.5V21h14V9.5M9 21v-6h6v6",
  },
  {
    label: "ตารางการจอง",
    path: "/desktop/schedule",
    icon: "M7 3v3M17 3v3M4 8h16M5 5h14a1 1 0 0 1 1 1v14H4V6a1 1 0 0 1 1-1ZM8 12h3M13 12h3M8 16h3M13 16h3",
  },
  {
    label: "จองห้อง",
    path: "/login",
    authPath: "/desktop/overview",
    icon: "M7 3v3M17 3v3M4 8h16M6 12h7M6 16h5M16 14h4M18 12v4",
  },
  {
    label: "จัดการ PIN",
    path: "/login",
    authPath: "/desktop/overview",
    icon: "M15 7a4 4 0 1 1-2.8 6.8L9 17H7v2H5v2H3v-3.2l5.2-5.2A4 4 0 0 1 15 7Z",
  },
];

const authActionLabel = computed(() => (userStore.isLoggedIn ? "ออกจากระบบ" : "เข้าสู่ระบบ"));

function isActive(path: string) {
  return route.path === path;
}

function go(path: string, authPath?: string) {
  drawerOpen.value = false;
  router.push(userStore.isLoggedIn && authPath ? authPath : path);
}

function handleAuthAction() {
  drawerOpen.value = false;
  if (userStore.isLoggedIn) {
    userStore.clearUser();
    router.push("/");
  } else {
    router.push("/login");
  }
}
</script>

<template>
  <div class="test-layout">
    <header class="test-topbar">
      <button
        type="button"
        class="drawer-toggle"
        :aria-expanded="drawerOpen"
        aria-controls="dashboard-test-navigation"
        aria-label="เปิดหรือปิดเมนูหลัก"
        @click="drawerOpen = !drawerOpen"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>

      <button type="button" class="brand" aria-label="ไปหน้าหลัก" @click="go('/dashboard-test')">
        <img :src="logo" alt="ตราสัญลักษณ์ระบบบริหารจัดการห้องคอมพิวเตอร์" class="brand-logo" />
        <span class="brand-title">ระบบบริหารจัดการห้องคอมพิวเตอร์สำนักคอมพิวเตอร์</span>
      </button>

      <nav
        id="dashboard-test-navigation"
        class="test-menu"
        :class="{ open: drawerOpen }"
        aria-label="เมนูหลัก"
        @keydown.esc="drawerOpen = false"
      >
        <button
          v-for="item in menuItems"
          :key="item.label"
          type="button"
          class="menu-item"
          :class="{ active: isActive(item.path) }"
          :aria-current="isActive(item.path) ? 'page' : undefined"
          @click="go(item.path, item.authPath)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path :d="item.icon" />
          </svg>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="topbar-actions">
        <LanguageToggle />
        <ThemeToggle />
        <button type="button" class="auth-button" :aria-label="authActionLabel" @click="handleAuthAction">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
          <span>{{ authActionLabel }}</span>
        </button>
      </div>
    </header>

    <button
      v-if="drawerOpen"
      type="button"
      class="drawer-backdrop"
      aria-label="ปิดเมนูหลัก"
      @click="drawerOpen = false"
    />

    <main class="test-content">
      <RouterView />
    </main>

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
.test-layout {
  min-height: 100dvh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif;
  overflow-x: clip;
}

.test-topbar {
  position: relative;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: 3.1rem;
  padding: 0.32rem 1rem;
  box-sizing: border-box;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
  box-shadow: 0 2px 10px rgb(7 31 97 / 0.2);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.62rem;
  min-width: 0;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
}

.brand-logo {
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  box-sizing: border-box;
  padding: 0.15rem;
  border-radius: 50%;
  object-fit: contain;
  background: var(--brand-on-primary);
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.18);
}

.brand-title {
  max-width: 24rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  font-weight: 750;
}

.test-menu {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  min-width: 0;
  margin-inline: auto;
}

.menu-item,
.auth-button,
.drawer-toggle {
  border: 1px solid transparent;
  background: transparent;
  color: #fff;
  font: inherit;
  cursor: pointer;
}

.menu-item {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  min-height: 1.95rem;
  padding: 0.28rem 0.55rem;
  border-radius: 0.5rem;
  font-size: 0.76rem;
  font-weight: 650;
  white-space: nowrap;
}

.menu-item svg,
.auth-button svg,
.drawer-toggle svg {
  width: 1rem;
  height: 1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.menu-item:hover,
.menu-item.active {
  border-color: var(--brand-control-border);
  background: var(--brand-control-bg);
}

.menu-item.active { box-shadow: inset 0 -2px 0 rgb(255 255 255 / 0.9); }

.menu-item:focus-visible,
.auth-button:focus-visible,
.drawer-toggle:focus-visible,
.brand:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 0.48rem;
  flex: 0 0 auto;
}

.auth-button {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  min-height: 1.95rem;
  padding: 0.28rem 0.68rem;
  border-color: rgb(255 255 255 / 0.32);
  border-radius: 999px;
  background: var(--brand-control-bg);
  font-size: 0.76rem;
  font-weight: 650;
}

.auth-button:hover {
  background: var(--brand-control-bg-hover);
}

.drawer-toggle,
.drawer-backdrop {
  display: none;
}

.test-content {
  min-width: 0;
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
  color: var(--brand-on-primary);
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

@media (max-width: 1040px) {
  .brand-title {
    max-width: 13rem;
  }

  .test-topbar {
    gap: 0.55rem;
  }

  .menu-item {
    padding-inline: 0.42rem;
  }
}

@media (max-width: 780px) {
  .test-topbar {
    position: sticky;
    top: 0;
    height: 3.35rem;
    padding-inline: 0.72rem;
  }

  .drawer-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.2rem;
    height: 2.2rem;
    flex: 0 0 auto;
    border-color: rgb(255 255 255 / 0.28);
    border-radius: 0.48rem;
  }

  .brand {
    flex: 1 1 auto;
  }

  .brand-logo {
    width: 1.9rem;
    height: 1.9rem;
  }

  .brand-title {
    max-width: none;
    font-size: 0.82rem;
  }

  .test-menu {
    position: fixed;
    inset: calc(3.35rem + env(safe-area-inset-top, 0px)) auto 0 0;
    z-index: 60;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
    width: min(18rem, 84vw);
    padding: 0.8rem;
    box-sizing: border-box;
    background: var(--brand-primary);
    box-shadow: 8px 0 24px rgb(15 48 138 / 0.22);
    visibility: hidden;
    pointer-events: none;
    transform: translateX(-102%);
    transition: transform 180ms ease-out;
  }

  .test-menu.open {
    visibility: visible;
    pointer-events: auto;
    transform: translateX(0);
  }

  .menu-item {
    justify-content: flex-start;
    min-height: 2.8rem;
    color: var(--brand-on-primary);
    font-size: 0.9rem;
  }

  .menu-item:hover,
  .menu-item.active {
    border-color: var(--brand-control-border);
    background: var(--brand-control-bg-hover);
  }

  .drawer-backdrop {
    position: fixed;
    inset: 0;
    z-index: 45;
    display: block;
    width: 100%;
    border: 0;
    background: rgb(15 23 42 / 0.5);
  }

  .auth-button span {
    display: none;
  }

  .auth-button {
    width: 2.2rem;
    padding: 0;
    justify-content: center;
  }
}

@media (max-width: 430px) {
  .brand-title {
    max-width: 9.5rem;
  }

  .booking-overlay { padding: 0.7rem; }
}

@media (prefers-reduced-motion: reduce) {
  .test-menu {
    transition: none;
  }
}
</style>
