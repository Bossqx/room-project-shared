<script setup lang="ts">
import { locale, setLocale, type AppLocale } from '../../i18n'

function selectLanguage(next: AppLocale) {
  if (locale.value !== next) setLocale(next)
}
</script>

<template>
  <div class="language-switch" role="group" :aria-label="locale === 'th' ? 'เลือกภาษา' : 'Choose language'">
    <button
      type="button"
      :class="{ active: locale === 'th' }"
      :aria-pressed="locale === 'th'"
      aria-label="ภาษาไทย"
      @click="selectLanguage('th')"
    >
      ไทย
    </button>
    <button
      type="button"
      :class="{ active: locale === 'en' }"
      :aria-pressed="locale === 'en'"
      aria-label="English"
      @click="selectLanguage('en')"
    >
      EN
    </button>
  </div>
</template>

<style scoped>
.language-switch {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid color-mix(in srgb, currentColor 24%, transparent);
  border-radius: 9px;
  background: color-mix(in srgb, var(--bg-surface, #fff) 14%, transparent);
  color: inherit;
}

.language-switch button {
  min-width: 2.25rem;
  min-height: 1.9rem;
  padding: 0.25rem 0.48rem;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 650;
  line-height: 1;
  cursor: pointer;
  opacity: 0.72;
}

.language-switch button.active {
  background: var(--bg-surface, #fff);
  color: var(--brand-primary, #17479e);
  box-shadow: 0 1px 3px rgb(15 23 42 / 0.18);
  opacity: 1;
}

.language-switch button:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

@media (max-width: 640px) {
  .language-switch button {
    min-width: 2rem;
    min-height: 1.75rem;
    padding-inline: 0.35rem;
    font-size: 0.72rem;
  }
}
</style>
