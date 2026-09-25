<script setup lang="ts">
import { computed } from "vue";
import { useThemeStore } from "../../stores/theme";

const themeStore = useThemeStore();

const isDark = computed(() => themeStore.theme === "dark");
const label = computed(() => (isDark.value ? "เปลี่ยนเป็นโหมดสว่าง" : "เปลี่ยนเป็นโหมดมืด"));
</script>

<template>
  <button class="theme-toggle" type="button" :aria-label="label" :title="label" @click="themeStore.toggleTheme()">
    <svg v-if="isDark" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 999px;
  border: 1px solid var(--brand-control-border);
  background: var(--brand-control-bg);
  color: var(--brand-on-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.theme-toggle:hover {
  background: var(--brand-control-bg-hover);
}

.theme-toggle:focus-visible {
  outline: 2px solid var(--brand-on-primary);
  outline-offset: 2px;
}

.theme-toggle svg {
  width: 1.15rem;
  height: 1.15rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.theme-toggle svg circle {
  fill: currentColor;
}
</style>
