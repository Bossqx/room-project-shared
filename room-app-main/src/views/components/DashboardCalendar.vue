<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import config from "../../assets/config.json";

const API_BASE = (config.apiRoute ?? "http://localhost:8000/").replace(/\/$/, "");

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

interface Teacher {
  prefixname?: string;
  officername?: string;
  officersurname?: string;
  officerlogin?: string;
}

interface CalendarDay {
  date: string;
  dayNo: number;
  currentMonth: boolean;
  isToday: boolean;
  isSelected: boolean;
  schedules: DashboardScheduleItem[];
}

const emit = defineEmits<{
  "date-schedules": [date: string, schedules: DashboardScheduleItem[]];
}>();

const schedules = ref<DashboardScheduleItem[]>([]);
const selectedDate = ref(new Date().toISOString().slice(0, 10));
const visibleMonth = ref(selectedDate.value.slice(0, 7));
const state = ref<"loading" | "idle" | "error">("loading");
const errorMsg = ref("");
const dayButtonRefs = new Map<string, HTMLButtonElement>();

function dateKey(value: string): string {
  return value.slice(0, 10);
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function addMonths(month: string, delta: number): string {
  const [year, monthIndex] = month.split("-").map(Number);
  const d = new Date(year, monthIndex - 1 + delta, 1);
  return d.toISOString().slice(0, 7);
}

function formatMonth(month: string): string {
  const [year, monthIndex] = month.split("-").map(Number);
  return new Date(year, monthIndex - 1, 1).toLocaleDateString("th-TH", {
    month: "long",
    year: "numeric",
  });
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

const selectedDaySchedules = computed(() =>
  schedules.value
    .filter((item) => dateKey(item.schedule_date) === selectedDate.value)
    .sort((a, b) => a.startTime.localeCompare(b.startTime)),
);

const monthLabel = computed(() => formatMonth(visibleMonth.value));

const selectedDateLabel = computed(() => formatDateLabel(selectedDate.value));

function formatDateLabel(date: string): string {
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString("th-TH", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

const calendarDays = computed<CalendarDay[]>(() => {
  const [year, monthIndex] = visibleMonth.value.split("-").map(Number);
  const first = new Date(year, monthIndex - 1, 1);
  const start = new Date(first);
  start.setDate(first.getDate() - first.getDay());

  const today = new Date().toISOString().slice(0, 10);
  return Array.from({ length: 42 }, (_, index) => {
    const d = new Date(start);
    d.setDate(start.getDate() + index);
    const date = toIsoDate(d);
    const daySchedules = schedules.value.filter((item) => dateKey(item.schedule_date) === date);
    return {
      date,
      dayNo: d.getDate(),
      currentMonth: date.slice(0, 7) === visibleMonth.value,
      isToday: date === today,
      isSelected: date === selectedDate.value,
      schedules: daySchedules,
    };
  });
});

async function loadSchedule() {
  state.value = "loading";
  errorMsg.value = "";
  try {
    const res = await fetch(`${API_BASE}/schedule/get_schedule_from_json/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    schedules.value = Array.isArray(data) ? data : [];
    state.value = "idle";
  } catch (err) {
    errorMsg.value = `Failed to load calendar: ${err}`;
    state.value = "error";
  }
}

function setDayButtonRef(date: string, el: Element | null) {
  if (el instanceof HTMLButtonElement) {
    dayButtonRefs.set(date, el);
  } else {
    dayButtonRefs.delete(date);
  }
}

async function focusDateButton(date: string) {
  await nextTick();
  dayButtonRefs.get(date)?.focus();
}

function selectDate(date: string) {
  selectedDate.value = date;
  visibleMonth.value = date.slice(0, 7);
}

function shiftMonth(delta: number) {
  visibleMonth.value = addMonths(visibleMonth.value, delta);
}

function shiftSelectedDate(deltaDays: number) {
  const current = new Date(selectedDate.value);
  if (Number.isNaN(current.getTime())) return;
  current.setDate(current.getDate() + deltaDays);
  const nextDate = toIsoDate(current);
  selectDate(nextDate);
  focusDateButton(nextDate);
}

function handleDayKeydown(event: KeyboardEvent, day: CalendarDay) {
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    shiftSelectedDate(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    shiftSelectedDate(1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    shiftSelectedDate(-7);
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    shiftSelectedDate(7);
  } else if (event.key === "Home") {
    event.preventDefault();
    const nextDate = day.date.slice(0, 8) + "01";
    selectDate(nextDate);
    focusDateButton(nextDate);
  } else if (event.key === "End") {
    event.preventDefault();
    const [year, month] = day.date.slice(0, 7).split("-").map(Number);
    const nextDate = toIsoDate(new Date(year, month, 0));
    selectDate(nextDate);
    focusDateButton(nextDate);
  } else if (event.key === "PageUp") {
    event.preventDefault();
    const [year, monthIndex, dayNo] = selectedDate.value.split("-").map(Number);
    const nextDate = toIsoDate(new Date(year, monthIndex - 2, dayNo));
    selectDate(nextDate);
    focusDateButton(nextDate);
  } else if (event.key === "PageDown") {
    event.preventDefault();
    const [year, monthIndex, dayNo] = selectedDate.value.split("-").map(Number);
    const nextDate = toIsoDate(new Date(year, monthIndex, dayNo));
    selectDate(nextDate);
    focusDateButton(nextDate);
  }
}

function dayAriaLabel(day: CalendarDay): string {
  const parts = [formatDateLabel(day.date)];
  if (day.isToday) parts.push("วันนี้");
  if (day.isSelected) parts.push("วันที่เลือก");
  if (!day.currentMonth) parts.push("นอกเดือนที่แสดง");
  parts.push(day.schedules.length ? `มีรายการจอง ${day.schedules.length} รายการ` : "ไม่มีรายการจอง");
  return parts.join(", ");
}

watch(
  selectedDaySchedules,
  (items) => {
    emit("date-schedules", selectedDate.value, items);
  },
  { immediate: true },
);

onMounted(loadSchedule);

defineExpose({ scheduleTitle, ownerLabel });
</script>

<template>
  <section class="calendar-panel" aria-labelledby="booking-calendar-title">
    <div class="calendar-head">
      <div>
        <h2 id="booking-calendar-title" class="panel-title">ปฏิทินการใช้ห้อง</h2>
        <p class="calendar-subtitle">{{ monthLabel }}</p>
      </div>
      <div class="calendar-controls" aria-label="เลือกเดือน">
        <button type="button" class="nav-btn" aria-label="เดือนก่อนหน้า" @click="shiftMonth(-1)">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
        </button>
        <button type="button" class="today-btn" aria-label="เลือกวันนี้" @click="selectDate(new Date().toISOString().slice(0, 10))">วันนี้</button>
        <button type="button" class="nav-btn" aria-label="เดือนถัดไป" @click="shiftMonth(1)">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m9 18 6-6-6-6" />
          </svg>
        </button>
      </div>
    </div>

    <p class="sr-only" aria-live="polite">วันที่เลือก {{ selectedDateLabel }} มี {{ selectedDaySchedules.length }} รายการจอง</p>
    <div v-if="state === 'error'" class="calendar-state error" role="alert">{{ errorMsg }}</div>
    <div v-else-if="state === 'loading'" class="calendar-state" role="status">กำลังโหลดปฏิทิน…</div>
    <div v-else class="calendar-grid" :aria-label="`ปฏิทินการจองรายเดือน ${monthLabel}`">
      <div v-for="day in ['อา', 'จ', 'อ', 'พ', 'พฤ', 'ศ', 'ส']" :key="day" class="weekday" role="columnheader">
        {{ day }}
      </div>
      <button
        v-for="day in calendarDays"
        :key="day.date"
        :ref="(el) => setDayButtonRef(day.date, el as Element | null)"
        type="button"
        class="day-cell"
        :class="{ muted: !day.currentMonth, today: day.isToday, selected: day.isSelected, booked: day.schedules.length }"
        :aria-pressed="day.isSelected"
        :aria-current="day.isToday ? 'date' : undefined"
        :aria-label="dayAriaLabel(day)"
        @click="selectDate(day.date)"
        @keydown="handleDayKeydown($event, day)"
      >
        <span class="day-no">{{ day.dayNo }}</span>
        <span v-if="day.schedules.length" class="booking-count" aria-hidden="true">{{ day.schedules.length }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.calendar-panel {
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  background: var(--dashboard-surface);
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
  padding: 0.62rem 0.68rem;
}

.calendar-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.42rem;
}

.panel-title {
  margin: 0;
  font-size: 0.88rem;
  font-weight: 750;
  color: var(--dashboard-text-strong);
}

.calendar-subtitle {
  margin: 0.12rem 0 0;
  font-size: 0.72rem;
  color: var(--dashboard-text-secondary);
}

.calendar-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  min-width: 0;
}

.nav-btn,
.today-btn {
  border: 1px solid var(--dashboard-border);
  background: var(--dashboard-surface-raised);
  color: var(--dashboard-control-text);
  border-radius: 0.38rem;
  font: inherit;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.nav-btn {
  width: 2rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.nav-btn svg {
  width: 0.95rem;
  height: 0.95rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.today-btn {
  height: 2rem;
  padding: 0 0.6rem;
}

.nav-btn:hover,
.nav-btn:focus-visible,
.today-btn:hover,
.today-btn:focus-visible {
  border-color: var(--dashboard-accent);
  outline: none;
}

.calendar-state {
  color: var(--dashboard-text-muted);
  font-size: 0.8rem;
  padding: 1rem 0;
}

.calendar-state.error {
  color: var(--dashboard-error-text);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.22rem;
  min-width: 0;
}

.weekday {
  color: var(--dashboard-text-subtle);
  font-size: 0.66rem;
  font-weight: 750;
  text-align: center;
  padding: 0.1rem;
}

.day-cell {
  position: relative;
  min-width: 0;
  min-height: 1.95rem;
  aspect-ratio: auto;
  border: 1px solid var(--dashboard-border-soft);
  border-radius: 0.38rem;
  background: var(--dashboard-surface-raised);
  color: var(--dashboard-text);
  font: inherit;
  font-size: 0.75rem;
  cursor: pointer;
}

.day-cell.muted {
  color: var(--dashboard-text-muted);
  background: var(--dashboard-surface-muted);
}

.day-cell.booked {
  border-color: color-mix(in srgb, var(--dashboard-accent) 45%, var(--dashboard-border));
}

.day-cell.today .day-no {
  color: var(--status-free);
  font-weight: 800;
}

.day-cell.selected {
  border-color: var(--dashboard-accent);
  box-shadow: inset 0 0 0 1px var(--dashboard-accent);
}

.day-cell:hover,
.day-cell:focus-visible {
  border-color: var(--dashboard-accent);
  outline: none;
}

.day-no {
  position: absolute;
  top: 0.24rem;
  left: 0.32rem;
}

.booking-count {
  position: absolute;
  right: 0.25rem;
  bottom: 0.22rem;
  min-width: 1.15rem;
  height: 1.15rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--dashboard-accent);
  color: var(--brand-on-primary);
  font-size: 0.62rem;
  font-weight: 800;
}

@media (max-width: 520px) {
  .calendar-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .calendar-controls {
    width: 100%;
    justify-content: space-between;
  }

  .day-cell {
    aspect-ratio: auto;
    min-height: 2.75rem;
  }

  .booking-count {
    right: 0.18rem;
    bottom: 0.18rem;
  }
}
</style>
