<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import InfoComponent from "./components/InfoComponent.vue";
import RoomComponent from "./components/RoomComponent.vue";
import DashboardCalendar from "./components/DashboardCalendar.vue";

interface Teacher {
  prefixname?: string;
  officername?: string;
  officersurname?: string;
  officerlogin?: string;
}

interface DashboardScheduleItem {
  rowId?: number;
  id?: string | number;
  schedule_id?: string | number;
  roomcode: string;
  coursecode?: string;
  coursename?: string;
  subject_code?: string;
  subject_name?: string;
  schedule_date: string;
  teacher_name?: string | Teacher[];
  userCode?: string;
  user_code?: string;
  user_name?: string;
  user_login?: string;
  startTime: string;
  finishTime: string;
  objective?: string;
  source?: string;
  usage_status?: number | string;
}

const selectedRoomNo = ref<string | null>(null);
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const selectedDateSchedules = ref<DashboardScheduleItem[]>([]);

function selectRoom(roomcode: string) {
  selectedRoomNo.value = roomcode;
}

function closeRoom() {
  selectedRoomNo.value = null;
}

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

const selectedDateLabel = computed(() => {
  const d = new Date(selectedDate.value);
  if (Number.isNaN(d.getTime())) return selectedDate.value;
  return d.toLocaleDateString("th-TH", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
});

function updateDateSchedules(date: string, schedules: DashboardScheduleItem[]) {
  selectedDate.value = date;
  selectedDateSchedules.value = schedules;
}

function scheduleTitle(item: DashboardScheduleItem): string {
  return item.coursename || item.subject_name || item.coursecode || item.subject_code || "รายการจอง";
}

function ownerLabel(item: DashboardScheduleItem): string {
  const teacher = item.teacher_name;
  if (Array.isArray(teacher)) {
    const first = teacher[0];
    return first ? `${first.prefixname ?? ""}${first.officername ?? ""} ${first.officersurname ?? ""}`.trim() : "";
  }
  return teacher || item.user_name || item.user_login || item.userCode || item.user_code || "";
}

function statusLabel(item: DashboardScheduleItem): string {
  const status = Number(item.usage_status);
  if (status === 3) return "ยืนยันแล้ว";
  if (status === 4) return "ปิดการใช้งานแล้ว";
  return item.objective || item.source || "ตามตาราง";
}

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
  <div class="dashboard-shell">
    <header class="dash-clock" aria-label="วันที่และเวลาปัจจุบัน">
      <span class="clock-date">{{ dateLabel }}</span>
      <span class="clock-time" aria-live="off">{{ timeLabel }}</span>
    </header>

    <section class="dashboard-main" aria-label="สถานะห้องและรายละเอียดห้อง">
      <div class="dashboard-primary">
        <InfoComponent :selected-room-no="selectedRoomNo" @select-room="selectRoom" />
      </div>

      <aside class="dashboard-detail" aria-label="รายละเอียดห้องที่เลือก">
        <RoomComponent v-if="selectedRoomNo" :room-no="selectedRoomNo" @close="closeRoom" />
        <div v-else class="placeholder-panel">
          <p class="placeholder-text">เลือกห้องเพื่อดูรายละเอียด</p>
        </div>
      </aside>
    </section>

    <section class="dashboard-lower" aria-label="ปฏิทินและตารางการใช้ห้อง">
      <DashboardCalendar @date-schedules="updateDateSchedules" />

      <section class="day-schedule-panel" aria-labelledby="day-schedule-title">
        <div class="schedule-head">
          <div>
            <h2 id="day-schedule-title">ตารางการใช้ห้อง</h2>
            <p>{{ selectedDateLabel }}</p>
          </div>
          <span class="schedule-count" :aria-label="`วันที่เลือกมีรายการจอง ${selectedDateSchedules.length} รายการ`">{{ selectedDateSchedules.length }}</span>
        </div>

        <div v-if="!selectedDateSchedules.length" class="empty-schedule">
          ไม่มีรายการจองในวันที่เลือก
        </div>
        <ul v-else class="day-schedule-list">
          <li
            v-for="item in selectedDateSchedules"
            :key="`${item.rowId ?? item.schedule_id ?? item.id ?? item.roomcode}-${item.startTime}-${item.finishTime}`"
            class="day-schedule-item"
          >
            <span class="schedule-time">{{ item.startTime }}-{{ item.finishTime }}</span>
            <span class="schedule-room">{{ item.roomcode }}</span>
            <span class="schedule-title">{{ scheduleTitle(item) }}</span>
            <span v-if="ownerLabel(item)" class="schedule-owner">{{ ownerLabel(item) }}</span>
            <span class="schedule-status">{{ statusLabel(item) }}</span>
          </li>
        </ul>
      </section>
    </section>
  </div>
</template>

<style scoped>
.dash-clock {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 0.8rem;
  min-height: 2.65rem;
  padding: 0.42rem 0.75rem;
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
  background: var(--dashboard-surface);
  box-sizing: border-box;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

.clock-date {
  font-size: 0.9rem;
  color: var(--dashboard-text-secondary);
}

.clock-time {
  font-size: 1.5rem;
  font-weight: 750;
  color: var(--dashboard-text);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
  line-height: 1.1;
}

.dashboard-shell {
  display: flex;
  flex-direction: column;
  gap: 0.58rem;
  width: 100%;
  min-height: calc(100vh - 4rem);
  margin: 0;
  padding: 0.65rem 1rem 0.75rem;
  box-sizing: border-box;
  background: var(--dashboard-page);
  max-width: 100%;
}

.dashboard-main {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(20rem, 3fr);
  gap: 0.62rem;
  align-items: start;
}

.dashboard-primary,
.dashboard-detail {
  min-width: 0;
}

.dashboard-detail {
  box-sizing: border-box;
  align-self: flex-start;
  min-height: 0;
  max-height: calc(100vh - 15.5rem);
  overflow: visible;
}

.dashboard-detail :deep(.room-panel) {
  max-height: calc(100vh - 15.5rem);
}

.dashboard-lower {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(18rem, 0.65fr);
  gap: 0.62rem;
  align-items: stretch;
}

.placeholder-panel {
  min-height: 200px;
  background: var(--dashboard-surface);
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  color: var(--dashboard-text-muted);
  font-size: 0.85rem;
  margin: 0;
}

.day-schedule-panel {
  min-width: 0;
  background: var(--dashboard-surface);
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
  padding: 0.62rem 0.68rem;
  box-sizing: border-box;
}

.schedule-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}

.schedule-head h2 {
  margin: 0;
  font-size: 0.88rem;
  color: var(--dashboard-text-strong);
}

.schedule-head p {
  margin: 0.12rem 0 0;
  font-size: 0.72rem;
  color: var(--dashboard-text-secondary);
}

.schedule-count {
  min-width: 1.7rem;
  height: 1.7rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--dashboard-accent-soft);
  color: var(--dashboard-accent-strong);
  font-size: 0.78rem;
  font-weight: 800;
}

.empty-schedule {
  color: var(--dashboard-text-muted);
  font-size: 0.8rem;
  padding: 0.8rem 0;
}

.day-schedule-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 13rem;
  overflow-y: auto;
  margin: 0;
  padding: 0;
}

.day-schedule-item {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  gap: 0.4rem;
  align-items: center;
  border: 1px solid var(--dashboard-border-soft);
  border-radius: 0.45rem;
  padding: 0.42rem 0.5rem;
  font-size: 0.75rem;
}

.schedule-time {
  font-variant-numeric: tabular-nums;
  color: var(--dashboard-accent-strong);
  font-weight: 800;
  white-space: nowrap;
}

.schedule-room {
  color: var(--dashboard-text-secondary);
  font-weight: 750;
  white-space: nowrap;
}

.schedule-title {
  min-width: 0;
  color: var(--dashboard-text);
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-owner {
  grid-column: 3;
  color: var(--dashboard-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.schedule-status {
  grid-column: 4;
  grid-row: 1 / span 2;
  color: var(--dashboard-text-secondary);
  font-size: 0.68rem;
  font-weight: 750;
  white-space: nowrap;
}

@media (min-width: 1121px) {
  .dashboard-shell {
    display: grid;
    grid-template-columns: minmax(0, 7fr) minmax(20rem, 3fr);
    grid-auto-rows: auto;
    align-items: start;
    column-gap: 0.62rem;
    row-gap: 0.58rem;
  }

  .dash-clock {
    grid-column: 1 / -1;
    grid-row: 1;
  }

  .dashboard-main,
  .dashboard-primary,
  .dashboard-primary :deep(.dash-root) {
    display: contents;
  }

  .dashboard-primary :deep(.top-stat-row) {
    grid-column: 1;
    grid-row: 2;
    width: 100%;
  }

  .dashboard-primary :deep(.dash-root > .panel) {
    grid-column: 1;
    grid-row: 3;
    width: 100%;
  }

  .dashboard-detail {
    grid-column: 2;
    grid-row: 2 / span 2;
    width: 100%;
    height: min(25rem, calc(100vh - 9.75rem));
    max-height: min(25rem, calc(100vh - 9.75rem));
    overflow: hidden;
  }

  .dashboard-detail :deep(.room-panel) {
    height: 100%;
    max-height: 100%;
  }

  .dashboard-lower {
    grid-column: 1 / -1;
    grid-row: 4;
  }

  .dashboard-primary :deep(.split-row) {
    grid-column: 1;
    grid-row: 5;
    width: 100%;
  }

  .dashboard-primary :deep(.bottom-row) {
    grid-column: 1 / -1;
    grid-row: 6;
    width: 100%;
  }

  .dashboard-primary :deep(.dash-footer) {
    grid-column: 1 / -1;
    grid-row: 7;
  }
}

@media (max-width: 1120px) {
  .dashboard-main,
  .dashboard-lower {
    grid-template-columns: 1fr;
  }

  .dashboard-main {
    display: contents;
  }

  .dashboard-primary,
  .dashboard-primary :deep(.dash-root) {
    display: contents;
  }

  .dashboard-primary :deep(.top-stat-row) {
    order: 1;
    width: 100%;
  }

  .dashboard-primary :deep(.dash-root > .panel) {
    order: 2;
    width: 100%;
  }

  .dashboard-detail {
    order: 3;
    width: 100%;
    min-height: 0;
    max-height: none;
    overflow: visible;
  }

  .dashboard-primary :deep(.split-row) {
    order: 5;
    width: 100%;
  }

  .dashboard-primary :deep(.bottom-row) {
    order: 6;
    width: 100%;
  }

  .dashboard-primary :deep(.dash-footer) {
    order: 7;
  }

  .dashboard-lower {
    order: 4;
  }

  .dashboard-detail :deep(.room-panel) {
    max-height: none;
  }
}

@media (max-width: 960px) {
  .dashboard-shell {
    padding: 0.75rem;
  }

  .dash-clock {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.1rem;
  }

  .day-schedule-item {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .schedule-room {
    grid-column: 2;
  }

  .schedule-title,
  .schedule-owner {
    grid-column: 1 / -1;
    white-space: normal;
  }

  .schedule-status {
    grid-column: 3;
    grid-row: 1;
  }
}

@media (max-width: 520px) {
  .dashboard-shell {
    gap: 0.55rem;
    padding: 0.55rem;
  }

  .dash-clock {
    padding: 0.5rem 0.6rem;
  }

  .clock-time {
    font-size: 1.35rem;
  }

  .day-schedule-panel {
    padding: 0.65rem;
  }

  .schedule-head {
    align-items: center;
  }

  .day-schedule-list {
    max-height: none;
  }

  .day-schedule-item {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .schedule-time,
  .schedule-room,
  .schedule-title,
  .schedule-owner {
    grid-column: 1;
  }

  .schedule-status {
    grid-column: 2;
    grid-row: 1;
    align-self: start;
  }
}
</style>
