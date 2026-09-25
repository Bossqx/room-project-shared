<script setup lang="ts">
</script>

<template>
  <div class="frame-page">
    <RouterView />
  </div>
</template>

<style scoped>
.frame-page {
  width: 100%;
  min-height: 100vh;
  box-sizing: border-box;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1rem;
}

@media (max-width: 600px) {
  .frame-page { padding: 0.5rem; }
}
</style>
