<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, inject } from "vue";
import config from "../../assets/config.json";
import { useUserStore } from "../../stores/user";

const API_BASE = (config.apiRoute ?? "http://localhost:8000/").replace(/\/$/, "");

const userStore = useUserStore();
const showBooking = inject<((startTime?: string, finishTime?: string, roomCode?: string) => void) | undefined>(
  "showBooking",
  undefined,
);

const props = defineProps<{
  selectedRoomNo?: string | null;
}>();

const emit = defineEmits<{ "select-room": [roomcode: string] }>();

interface RoomSlot {
  roomcode: string;
  startTime: string;
  finishTime: string;
  usageStatus?: string;
}

interface SummaryRow {
  roomcode: string;
  schedule_date: string;
  total_bookings: number;
  source: string;
  total_hours: number;
  slot_breakdown: string;
}

interface PersonCountEvent {
  kind: string;
  topic: string;
  room_no: string;
  count: number;
}

interface DashboardData {
  schedule_count: number;
  usage_count: number;
  all_rooms_count: number;
  free_rooms_count: number;
  list_empty_rooms: RoomSlot[];
  list_usage_rooms: RoomSlot[];
  sumary_hours: SummaryRow[];
}

// Fixed categorical order — never cycled/reassigned per re-render.
// Validated: scripts/validate_palette.js (dataviz skill) — all 6 checks pass at light+dark surfaces.
const CATEGORICAL = [
  "var(--chart-blue)", // blue
  "var(--chart-orange)", // orange
  "var(--chart-aqua)", // aqua
  "var(--chart-yellow)", // yellow
  "var(--chart-magenta)", // magenta
  "var(--chart-green)", // green
  "var(--chart-violet)", // violet
  "var(--chart-red)", // red (also doubles as "Other")
];

const data = ref<DashboardData | null>(null);
const loading = ref(true);
const errorMsg = ref("");
const now = ref(new Date());

// Live person_count events, one per room_no (distinct — newest reading replaces the old one).
const personCountEvents = ref<PersonCountEvent[]>([]);

// Look up the latest live count for a room directly off the distinct event list.
function personCountFor(roomcode: string): number | undefined {
  return personCountEvents.value.find((e) => e.room_no === roomcode)?.count;
}

let clockTimer: ReturnType<typeof setInterval> | null = null;
let refreshTimer: ReturnType<typeof setInterval> | null = null;
let personCountStreamSource: EventSource | null = null;

function subscribePersonCountStream() {
  const url = `${API_BASE}/mqtt-stream/subscribe/`;
  personCountStreamSource = new EventSource(url);
  personCountStreamSource.onmessage = (event) => {
    try {
      const parsed = JSON.parse(event.data);
      if (parsed?.kind === "person_count" && typeof parsed.room_no === "string" && typeof parsed.count === "number") {
        const evt: PersonCountEvent = parsed;
        const idx = personCountEvents.value.findIndex((e) => e.room_no === evt.room_no);
        if (idx >= 0) {
          personCountEvents.value[idx] = evt;
        } else {
          personCountEvents.value.push(evt);
        }

      }
    } catch {
      // ignore malformed SSE payload
    }
  };
  personCountStreamSource.onerror = () => {
    // browser auto-retries the SSE connection; nothing to do here
  };
}

function toMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

const nowMinutes = computed(() => now.value.getHours() * 60 + now.value.getMinutes());

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "2-digit" });
}

async function loadDashboard() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const res = await fetch(`${API_BASE}/schedule/get_rooms_dashboard/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data.value = await res.json();
  } catch (err) {
    errorMsg.value = `Failed to load dashboard: ${err}`;
  } finally {
    loading.value = false;
  }
}

// ---------------------------------------------------------------------------
// Top stat tiles
// ---------------------------------------------------------------------------
const allRoomsCount = computed(() => data.value?.all_rooms_count ?? 0);
const freeRoomsCount = computed(() => data.value?.free_rooms_count ?? 0);
const usageRoomsCount = computed(() => data.value?.usage_count ?? 0);
const scheduleCount = computed(() => data.value?.schedule_count ?? 0);

function pct(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0;
}

const freePct = computed(() => pct(freeRoomsCount.value, allRoomsCount.value));
const usagePct = computed(() => pct(usageRoomsCount.value, allRoomsCount.value));

// ---------------------------------------------------------------------------
// Per-room real-time status — derived by checking which slot (from
// list_empty_rooms / list_usage_rooms) contains the current time.
// ---------------------------------------------------------------------------
type RoomStatus = "free" | "busy" | "schedule_but_unuse" | "unknown";

interface RoomStatusInfo {
  roomcode: string;
  status: RoomStatus;
  until: string | null;
}

const statusLabel: Record<RoomStatus, string> = {
  free: "ว่าง",
  busy: "กำลังใช้งาน",
  schedule_but_unuse: "มีในตารางแต่ไม่มีการยืนยัน",
  unknown: "ไม่มีข้อมูล",
};

const roomStatuses = computed<RoomStatusInfo[]>(() => {
  const d = data.value;
  if (!d) return [];
  const codes = new Set<string>();
  d.list_empty_rooms.forEach((r) => codes.add(r.roomcode));
  d.list_usage_rooms.forEach((r) => codes.add(r.roomcode));

  return [...codes].sort().map((roomcode) => {
    const busySlot = d.list_usage_rooms.find(
      (r) =>
        r.roomcode === roomcode &&
        nowMinutes.value >= toMinutes(r.startTime) &&
        nowMinutes.value <= toMinutes(r.finishTime),
    );
    if (busySlot) {
      const statusNum = Number(busySlot.usageStatus);
      const status = !Number.isNaN(statusNum) && statusNum < 3 ? "schedule_but_unuse" : "busy";
      return { roomcode, status, until: busySlot.finishTime };
    }

    const freeSlot = d.list_empty_rooms.find((r) => r.roomcode === roomcode);
    if (freeSlot) return { roomcode, status: "free" as const, until: freeSlot.finishTime };

    return { roomcode, status: "unknown" as const, until: null };
  });
});

interface FreeRoomNow {
  roomcode: string;
  until: string;
}

const freeRoomsNow = computed<FreeRoomNow[]>(() =>
  (data.value?.list_empty_rooms ?? [])
    .filter((r) => nowMinutes.value >= toMinutes(r.startTime) && nowMinutes.value <= toMinutes(r.finishTime))
    .map((r) => ({ roomcode: r.roomcode, until: r.finishTime }))
    .sort((a, b) => a.roomcode.localeCompare(b.roomcode)),
);

// ---------------------------------------------------------------------------
// Today's occupied time slots — timeline panel
// ---------------------------------------------------------------------------
const todayUsageSorted = computed<RoomSlot[]>(() =>
  [...(data.value?.list_usage_rooms ?? [])].sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime)),
);

const roomColorMap = computed(() => {
  const rooms = [...new Set(todayUsageSorted.value.map((r) => r.roomcode))];
  const map = new Map<string, string>();
  rooms.forEach((room, i) => map.set(room, CATEGORICAL[Math.min(i, CATEGORICAL.length - 1)]));
  return map;
});

function isSlotActive(slot: RoomSlot): boolean {


  return nowMinutes.value >= toMinutes(slot.startTime) && nowMinutes.value <= toMinutes(slot.finishTime);
}

function isPendingUsage(slot: RoomSlot): boolean {
  const statusNum = Number(slot.usageStatus);
  return !Number.isNaN(statusNum) && statusNum < 3;
}

function usageStatusLabel(slot: RoomSlot): string {
  return isPendingUsage(slot) ? "มีในตารางแต่ไม่มีการยืนยัน" : "กำลังใช้งาน";
}

// ---------------------------------------------------------------------------
// Hours summary — trend by date + top rooms by booking count
// ---------------------------------------------------------------------------
interface DateHours {
  date: string;
  label: string;
  hours: number;
}

const hoursByDate = computed<DateHours[]>(() => {
  const totals = new Map<string, number>();
  for (const row of data.value?.sumary_hours ?? []) {
    const date = row.schedule_date.slice(0, 10);
    totals.set(date, (totals.get(date) ?? 0) + row.total_hours);
  }
  return [...totals.entries()]
    .map(([date, hours]) => ({ date, label: formatDateLabel(date), hours: Math.max(0, Math.round(hours * 10) / 10) }))
    .sort((a, b) => a.date.localeCompare(b.date));
});

const totalHoursAll = computed(
  () => Math.round((data.value?.sumary_hours ?? []).reduce((sum, r) => sum + Math.max(0, r.total_hours), 0) * 10) / 10,
);

interface TopRoom {
  roomcode: string;
  bookings: number;
}

const topRooms = computed<TopRoom[]>(() => {
  const totals = new Map<string, number>();
  for (const row of data.value?.sumary_hours ?? []) {
    totals.set(row.roomcode, (totals.get(row.roomcode) ?? 0) + row.total_bookings);
  }
  return [...totals.entries()]
    .map(([roomcode, bookings]) => ({ roomcode, bookings }))
    .sort((a, b) => b.bookings - a.bookings)
    .slice(0, 3);
});

const rankColors = ["var(--status-pending)", "var(--rank-silver)", "var(--rank-bronze)"];

// ---------------------------------------------------------------------------
// Sparkline geometry for hours-by-date trend
// ---------------------------------------------------------------------------
const SPARK_W = 220;
const SPARK_H = 56;

const sparkPoints = computed(() => {
  const rows = hoursByDate.value;
  if (rows.length === 0) return [];
  const max = Math.max(1, ...rows.map((r) => r.hours));
  const stepX = rows.length > 1 ? SPARK_W / (rows.length - 1) : 0;
  return rows.map((r, i) => ({
    ...r,
    x: rows.length > 1 ? i * stepX : SPARK_W / 2,
    y: SPARK_H - (r.hours / max) * (SPARK_H - 8) - 4,
  }));
});

const sparkPath = computed(() => sparkPoints.value.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.y}`).join(" "));

const sparkSummary = computed(() => {
  const points = sparkPoints.value;
  if (!points.length) return "ไม่มีข้อมูลแนวโน้มชั่วโมงการใช้งาน";

  const peak = points.reduce((max, point) => (point.hours > max.hours ? point : max), points[0]);
  const latest = points[points.length - 1];
  return `แนวโน้มชั่วโมงการใช้งานครอบคลุม ${points.length} วัน รวม ${totalHoursAll.value} ชั่วโมง สูงสุด ${peak.hours} ชั่วโมงในวันที่ ${peak.label} และข้อมูลล่าสุด ${latest.hours} ชั่วโมงในวันที่ ${latest.label}`;
});

function roomCardAriaLabel(room: RoomStatusInfo): string {
  const parts = [
    props.selectedRoomNo === room.roomcode ? `ห้อง ${room.roomcode} ที่เลือกอยู่` : `เลือกห้อง ${room.roomcode}`,
    `สถานะ${statusLabel[room.status]}`,
  ];
  const count = personCountFor(room.roomcode);
  if (count !== undefined) parts.push(`จำนวนผู้ใช้ ${count} คน`);
  if (room.until) parts.push(`${room.status === "busy" ? "สิ้นสุด" : "ว่างถึง"} ${room.until}`);
  return parts.join(", ");
}

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

const usageDonutSummary = computed(
  () => `การใช้ห้องวันนี้ ${usagePct.value}% จากทั้งหมด ${allRoomsCount.value} ห้อง กำลังใช้งาน ${usageRoomsCount.value} ห้อง`,
);

const summaryHoursLabel = computed(
  () => `ชั่วโมงใช้งานสะสม ${totalHoursAll.value} ชั่วโมง จากข้อมูลสรุป ${(data.value?.sumary_hours ?? []).length} รายการ`,
);

const topRoomsSummary = computed(() => {
  if (!topRooms.value.length) return "ไม่มีข้อมูลห้องยอดนิยม";
  return topRooms.value.map((room, index) => `อันดับ ${index + 1} ห้อง ${room.roomcode} จอง ${room.bookings} ครั้ง`).join(", ");
});

function showTooltip(evt: MouseEvent | FocusEvent, title: string, value: string) {
  const pointer = evt instanceof MouseEvent ? evt : null;
  tooltip.value = { visible: true, x: pointer?.clientX ?? 0, y: pointer?.clientY ?? 0, title, value };
}
function moveTooltip(evt: MouseEvent) {
  if (!tooltip.value.visible) return;
  tooltip.value.x = evt.clientX;
  tooltip.value.y = evt.clientY;
}
function hideTooltip() {
  tooltip.value.visible = false;
}

onMounted(() => {
  loadDashboard();
  clockTimer = setInterval(() => {
    now.value = new Date();
  }, 30_000);
  refreshTimer = setInterval(loadDashboard, 5 * 60_000);
  subscribePersonCountStream();
});

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer);
  if (refreshTimer) clearInterval(refreshTimer);
  personCountStreamSource?.close();
  personCountStreamSource = null;
});
</script>

<template>
  <div class="dash-root">
    <div v-if="errorMsg" class="error-box">{{ errorMsg }}</div>
    <div v-if="loading" class="muted loading-state">กำลังโหลด…</div>

    <template v-else-if="data">
      <!-- Top stat tiles -->
      <div class="stat-row top-stat-row">
        <div class="stat-tile" :aria-label="`ห้องทั้งหมด ${allRoomsCount} ห้อง`">
          <div class="stat-icon icon-blue" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 21h18" /><path d="M5 21V7l7-4 7 4v14" />
              <path d="M9 9h1M14 9h1M9 13h1M14 13h1M9 17h1M14 17h1" />
            </svg>
          </div>
          <div class="stat-body">
            <p class="stat-label">ห้องทั้งหมด</p>
            <p class="stat-value">{{ allRoomsCount }} <span class="stat-unit">ห้อง</span></p>
          </div>
        </div>

        <div class="stat-tile" :aria-label="`ห้องว่างตอนนี้ ${freeRoomsCount} ห้อง ${freePct}% ของทั้งหมด`">
          <div class="stat-icon icon-green" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" /><path d="M9 12l2 2 4-4" />
            </svg>
          </div>
          <div class="stat-body">
            <p class="stat-label">ห้องว่างตอนนี้</p>
            <p class="stat-value">{{ freeRoomsCount }} <span class="stat-unit">ห้อง</span></p>
            <p class="stat-sub sub-green">{{ freePct }}% ของทั้งหมด</p>
          </div>
        </div>

        <div class="stat-tile" :aria-label="`ห้องที่กำลังใช้งาน ${usageRoomsCount} ห้อง ${usagePct}% ของทั้งหมด`">
          <div class="stat-icon icon-violet" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M17 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div class="stat-body">
            <p class="stat-label">กำลังใช้งาน</p>
            <p class="stat-value">{{ usageRoomsCount }} <span class="stat-unit">ห้อง</span></p>
            <p class="stat-sub sub-red">{{ usagePct }}% ของทั้งหมด</p>
          </div>
        </div>

        <div class="stat-tile" :aria-label="`จองวันนี้ ${scheduleCount} รายการ`">
          <div class="stat-icon icon-orange" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
            </svg>
          </div>
          <div class="stat-body">
            <p class="stat-label">จองวันนี้</p>
            <p class="stat-value">{{ scheduleCount }} <span class="stat-unit">รายการ</span></p>
            <p class="stat-sub">ตลอดทั้งวัน</p>
          </div>
        </div>
      </div>

      <!-- Middle: real-time room status — full width -->
      <section class="panel">
        <div class="panel-head">
          <h2 class="panel-title">สถานะห้องแบบ Real-time</h2>
          <ul class="legend-inline">
            <li class="legend-free"><span class="dot dot-free" aria-hidden="true"></span>ว่าง</li>
            <li><span class="dot dot-busy" aria-hidden="true"></span>กำลังใช้งาน</li>
            <li><span class="dot dot-schedule_but_unuse" aria-hidden="true"></span>มีในตาราง-แต่ไม่มีการใช้งาน</li>
            <li><span class="dot dot-unknown" aria-hidden="true"></span>ไม่มีข้อมูล</li>
          </ul>
        </div>

        <div v-if="!roomStatuses.length" class="muted">ไม่มีข้อมูลห้อง</div>
        <div v-else class="room-card-grid" aria-label="รายการสถานะห้อง">
          <button
            v-for="r in roomStatuses"
            :key="r.roomcode"
            type="button"
            class="room-card"
            :class="[`status-${r.status}`, { selected: props.selectedRoomNo === r.roomcode }]"
            :aria-pressed="props.selectedRoomNo === r.roomcode"
            :aria-current="props.selectedRoomNo === r.roomcode ? 'true' : undefined"
            :aria-label="roomCardAriaLabel(r)"
            @click="emit('select-room', r.roomcode)"
          >
            <div class="room-card-top">
              <span class="room-code">{{ r.roomcode }}</span>
              <span class="dot" :class="`dot-${r.status}`" aria-hidden="true"></span>
            </div>
            <p class="room-status-label">{{ statusLabel[r.status] }}</p>
            <p v-if="personCountFor(r.roomcode) !== undefined" class="room-person-count">
              จำนวนผู้ใช้ {{ personCountFor(r.roomcode) }} คน
            </p>
            <p v-if="r.until" class="room-until">
              {{ r.status === "busy" ? "สิ้นสุด" : "ว่างถึง" }} {{ r.until }}
            </p>
          </button>
        </div>
      </section>

      <!-- Lower: free rooms list + today's timeline -->
      <div class="split-row">
        <section class="panel">
          <h2 class="panel-title">ห้องว่างตอนนี้</h2>
          <div v-if="!freeRoomsNow.length" class="muted">ไม่มีห้องว่างในขณะนี้</div>
          <ul v-else class="free-list">
            <li v-for="r in freeRoomsNow" :key="r.roomcode" class="free-row">
              <span class="dot dot-free" aria-hidden="true"></span>
              <span class="free-room">{{ r.roomcode }}</span>
              <span class="free-until">ว่างถึง {{ r.until }}</span>
              <button
                v-if="userStore.isLoggedIn"
                type="button"
                class="book-btn"
                @click="showBooking?.(undefined, r.until, r.roomcode)"
              >
                จองเลย
              </button>
            </li>
          </ul>
        </section>

        <section class="panel">
          <h2 class="panel-title">ช่วงเวลาที่ใช้งานวันนี้</h2>
          <div v-if="!todayUsageSorted.length" class="muted">ไม่มีการใช้งานวันนี้</div>
          <ul v-else class="timeline-list">
            <li
              v-for="(slot, i) in todayUsageSorted"
              :key="i"
              class="timeline-row"
              :class="{ active: isSlotActive(slot) }"
            >
              <span class="timeline-dot" :style="{ background: roomColorMap.get(slot.roomcode) ?? CATEGORICAL[0] }" aria-hidden="true"></span>
              <span class="timeline-time">{{ slot.startTime }}–{{ slot.finishTime }}</span>
              <span class="timeline-room">ห้อง {{ slot.roomcode }}</span>
              <span
                v-if="isSlotActive(slot)"
                class="active-badge"
                :class="isPendingUsage(slot) ? 'badge-pending' : 'badge-busy'"
              >{{ usageStatusLabel(slot) }}</span>
            </li>
          </ul>
        </section>
      </div>

      <!-- Bottom: usage stats -->
      <div class="stat-row bottom-row">
        <div class="card">
          <p class="card-title">การใช้ห้องวันนี้</p>
          <div class="donut-wrap" role="img" :aria-label="usageDonutSummary">
            <svg viewBox="0 0 100 100" class="donut-svg" aria-hidden="true">
              <circle cx="50" cy="50" r="42" class="donut-track" />
              <circle
                cx="50" cy="50" r="42" class="donut-fill"
                :style="{ strokeDasharray: `${usagePct * 2.639} 263.9` }"
              />
            </svg>
            <div class="donut-center">
              <span class="donut-pct">{{ usagePct }}%</span>
            </div>
          </div>
          <p class="hint">จาก {{ allRoomsCount }} ห้อง</p>
        </div>

        <div class="card">
          <p id="sparkline-summary" class="card-title">แนวโน้มชั่วโมงการใช้งาน</p>
          <p class="sr-only">{{ sparkSummary }}</p>
          <div v-if="!sparkPoints.length" class="muted">ไม่มีข้อมูล</div>
          <svg
            v-else
            viewBox="0 0 220 56"
            class="spark-svg"
            role="img"
            aria-labelledby="sparkline-summary"
            :aria-describedby="'sparkline-summary-text'"
            @pointerleave="hideTooltip"
          >
            <desc id="sparkline-summary-text">{{ sparkSummary }}</desc>
            <path :d="sparkPath" class="spark-line" />
            <circle
              v-for="p in sparkPoints"
              :key="p.date"
              :cx="p.x"
              :cy="p.y"
              r="3"
              class="spark-dot"
              tabindex="0"
              role="img"
              :aria-label="`${p.label}: ${p.hours} ชม.`"
              @pointermove="showTooltip($event, p.label, `${p.hours} ชม.`)"
              @focus="showTooltip($event, p.label, `${p.hours} ชม.`)"
              @blur="hideTooltip"
            />
          </svg>
        </div>

        <div class="card">
          <p class="card-title">ชั่วโมงใช้งานสะสม</p>
          <p class="big-number" :aria-label="summaryHoursLabel">{{ totalHoursAll }} <span class="stat-unit">ชม.</span></p>
          <p class="hint">จากข้อมูลสรุป {{ (data.sumary_hours ?? []).length }} รายการ</p>
        </div>

        <div class="card">
          <p class="card-title">Top 3 ห้องยอดนิยม</p>
          <div v-if="!topRooms.length" class="muted">ไม่มีข้อมูล</div>
          <p class="sr-only">{{ topRoomsSummary }}</p>
          <ul v-if="topRooms.length" class="rank-list" :aria-label="topRoomsSummary">
            <li v-for="(r, i) in topRooms" :key="r.roomcode" class="rank-row">
              <span class="rank-badge" :style="{ background: rankColors[i] }" aria-hidden="true">{{ i + 1 }}</span>
              <span class="rank-room">{{ r.roomcode }}</span>
              <span class="rank-value">จอง {{ r.bookings }} ครั้ง</span>
            </li>
          </ul>
        </div>
      </div>
    </template>

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

    <footer class="dash-footer">© 2026 NRRU SmartLab · IOT Room Manager</footer>
  </div>
</template>

<style scoped>
.dash-root {
  color-scheme: light;
  --surface-1: var(--dashboard-surface);
  --page-plane: var(--dashboard-page);
  --text-primary: var(--dashboard-text);
  --text-secondary: var(--dashboard-text-secondary);
  --text-muted: var(--dashboard-text-muted);
  --gridline: var(--dashboard-border);
  --series-1: var(--dashboard-accent);

  /* Ceiling for the scrolling lists. Starts at the old fixed 22rem on short
     screens and grows with the viewport, so a tall window shows more rows
     before the list falls back to its own inner scrollbar. */
  --list-max-height: clamp(8rem, calc(100vh - 42rem), 13rem);

  min-height: 0;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
  padding: 0rem 0rem;
  background: var(--page-plane);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  display: flex;
  flex-direction: column;
  gap: 0.58rem;
}

html[data-theme="dark"] .dash-root {
  color-scheme: dark;
}

.error-box {
  background: var(--pill-error-bg);
  color: var(--pill-error-text);
  border: 1px solid var(--dashboard-error-border);
  border-radius: 0.5rem;
  padding: 0.6rem 0.9rem;
  font-size: 0.85rem;
}

.muted {
  color: var(--text-muted);
  font-size: 0.85rem;
  padding: 0.5rem 0;
}
.loading-state {
  text-align: center;
  padding: 2rem 0;
}

/* ── Top / bottom stat rows ── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
}

.top-stat-row {
  margin-top: 0;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.stat-tile {
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 8px;
  padding: 0.46rem 0.62rem;
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  min-width: 0;
}

.stat-icon {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 0.55rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-icon svg {
  width: 18px;
  height: 18px;
}
.icon-blue   { background: color-mix(in srgb, var(--dashboard-accent) 16%, var(--surface-1)); color: var(--dashboard-accent); }
.icon-green  { background: color-mix(in srgb, var(--status-free) 16%, var(--surface-1)); color: var(--status-free); }
.icon-violet { background: color-mix(in srgb, var(--chart-violet) 16%, var(--surface-1)); color: var(--chart-violet); }
.icon-orange { background: color-mix(in srgb, var(--chart-orange) 16%, var(--surface-1)); color: var(--chart-orange); }

.stat-body { min-width: 0; }

.stat-label {
  font-size: 0.72rem;
  color: var(--text-secondary);
  margin: 0 0 0.15rem;
}

.stat-value {
  font-size: 1.22rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

.stat-unit {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.stat-sub {
  font-size: 0.66rem;
  color: var(--text-muted);
  margin: 0.2rem 0 0;
}
.sub-green { color: var(--status-free); font-weight: 600; }
.sub-red   { color: var(--status-busy); font-weight: 600; }

/* ── Panels ── */
.split-row {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
  gap: 0.58rem;
  align-items: start;
}

.panel {
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 8px;
  padding: 0.58rem 0.66rem;
  min-width: 0;
  box-sizing: border-box;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.45rem;
}

.panel-title {
  font-size: 0.86rem;
  font-weight: 700;
  margin: 0 0 0.45rem;
}
.panel-head .panel-title { margin: 0; }

.legend-inline {
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  font-size: 0.66rem;
  color: var(--text-secondary);
}
.legend-inline li {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.legend-inline li.legend-free {
  background: color-mix(in srgb, var(--status-free) 16%, var(--surface-1));
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-block;
}
.dot-free               { background: var(--status-free); }
.dot-busy               { background: var(--status-busy); }
.dot-schedule_but_unuse { background: var(--status-pending); }
.dot-unknown            { background: var(--status-unknown); }

/* ── Real-time room cards ── */
.room-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.38rem;
}

.room-card {
  appearance: none;
  width: 100%;
  background: var(--surface-1);
  color: inherit;
  font: inherit;
  text-align: left;
  border: 1px solid var(--gridline);
  border-radius: 8px;
  padding: 0.43rem 0.56rem;
  border-left: 1px solid var(--status-unknown);
  min-height: 3rem;
  min-width: 0;
  cursor: pointer;
  transition: box-shadow .15s, border-color .15s, background .15s;
}
.room-card:hover,
.room-card:focus-visible {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--series-1) 35%, transparent);
  outline: none;
}
.room-card.selected {
  border-color: var(--dashboard-accent);
  background: color-mix(in srgb, var(--dashboard-accent) 8%, var(--surface-1));
  box-shadow: inset 0 0 0 1px var(--dashboard-accent);
}
.room-card.status-free               { border-left-color: var(--status-free); }
.room-card.status-busy               { border-left-color: var(--status-busy); }
.room-card.status-schedule_but_unuse { border-left-color: var(--status-pending); }

.room-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.room-code {
  font-weight: 700;
  font-size: 0.78rem;
  min-width: 0;
  overflow-wrap: anywhere;
}

.room-status-label {
  font-size: 0.68rem;
  color: var(--text-secondary);
  margin: 0.18rem 0 0;
}

.room-person-count {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--series-1);
  margin: 0.15rem 0 0;
}

.room-until {
  font-size: 0.64rem;
  color: var(--text-muted);
  margin: 0.15rem 0 0;
  font-variant-numeric: tabular-nums;
}

/* ── Room status tile grid ── */
.room-tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 0.55rem;
}

.room-tile {
  border-radius: 0.55rem;
  padding: 0.55rem 0.5rem;
  text-align: center;
  background: color-mix(in srgb, var(--status-unknown) 12%, var(--surface-1));
  border: 1px solid color-mix(in srgb, var(--status-unknown) 30%, var(--gridline));
  cursor: pointer;
  transition: box-shadow .15s;
}
.room-tile:hover,
.room-tile:focus-visible {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--series-1) 35%, transparent);
  outline: none;
}
.room-tile.status-free {
  background: color-mix(in srgb, var(--status-free) 12%, var(--surface-1));
  border-color: color-mix(in srgb, var(--status-free) 35%, var(--gridline));
}
.room-tile.status-busy {
  background: color-mix(in srgb, var(--status-busy) 12%, var(--surface-1));
  border-color: color-mix(in srgb, var(--status-busy) 35%, var(--gridline));
}
.room-tile.status-schedule_but_unuse {
  background: color-mix(in srgb, var(--status-pending) 12%, var(--surface-1));
  border-color: color-mix(in srgb, var(--status-pending) 35%, var(--gridline));
}

.tile-code {
  display: block;
  font-weight: 700;
  font-size: 0.78rem;
}
.tile-label {
  display: block;
  font-size: 0.65rem;
  color: var(--text-secondary);
  margin-top: 0.15rem;
}

/* ── Free rooms list ── */
.free-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  max-height: var(--list-max-height);
  overflow-y: auto;
}

.free-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.45rem;
  padding: 0.28rem 0.45rem;
  border-radius: 0.42rem;
  border: 1px solid var(--gridline);
  font-size: 0.78rem;
}

.free-room { font-weight: 700; white-space: nowrap; }
.free-until {
  color: var(--text-secondary);
  font-size: 0.7rem;
  font-variant-numeric: tabular-nums;
}

.book-btn {
  border: 1px solid var(--series-1);
  color: var(--series-1);
  background: none;
  border-radius: 0.4rem;
  padding: 0.3rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 600;
  font-family: inherit;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
}
.book-btn:hover {
  background: color-mix(in srgb, var(--series-1) 10%, transparent);
}

/* ── Today's timeline ── */
.timeline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  max-height: var(--list-max-height);
  overflow-y: auto;
}

.timeline-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.45rem;
  padding: 0.28rem 0.45rem;
  border-radius: 0.42rem;
  border: 1px solid var(--gridline);
  font-size: 0.78rem;
}
.timeline-row.active {
  border-color: var(--series-1);
  background: color-mix(in srgb, var(--series-1) 8%, var(--surface-1));
}

.timeline-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.timeline-time {
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
  white-space: nowrap;
}

.timeline-room { font-weight: 600; }

.active-badge {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--brand-on-primary);
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
  white-space: nowrap;
}
.active-badge.badge-busy    { background: var(--status-busy); }
.active-badge.badge-pending { background: var(--status-pending); }

/* ── Bottom stat cards ── */
.card {
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
}

.card-title {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin: 0 0 0.4rem;
}

.hint {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin: 0.5rem 0 0;
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

.big-number {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

/* Donut */
.donut-wrap {
  position: relative;
  width: 58px;
  height: 58px;
  margin: 0 auto;
}
.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.donut-track {
  fill: none;
  stroke: var(--gridline);
  stroke-width: 10;
}
.donut-fill {
  fill: none;
  stroke: var(--series-1);
  stroke-width: 10;
  stroke-linecap: round;
  transition: stroke-dasharray 0.3s ease;
}
.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.donut-pct {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--series-1);
}

/* Sparkline */
.spark-svg {
  width: 100%;
  height: 42px;
  overflow: visible;
}
.spark-line {
  fill: none;
  stroke: var(--series-1);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.spark-dot {
  fill: var(--surface-1);
  stroke: var(--series-1);
  stroke-width: 2;
  cursor: pointer;
  outline: none;
}
.spark-dot:hover,
.spark-dot:focus-visible {
  fill: var(--series-1);
}

/* Rank list */
.rank-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.rank-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.rank-badge {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  color: var(--brand-on-primary);
  font-size: 0.7rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.rank-room {
  font-weight: 700;
  font-size: 0.82rem;
  flex: 1;
}
.rank-value {
  font-size: 0.75rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* Shared tooltip */
.viz-tooltip {
  position: fixed;
  z-index: 1000;
  pointer-events: none;
  background: var(--surface-1);
  border: 1px solid var(--gridline);
  border-radius: 0.4rem;
  padding: 0.45rem 0.6rem;
  box-shadow: var(--dashboard-tooltip-shadow);
}

.viz-tooltip-value {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--text-primary);
}

.viz-tooltip-title {
  margin-top: 0.1rem;
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.dash-footer {
  margin-top: 1.2rem;
  color: var(--text-muted);
  font-size: 0.72rem;
  text-align: center;
}

@media (max-width: 960px) {
  .stat-row,
  .split-row {
    grid-template-columns: 1fr;
  }

  .room-card-grid {
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  }
}

@media (max-width: 720px) {
  .top-stat-row,
  .bottom-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 430px) {
  .top-stat-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .bottom-row {
    grid-template-columns: 1fr;
  }

  .stat-tile {
    padding: 0.48rem 0.5rem;
    gap: 0.42rem;
  }

  .stat-icon {
    width: 28px;
    height: 28px;
  }

  .stat-value {
    font-size: 1rem;
  }

  .legend-inline {
    gap: 0.35rem;
  }

  .room-card-grid {
    grid-template-columns: repeat(auto-fit, minmax(8.25rem, 1fr));
  }

  .free-row,
  .timeline-row {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .free-room,
  .timeline-time {
    grid-column: 2;
  }

  .free-until,
  .timeline-room,
  .active-badge,
  .book-btn {
    grid-column: 1 / -1;
  }

  .book-btn {
    justify-self: start;
  }
}
</style>
