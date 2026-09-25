<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
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

// Fixed categorical order — never cycled/reassigned per re-render.
const CATEGORICAL = [
  "#2a78d6", // blue
  "#eb6834", // orange
  "#1baf7a", // aqua
  "#eda100", // yellow
  "#e87ba4", // magenta
  "#008300", // green
  "#4a3aa7", // violet
  "#e34948", // red (also doubles as "Other")
];

const items = ref<ScheduleRow[]>([]);
const loading = ref(true);
const errorMsg = ref("");
const now = ref(new Date());

const todayStr = computed(() => new Date().toISOString().slice(0, 10));

function toMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function hoursBetween(start: string, finish: string): number {
  if (!start || !finish) return 0;
  const diff = toMinutes(finish) - toMinutes(start);
  return diff > 0 ? diff / 60 : 0;
}

async function loadSchedule() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const res = await fetch(`${API_BASE}/schedule/get_schedule_all_DB/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: ScheduleRow[] = await res.json();
    items.value = Array.isArray(data) ? data : [];
  } catch (err) {
    errorMsg.value = `Failed to load schedule: ${err}`;
  } finally {
    loading.value = false;
  }
}

// ---------------------------------------------------------------------------
// Left pane — today's list, current item highlighted as active
// ---------------------------------------------------------------------------
const todayItems = computed(() =>
  items.value
    .filter((i) => i.schedule_date?.slice(0, 10) === todayStr.value && i.startTime && i.finishTime)
    .sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime)),
);

function isActiveNow(item: ScheduleRow): boolean {
  const nowMin = now.value.getHours() * 60 + now.value.getMinutes();
  return nowMin >= toMinutes(item.startTime) && nowMin <= toMinutes(item.finishTime);
}

// ---------------------------------------------------------------------------
// Right pane — total hours by room, across all schedule data
// ---------------------------------------------------------------------------
interface RoomHours {
  room: string;
  hours: number;
  color: string;
}

const roomHoursSorted = computed<RoomHours[]>(() => {
  const totals = new Map<string, number>();
  for (const item of items.value) {
    if (!item.roomcode) continue;
    const h = hoursBetween(item.startTime, item.finishTime);
    totals.set(item.roomcode, (totals.get(item.roomcode) ?? 0) + h);
  }
  const sorted = [...totals.entries()]
    .map(([room, hours]) => ({ room, hours: Math.round(hours * 10) / 10 }))
    .sort((a, b) => b.hours - a.hours);

  // Categorical hues seat at most 8 slots (see palette § series-count ladder);
  // past 3 all-pairs is unsafe for a pie, so fold the tail into "Other" at 7.
  const PIE_CAP = 7;
  if (sorted.length <= PIE_CAP) {
    return sorted.map((r, i) => ({ ...r, color: CATEGORICAL[i] }));
  }
  const head = sorted.slice(0, PIE_CAP).map((r, i) => ({ ...r, color: CATEGORICAL[i] }));
  const tailHours = sorted.slice(PIE_CAP).reduce((sum, r) => sum + r.hours, 0);
  return [...head, { room: "อื่นๆ", hours: Math.round(tailHours * 10) / 10, color: CATEGORICAL[7] }];
});

const barMax = computed(() => Math.max(1, ...roomHoursSorted.value.map((r) => r.hours)));

// ---------------------------------------------------------------------------
// Pie geometry — plain SVG arcs so each slice is its own hoverable mark
// ---------------------------------------------------------------------------
const PIE_R = 90;
const PIE_CX = 100;
const PIE_CY = 100;

function polarPoint(angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: PIE_CX + PIE_R * Math.cos(rad), y: PIE_CY + PIE_R * Math.sin(rad) };
}

const pieSlices = computed(() => {
  const total = roomHoursSorted.value.reduce((sum, r) => sum + r.hours, 0);
  if (total <= 0) return [];
  let cursor = 0;
  return roomHoursSorted.value.map((r) => {
    const pct = r.hours / total;
    const startAngle = cursor * 360;
    const endAngle = (cursor + pct) * 360;
    cursor += pct;
    const p1 = polarPoint(startAngle);
    const p2 = polarPoint(endAngle);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    const path =
      pct >= 0.999
        ? `M ${PIE_CX - PIE_R},${PIE_CY} A ${PIE_R},${PIE_R} 0 1,1 ${PIE_CX + PIE_R},${PIE_CY} A ${PIE_R},${PIE_R} 0 1,1 ${PIE_CX - PIE_R},${PIE_CY} Z`
        : `M ${PIE_CX},${PIE_CY} L ${p1.x},${p1.y} A ${PIE_R},${PIE_R} 0 ${largeArc},1 ${p2.x},${p2.y} Z`;
    return { ...r, pct, path };
  });
});

// ---------------------------------------------------------------------------
// Shared hover tooltip
// ---------------------------------------------------------------------------
const tooltip = ref<{ visible: boolean; x: number; y: number; title: string; value: string }>({
  visible: false,
  x: 0,
  y: 0,
  title: "",
  value: "",
});

function showTooltip(evt: MouseEvent, title: string, value: string) {
  tooltip.value = { visible: true, x: evt.clientX, y: evt.clientY, title, value };
}
function moveTooltip(evt: MouseEvent) {
  if (!tooltip.value.visible) return;
  tooltip.value.x = evt.clientX;
  tooltip.value.y = evt.clientY;
}
function hideTooltip() {
  tooltip.value.visible = false;
}

let clockTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  loadSchedule();
  clockTimer = setInterval(() => {
    now.value = new Date();
  }, 30_000);
});
</script>

<template>
  <div class="viz-root">
    <div v-if="errorMsg" class="error-box">{{ errorMsg }}</div>

    <div class="layout">
      <!-- Left pane: today's schedule list -->
      <section class="pane list-pane">
        <h2 class="pane-title">ตารางการใช้งานวันนี้</h2>
        <p class="pane-sub">{{ todayStr }}</p>

        <div v-if="loading" class="muted">กำลังโหลด…</div>
        <div v-else-if="!todayItems.length" class="muted">ไม่มีตารางการใช้งานวันนี้</div>

        <ul v-else class="sched-list">
          <li
            v-for="item in todayItems"
            :key="item.rowId"
            class="sched-row"
            :class="{ active: isActiveNow(item) }"
          >
            <span class="sched-time">{{ item.startTime }}–{{ item.finishTime }}</span>
            <span class="sched-room">{{ item.roomcode }}</span>
            <span class="sched-course">{{ item.coursename }}</span>
            <span v-if="isActiveNow(item)" class="active-badge">กำลังใช้งาน</span>
          </li>
        </ul>
      </section>

      <!-- Right pane: dashboard -->
      <section class="pane dashboard-pane">
        <h2 class="pane-title">สรุปชั่วโมงการใช้งานตามห้อง</h2>

        <!-- Bar chart: one series → one hue, no legend needed -->
        <div class="card">
          <p class="card-title">กราฟแท่ง (ชั่วโมงต่อห้อง)</p>
          <div v-if="!roomHoursSorted.length" class="muted">ไม่มีข้อมูล</div>
          <div v-else class="bar-list">
            <div
              v-for="r in roomHoursSorted"
              :key="r.room"
              class="bar-row"
              tabindex="0"
              @pointermove="showTooltip($event, r.room, `${r.hours} ชม.`)"
              @pointerleave="hideTooltip"
              @focus="showTooltip($event as any, r.room, `${r.hours} ชม.`)"
              @blur="hideTooltip"
            >
              <span class="bar-label">{{ r.room }}</span>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: (r.hours / barMax) * 100 + '%' }"
                ></div>
              </div>
              <span class="bar-value">{{ r.hours }} ชม.</span>
            </div>
          </div>
        </div>

        <!-- Pie chart: categorical, fixed hue order, capped at 7 + Other -->
        <div class="card">
          <p class="card-title">กราฟวงกลม (สัดส่วนชั่วโมงต่อห้อง)</p>
          <div v-if="!pieSlices.length" class="muted">ไม่มีข้อมูล</div>
          <div v-else class="pie-wrap">
            <svg viewBox="0 0 200 200" class="pie-svg" @pointerleave="hideTooltip">
              <path
                v-for="s in pieSlices"
                :key="s.room"
                :d="s.path"
                :fill="s.color"
                stroke="var(--surface-1)"
                stroke-width="2"
                tabindex="0"
                @pointermove="showTooltip($event, s.room, `${s.hours} ชม. (${Math.round(s.pct * 100)}%)`)"
                @focus="showTooltip($event as any, s.room, `${s.hours} ชม. (${Math.round(s.pct * 100)}%)`)"
                @blur="hideTooltip"
              />
            </svg>
            <ul class="legend">
              <li v-for="s in pieSlices" :key="s.room" class="legend-row">
                <span class="legend-swatch" :style="{ background: s.color }"></span>
                <span class="legend-label">{{ s.room }}</span>
                <span class="legend-value">{{ s.hours }} ชม.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <!-- Shared hover tooltip -->
    <div
      v-if="tooltip.visible"
      class="viz-tooltip"
      :style="{ left: tooltip.x + 12 + 'px', top: tooltip.y + 12 + 'px' }"
      @pointermove="moveTooltip"
    >
      <div class="viz-tooltip-value">{{ tooltip.value }}</div>
      <div class="viz-tooltip-title">{{ tooltip.title }}</div>
    </div>
  </div>
</template>

<style scoped>
.viz-root {
  color-scheme: inherit;
  --surface-1: var(--dashboard-surface);
  --page-plane: var(--dashboard-page);
  --text-primary: var(--dashboard-text);
  --text-secondary: var(--dashboard-text-secondary);
  --text-muted: var(--dashboard-text-muted);
  --gridline: var(--dashboard-border);
  --baseline: var(--dashboard-border-muted);
  --series-1: var(--dashboard-accent);

  min-height: 100vh;
  box-sizing: border-box;
  padding: 1rem;
  background: var(--page-plane);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}

.error-box {
  background: var(--pill-error-bg);
  color: var(--pill-error-text);
  border: 1px solid var(--status-busy);
  border-radius: 0.5rem;
  padding: 0.6rem 0.9rem;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
}

.layout {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 1.4fr);
  gap: 1rem;
  align-items: start;
}

.pane {
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 0.75rem;
  padding: 1rem 1.1rem;
}

.pane-title {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 0.15rem;
}

.pane-sub {
  color: var(--text-secondary);
  font-size: 0.8rem;
  margin: 0 0 0.9rem;
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 0.5rem 0;
}

/* ── Left pane: today's list ── */
.sched-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-height: 75vh;
  overflow-y: auto;
}

.sched-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.6rem;
  border-radius: 0.5rem;
  border: 1px solid var(--gridline);
  font-size: 0.85rem;
}

.sched-row.active {
  border-color: var(--series-1);
  background: color-mix(in srgb, var(--series-1) 8%, var(--surface-1));
}

.sched-time {
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
  white-space: nowrap;
}

.sched-room {
  font-weight: 700;
  white-space: nowrap;
}

.sched-course {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.active-badge {
  font-size: 0.68rem;
  font-weight: 700;
  color: #ffffff;
  background: var(--series-1);
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
  white-space: nowrap;
}

/* ── Right pane: charts ── */
.card {
  border: 1px solid var(--gridline);
  border-radius: 0.6rem;
  padding: 0.9rem 1rem;
  margin-bottom: 0.9rem;
}
.card:last-child {
  margin-bottom: 0;
}

.card-title {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin: 0 0 0.75rem;
}

.bar-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bar-row {
  display: grid;
  grid-template-columns: 80px 1fr 56px;
  align-items: center;
  gap: 0.6rem;
  border-radius: 0.35rem;
  outline: none;
}
.bar-row:hover,
.bar-row:focus-visible {
  background: color-mix(in srgb, var(--series-1) 6%, transparent);
}

.bar-label {
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 24px;
  background: var(--gridline);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--series-1);
  border-radius: 0 4px 4px 0;
  transition: width 0.2s ease;
}

.bar-value {
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
  text-align: right;
}

.pie-wrap {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.pie-svg {
  width: 200px;
  height: 200px;
  flex-shrink: 0;
}

.pie-svg path {
  cursor: pointer;
  outline: none;
  transition: opacity 0.15s ease;
}
.pie-svg path:hover,
.pie-svg path:focus-visible {
  opacity: 0.85;
}

.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 160px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.8rem;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-label {
  flex: 1;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.legend-value {
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ── Shared tooltip ── */
.viz-tooltip {
  position: fixed;
  z-index: 1000;
  pointer-events: none;
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 0.4rem;
  padding: 0.4rem 0.6rem;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.viz-tooltip-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-primary);
}

.viz-tooltip-title {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
