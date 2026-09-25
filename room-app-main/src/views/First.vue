<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import InfoComponent from "./components/InfoComponent.vue";
import RoomComponent from "./components/RoomComponent.vue";

const selectedRoomNo = ref<string | null>(null);

function selectRoom(roomcode: string) {
  selectedRoomNo.value = roomcode;
}

function closeRoom() {
  selectedRoomNo.value = null;
}

// ── Live clock (updates every second) ──
const now = ref(new Date());
let clockTimer: ReturnType<typeof setInterval> | null = null;

const dateLabel = computed(() =>
  now.value.toLocaleDateString("th-TH", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }),
);
const timeLabel = computed(() =>
  now.value.toLocaleTimeString("th-TH", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }),
);

onMounted(() => {
  clockTimer = setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer);
});
</script>

<template>
  <div class="dashboard-container">
    <div class="dashboard-split">
      <header class="dash-clock">
        <span class="clock-date">{{ dateLabel }}</span>
        <span class="clock-time">{{ timeLabel }}</span>
      </header>
      <div class="dashboard-col dashboard-col-left">
        <InfoComponent @select-room="selectRoom" />
      </div>
      <div class="dashboard-col dashboard-col-right">
        <RoomComponent
          v-if="selectedRoomNo"
          :room-no="selectedRoomNo"
          @close="closeRoom"
        />
        <div v-else class="placeholder-panel">
          <p class="placeholder-text">Select a room to view details</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  width: 100%;
  min-height: 100vh;
  background: #f5f6f8;
  box-sizing: border-box;
}

/* Date + time — full-width top-left row spanning both columns */
.dash-clock {
  grid-column: 1 / -1;
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: baseline;
  justify-content: flex-start;
  gap: 0.8rem;
  min-height: 2.65rem;
  padding: 0.42rem 0.75rem;
  border: 1px solid #e1e0d9;
  border-radius: 0.75rem;
  background: #f5f6f8;
  font-family:
    system-ui,
    -apple-system,
    "Segoe UI",
    sans-serif;
}

.clock-date {
  font-size: 0.86rem;
  color: #52514e;
  white-space: nowrap;
}

.clock-time {
  font-size: 1.38rem;
  font-weight: 700;
  color: #0b0b0b;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  line-height: 1.1;
}

html[data-theme="dark"] .clock-date {
  color: #c3c2b7;
}
html[data-theme="dark"] .clock-time {
  color: #ffffff;
}
html[data-theme="dark"] .dash-clock {
  background: #0d0d0d;
  border-color: #2c2c2a;
}

.dashboard-split {
  display: grid;
  grid-template-columns: minmax(0, 70%) minmax(20rem, 30%);
  grid-template-rows: auto auto;
  align-items: start;
  gap: 0.65rem;
  width: 100%;
  min-height: calc(100vh - 4.5rem);
  margin: 0;
  padding: 2rem 1.6rem 0.8rem;
  box-sizing: border-box;
  background: #f5f6f8;
}

.dashboard-col-left {
  min-width: 0;
}

.dashboard-col-right {
  min-width: 0;
  box-sizing: border-box;
  padding: 0 0.1rem 1.1rem;
  height: calc(100vh - 8rem);
  min-height: 28rem;
  max-height: calc(100vh - 8rem);
  overflow: hidden;
}

.placeholder-panel {
  height: 100%;
  min-height: 200px;
  background: #fcfcfb;
  border: 1px solid #e1e0d9;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.placeholder-text {
  color: #898781;
  font-size: 0.85rem;
  margin: 0;
}

@media (max-width: 960px) {
  .dashboard-split {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
    padding: 0.9rem 1rem 1.25rem;
  }

  .dash-clock {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.1rem;
  }

  .dashboard-col-left,
  .dashboard-col-right {
    width: auto;
    height: auto;
    min-height: 0;
    max-height: none;
    overflow: visible;
  }
}
</style>
