<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import ThemeToggle from '../views/components/ThemeToggle.vue'
import LanguageToggle from '../views/components/LanguageToggle.vue'

const router    = useRouter()
const route     = useRoute()
const userStore = useUserStore()

const menuItems = [
  {
    name: '/dashboard',
    label: 'Dashboard',
    path: '/dashboard',
    icon: 'm2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
  },
  {
    name: '/admin/dashboard-new',
    label: 'แดชบอร์ดใหม่',
    path: '/admin/dashboard-new',
    icon: 'M3.75 3.75h6v6h-6v-6Zm10.5 0h6v6h-6v-6Zm-10.5 10.5h6v6h-6v-6Zm10.5 0h6v6h-6v-6Z',
  },
]

const adminSubItems = [
  {
    name: '/admin/home',
    label: 'Migration',
    path: '/admin/home',
    icon: 'M16.5 3.75V16.5L12 21m0 0-4.5-4.5M12 21V3.75',
  },
  {
    name: '/admin/semester',
    label: 'Semester',
    path: '/admin/semester',
    icon: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5',
  },
  {
    name: '/admin/schedule',
    label: 'Schedule',
    path: '/admin/schedule',
    icon: 'M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z',
  },
  {
    name: '/admin/rooms',
    label: 'Rooms',
    path: '/admin/rooms',
    icon: 'M2.25 21h19.5M4.5 3h9v18M13.5 21V3h6.75v18M6.75 6.75h.008v.008H6.75V6.75Zm3 0h.008v.008h-.008V6.75Zm-3 3.75h.008v.008H6.75V10.5Zm3 0h.008v.008h-.008V10.5Zm-3 3.75h.008v.008H6.75v-.008Zm3 0h.008v.008h-.008v-.008ZM16.5 6.75h.008v.008H16.5V6.75Zm0 3.75h.008v.008H16.5V10.5Zm0 3.75h.008v.008H16.5v-.008Z',
  },
  {
    name: '/admin/cancel-room',
    label: 'Cancel Room',
    path: '/admin/cancel-room',
    icon: 'M14.74 9-.346 9M9.605 9l.346 9m4.788-9L14.74 9M4.772 5.79h14.456M8.25 5.79V4.5a1.5 1.5 0 0 1 1.5-1.5h4.5a1.5 1.5 0 0 1 1.5 1.5v1.29m-9 0h9.75V18a2.25 2.25 0 0 1-2.25 2.25H8.25A2.25 2.25 0 0 1 6 18V5.79Z',
  },
]

const adminMenuOpen = ref(adminSubItems.some(item => item.name === route.name))

function isActive(name: string) {
  return route.name === name
}

function go(path: string) {
  router.push(path)
}

function logout() {
  userStore.clearUser()
  router.push('/login')
}
</script>

<template>
  <div class="admin-layout">
    <!-- Left menu -->
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-title">Admin</span>
        <div class="brand-actions">
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </div>

      <nav class="menu">
        <button
          v-for="item in menuItems"
          :key="item.name"
          class="menu-item"
          :class="{ active: isActive(item.name) }"
          @click="go(item.path)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span>{{ item.label }}</span>
        </button>

        <div class="menu-group">
          <button
            class="menu-item"
            :class="{ active: adminMenuOpen }"
            @click="adminMenuOpen = !adminMenuOpen"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            <span>Admin</span>
            <svg class="chevron" :class="{ open: adminMenuOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>

          <div v-if="adminMenuOpen" class="submenu">
            <button
              v-for="item in adminSubItems"
              :key="item.name"
              class="menu-item sub-item"
              :class="{ active: isActive(item.name) }"
              @click="go(item.path)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
              </svg>
              <span>{{ item.label }}</span>
            </button>
          </div>
        </div>
      </nav>

      <button class="menu-item logout" @click="logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
        </svg>
        <span>Logout</span>
      </button>
    </aside>

    <!-- Container -->
    <main class="container">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  width: 100%;
  min-height: 100vh;
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ── Left menu ── */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  flex-shrink: 0;
  width: 220px;
  box-sizing: border-box;
  background: var(--brand-primary);
  border-radius: 0 0.6rem 0.6rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 1rem 0.85rem;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.5rem 1rem;
}

.brand-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.brand-actions :deep(.language-switch) {
  color: var(--brand-on-primary);
}

.brand-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--brand-on-primary);
  letter-spacing: 0.02em;
}

.menu {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: transparent;
  border: none;
  border-radius: 0.6rem;
  color: var(--brand-on-primary);
  font-family: 'Kanit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 0.85rem;
  font-weight: 500;
  padding: 0.6rem 0.75rem;
  cursor: pointer;
  white-space: nowrap;
  text-align: left;
  transition: color .15s, background .15s;
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

.menu-group {
  display: flex;
  flex-direction: column;
}

.chevron {
  margin-left: auto;
  width: 14px !important;
  height: 14px !important;
  transition: transform .15s;
}
.chevron.open {
  transform: rotate(90deg);
}

.submenu {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  margin-top: 0.2rem;
  padding-left: 0.75rem;
  border-left: 1px solid var(--brand-control-border);
}

.menu-item.sub-item {
  font-size: 0.8rem;
  padding: 0.5rem 0.75rem;
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
  box-sizing: border-box;
  padding: 2.5rem 2rem 1.5rem;
  overflow-y: auto;
}

/* Keep admin pages usable on tablets and phones without letting the
   navigation consume most of the viewport. */
@media (max-width: 760px) {
  .sidebar {
    width: 84px;
    padding: 0.75rem 0.45rem;
    border-radius: 0 0.75rem 0.75rem 0;
  }

  .brand {
    flex-direction: column;
    gap: 0.55rem;
    padding: 0.25rem 0 0.75rem;
  }

  .brand-title {
    display: none;
  }

  .brand-actions {
    flex-direction: column;
  }

  .menu-item {
    justify-content: center;
    padding: 0.65rem;
  }

  .menu-item > span,
  .chevron {
    display: none;
  }

  .submenu {
    margin-top: 0.15rem;
    padding-left: 0;
    border-left: 0;
  }

  .container {
    padding: 1.25rem 0.75rem;
  }
}
</style>
