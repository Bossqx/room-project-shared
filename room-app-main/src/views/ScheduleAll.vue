<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import FullCalendar from "@fullcalendar/vue3";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";
import type { CalendarOptions, EventInput } from "@fullcalendar/core";
import config from "../assets/config.json";

const API_BASE = (config.apiRoute ?? "http://localhost:8000/").replace(/\/$/, "");

interface ScheduleRow {
  rowId: number;
  roomcode: string;
  coursecode: string;
  coursename: string;
  schedule_date: string;
  teacher_name: string;
  startTime: string;
  finishTime: string;
  userCode: string;
}

const events = ref<EventInput[]>([]);
const loading = ref(true);
const errorMsg = ref("");

function toEvent(item: ScheduleRow): EventInput | null {
  if (!item.schedule_date || !item.startTime || !item.finishTime) return null;
  const dateOnly = item.schedule_date.slice(0, 10);
  const start = `${dateOnly}T${item.startTime}`;
  const end = `${dateOnly}T${item.finishTime}`;
  const isPast = end < new Date().toISOString().slice(0, 16);

  return {
    id: String(item.rowId),
    title: item.roomcode,
    start,
    end,
    classNames: [isPast ? "sched-event-past" : "sched-event-upcoming"],
    extendedProps: {
      roomcode: item.roomcode,
      coursecode: item.coursecode,
      coursename: item.coursename,
      teacher_name: item.teacher_name,
      userCode: item.userCode,
      rowId: item.rowId,
    },
  };
}

async function loadSchedule() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const res = await fetch(`${API_BASE}/schedule/get_schedule_from_json/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: ScheduleRow[] = await res.json();
    events.value = (Array.isArray(data) ? data : [])
      .map(toEvent)
      .filter((e): e is EventInput => e !== null);
  } catch (err) {
    errorMsg.value = `Failed to load schedule: ${err}`;
  } finally {
    loading.value = false;
  }
}

const calendarOptions = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
  initialView: "dayGridMonth",
  height: "100%",
  locale: "th",
  firstDay: 0,
  headerToolbar: {
    left: "today prev,next",
    center: "title",
    right: "dayGridMonth,timeGridWeek,timeGridDay,listMonth",
  },
  buttonText: {
    today: "วันนี้",
    prev: "ย้อน",
    next: "ถัดไป",
    month: "เดือน",
    week: "สัปดาห์",
    day: "วัน",
    list: "กำหนดการ",
  },
  events: events.value,
  dayMaxEvents: true,
  nowIndicator: true,
  slotMinTime: "00:00:00",
  slotMaxTime: "24:00:00",
}));

onMounted(loadSchedule);
</script>

<template>
  <div class="page">
    <div v-if="errorMsg" class="error-box">{{ errorMsg }}</div>
    <div v-if="loading" class="loading-box">Loading schedule…</div>
    <FullCalendar :options="calendarOptions" />
  </div>
</template>

<style scoped>
.page {
  height: 100vh;
  padding: 0.75rem;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  background: var(--bg-page);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.error-box {
  background: var(--pill-error-bg);
  color: var(--pill-error-text);
  border: 1px solid #ef4444;
  border-radius: 0.5rem;
  padding: 0.6rem 0.9rem;
  margin-bottom: 0.6rem;
  font-size: 0.85rem;
}

.loading-box {
  color: #64748b;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
}

.page :deep(.fc) {
  flex: 1;
  min-height: 0;
  background: var(--bg-surface);
  border-radius: 0.6rem;
  padding: 0.5rem;
}

.page :deep(.fc-toolbar-title) {
  color: #ffffff;
  background: #6b7280;
  border-radius: 0.4rem;
  padding: 0.25rem 0.75rem;
}

.page :deep(.sched-event-upcoming) {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

.page :deep(.sched-event-upcoming) .fc-event-title,
.page :deep(.sched-event-upcoming) .fc-event-time,
.page :deep(.sched-event-upcoming) .fc-event-main {
  color: #ffffff;
}

.page :deep(.sched-event-past) .fc-event-title,
.page :deep(.sched-event-past) .fc-event-time,
.page :deep(.sched-event-past) .fc-event-main {
  color: #1e293b;
}

/* List/agenda (กำหนดการ) view uses a different DOM than day/week grids */
.page :deep(.sched-event-upcoming .fc-list-event-dot) {
  border-color: #3b82f6;
  background-color: #3b82f6;
}

.page :deep(.sched-event-upcoming .fc-list-event-title),
.page :deep(.sched-event-upcoming .fc-list-event-time) {
  color: #3b82f6;
  font-weight: 700;
}

.page :deep(.sched-event-past .fc-list-event-dot) {
  border-color: #6b7280;
  background-color: #9ca3af;
}

.page :deep(.sched-event-past .fc-list-event-title),
.page :deep(.sched-event-past .fc-list-event-time) {
  color: #6b7280;
}

.page :deep(.fc-day-past .fc-daygrid-day-number) {
  color: #6b7280;
}

.page :deep(.fc-day-today .fc-daygrid-day-number) {
  color: #22c55e;
  font-weight: 700;
}

.page :deep(.sched-event-past) {
  opacity: 0.6;
}
</style>
