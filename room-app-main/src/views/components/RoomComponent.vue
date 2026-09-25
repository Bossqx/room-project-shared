<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import config from "../../assets/config.json";

const props = defineProps<{
  roomNo: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const apiBase = (config.apiRoute ?? "http://localhost:8000").replace(/\/$/, "");

interface Room {
  id?: number;
  room_no: string;
  panorama?: string | null;
  room_type?: string | null;
  floor_no?: number | null;
  building?: string | null;
  computer_no?: number | null;
  seat_no?: number | null;
}

interface FeatureItem {
  code: string;
  application?: string;
  accessory?: string;
  icon?: string;
  usage?: boolean;
}

interface ScheduleItem {
  schedule_id?: string | number;
  id?: string | number;
  roomcode: string;
  coursecode?: string;
  subject_code?: string;
  subject_name?: string;
  user_login?: string;
  user_name?: string;
  startTime: string;
  finishTime: string;
  schedule_date?: string;
  source?: string;
}

const room = ref<Room | null>(null);
const applications = ref<FeatureItem[]>([]);
const accessories = ref<FeatureItem[]>([]);
const schedules = ref<ScheduleItem[]>([]);
const state = ref<"idle" | "loading" | "error">("idle");
const errorMsg = ref("");
const now = ref(new Date());
let clockTimer: ReturnType<typeof setInterval> | null = null;

const today = new Date().toISOString().slice(0, 10);

const title = computed(() => room.value?.room_no ?? props.roomNo);

const facts = computed(() => [
  { label: "ประเภทห้อง", value: room.value?.room_type || "ไม่มีข้อมูล" },
  { label: "อาคาร", value: room.value?.building || "ไม่มีข้อมูล" },
  { label: "ชั้น", value: room.value?.floor_no ?? "ไม่มีข้อมูล" },
  { label: "จำนวนเครื่อง", value: room.value?.computer_no ?? "ไม่มีข้อมูล" },
  { label: "จำนวนที่นั่ง", value: room.value?.seat_no ?? "ไม่มีข้อมูล" },
]);

const activeApplications = computed(() =>
  applications.value.filter((item) => item.usage !== false),
);

const activeAccessories = computed(() =>
  accessories.value.filter((item) => item.usage !== false),
);

const orderedSchedules = computed(() =>
  [...schedules.value].sort((a, b) => a.startTime.localeCompare(b.startTime)),
);

function toMinutes(t: string): number {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

const nowMinutes = computed(() => now.value.getHours() * 60 + now.value.getMinutes());

const currentSchedule = computed(() =>
  orderedSchedules.value.find(
    (item) => nowMinutes.value >= toMinutes(item.startTime) && nowMinutes.value <= toMinutes(item.finishTime),
  ),
);

const roomStatus = computed(() => {
  const active = currentSchedule.value;
  if (!active) {
    return orderedSchedules.value.length
      ? { label: "มีตารางวันนี้", tone: "pending" }
      : { label: "ไม่มีตารางวันนี้", tone: "unknown" };
  }

  const status = Number((active as ScheduleItem & { usage_status?: string | number }).usage_status);
  if (!Number.isNaN(status) && status < 3) {
    return { label: "มีในตารางแต่ไม่มีการยืนยัน", tone: "pending" };
  }
  return { label: "กำลังใช้งาน", tone: "busy" };
});

const roomImageUrl = computed(() => {
  const value = room.value?.panorama?.trim();
  if (!value) return "";
  if (/^(https?:|data:|\/)/.test(value)) return value;
  return "";
});

const roomStatusSummary = computed(() => `ห้อง ${title.value} สถานะ${roomStatus.value.label}`);

function pickString(source: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return null;
}

function pickNumber(source: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "number") return value;
    if (typeof value === "string" && value.trim() && !Number.isNaN(Number(value))) return Number(value);
  }
  return null;
}

function normalizeRoom(raw: unknown): Room | null {
  if (!raw || typeof raw !== "object") return null;
  const source = raw as Record<string, unknown>;
  const roomNo = pickString(source, ["room_no", "roomNo", "room_code", "roomCode", "roomcode"]);
  if (!roomNo) return null;

  return {
    id: pickNumber(source, ["id"]) ?? undefined,
    room_no: roomNo,
    panorama: pickString(source, ["panorama"]),
    room_type: pickString(source, ["room_type", "roomType", "type"]),
    floor_no: pickNumber(source, ["floor_no", "floorNo", "floor"]),
    building: pickString(source, ["building", "building_name", "buildingName"]),
    computer_no: pickNumber(source, ["computer_no", "computerNo", "computers", "computer_count"]),
    seat_no: pickNumber(source, ["seat_no", "seatNo", "seats", "seat_count"]),
  };
}

function normalizeRoomList(payload: unknown): Room[] {
  const rows = Array.isArray(payload)
    ? payload
    : payload && typeof payload === "object" && Array.isArray((payload as { data?: unknown }).data)
      ? (payload as { data: unknown[] }).data
      : [];
  return rows.map(normalizeRoom).filter((item): item is Room => item !== null);
}

function sameRoom(a: string, b: string): boolean {
  return a.trim().toLowerCase() === b.trim().toLowerCase();
}

function itemLabel(item: FeatureItem): string {
  return (item.application ?? item.accessory ?? item.code ?? "").trim();
}

function scheduleTitle(item: ScheduleItem): string {
  return item.subject_name || item.coursecode || item.subject_code || "รายการจอง";
}

function scheduleOwner(item: ScheduleItem): string {
  return item.user_name || item.user_login || "";
}

async function fetchJson<T>(url: string, fallback: T): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data ?? fallback;
}

async function loadRoomDetails() {
  if (!props.roomNo) return;

  state.value = "loading";
  errorMsg.value = "";
  room.value = { room_no: props.roomNo };
  applications.value = [];
  accessories.value = [];
  schedules.value = [];

  try {
    const roomsPayload = await fetchJson<unknown>(`${apiBase}/room/get_all_rooms`, []);
    const rooms = normalizeRoomList(roomsPayload);
    room.value = rooms.find((item) => sameRoom(item.room_no, props.roomNo)) ?? {
      room_no: props.roomNo,
    };

    const [appResult, accessoryResult, scheduleResult] = await Promise.allSettled([
      fetchJson<FeatureItem[]>(
        `${apiBase}/application/get_list_application/?room_no=${encodeURIComponent(props.roomNo)}`,
        [],
      ),
      fetchJson<FeatureItem[]>(
        `${apiBase}/accessory/get_list_accessory/?room_no=${encodeURIComponent(props.roomNo)}`,
        [],
      ),
      fetchJson<ScheduleItem[]>(
        `${apiBase}/schedule/get_schedule_by_criteria_db/${encodeURIComponent(props.roomNo)}?schedule_date=${today}&source_type=all`,
        [],
      ),
    ]);

    if (appResult.status === "fulfilled") applications.value = appResult.value;
    if (accessoryResult.status === "fulfilled") accessories.value = accessoryResult.value;
    if (scheduleResult.status === "fulfilled") schedules.value = scheduleResult.value;

    state.value = "idle";
  } catch (err) {
    room.value = { room_no: props.roomNo };
    state.value = "error";
    errorMsg.value = `Failed to load room details: ${err}`;
  }
}

onMounted(() => {
  loadRoomDetails();
  clockTimer = setInterval(() => {
    now.value = new Date();
  }, 30_000);
});

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer);
});

watch(() => props.roomNo, loadRoomDetails);
</script>

<template>
  <section class="room-panel" aria-labelledby="selected-room-title" :aria-describedby="'selected-room-status'">
    <header class="room-header">
      <div>
        <h2 id="selected-room-title">{{ title }}</h2>
        <span id="selected-room-status" class="status-pill" :class="`tone-${roomStatus.tone}`" role="status">{{ roomStatusSummary }}</span>
      </div>
      <button class="close-btn" type="button" :aria-label="`ปิดรายละเอียดห้อง ${title}`" @click="emit('close')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      </button>
    </header>

    <div v-if="state === 'loading'" class="state-box" role="status">กำลังโหลดรายละเอียดห้อง...</div>
    <div v-else>
      <div v-if="state === 'error'" class="error-box" role="alert">{{ errorMsg }}</div>

      <div class="room-media" :class="{ empty: !roomImageUrl }">
        <img v-if="roomImageUrl" :src="roomImageUrl" :alt="`รูปห้อง ${title}`" />
        <span v-else>ไม่มีรูปห้องจากข้อมูลปัจจุบัน</span>
      </div>

      <div class="fact-grid">
        <div v-for="fact in facts" :key="fact.label" class="fact">
          <span>{{ fact.label }}</span>
          <strong>{{ fact.value }}</strong>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h3>ตารางวันนี้</h3>
          <span :aria-label="`มีตารางวันนี้ ${orderedSchedules.length} รายการ`">{{ orderedSchedules.length }}</span>
        </div>
        <div v-if="orderedSchedules.length" class="schedule-list">
          <article
            v-for="item in orderedSchedules"
            :key="`${item.schedule_id ?? item.id ?? item.startTime}-${item.finishTime}`"
            class="schedule-card"
          >
            <div class="time">{{ item.startTime }} - {{ item.finishTime }}</div>
            <div class="subject">{{ scheduleTitle(item) }}</div>
            <div v-if="scheduleOwner(item)" class="owner">{{ scheduleOwner(item) }}</div>
          </article>
        </div>
        <p v-else class="empty">ไม่มีตารางสำหรับห้องนี้วันนี้</p>
      </div>

      <div class="section">
        <div class="section-head">
          <h3>ซอฟต์แวร์</h3>
          <span :aria-label="`มีข้อมูลซอฟต์แวร์ ${activeApplications.length} รายการ`">{{ activeApplications.length }}</span>
        </div>
        <div v-if="activeApplications.length" class="chip-list">
          <span v-for="item in activeApplications" :key="item.code" class="chip">{{ itemLabel(item) }}</span>
        </div>
        <p v-else class="empty">ไม่มีข้อมูลซอฟต์แวร์</p>
      </div>

      <div class="section">
        <div class="section-head">
          <h3>อุปกรณ์</h3>
          <span :aria-label="`มีข้อมูลอุปกรณ์ ${activeAccessories.length} รายการ`">{{ activeAccessories.length }}</span>
        </div>
        <div v-if="activeAccessories.length" class="chip-list">
          <span v-for="item in activeAccessories" :key="item.code" class="chip">{{ itemLabel(item) }}</span>
        </div>
        <p v-else class="empty">ไม่มีข้อมูลอุปกรณ์</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.room-panel {
  height: auto;
  min-height: 0;
  max-width: 100%;
  background: var(--dashboard-surface);
  border: 1px solid var(--dashboard-border);
  border-radius: 8px;
  padding: 0.7rem;
  color: var(--dashboard-text-strong);
  box-sizing: border-box;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.room-header,
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

h2,
h3,
p {
  margin: 0;
}

h2 {
  font-size: 1.28rem;
  line-height: 1.1;
  margin-bottom: 0.35rem;
}

h3 {
  font-size: 0.86rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.16rem 0.5rem;
  font-size: 0.68rem;
  font-weight: 800;
}

.status-pill.tone-busy {
  background: var(--pill-error-bg);
  color: var(--pill-error-text);
}

.status-pill.tone-pending {
  background: var(--pill-warning-bg);
  color: var(--pill-warning-text);
}

.status-pill.tone-unknown {
  background: var(--dashboard-surface-muted);
  color: var(--dashboard-text-secondary);
}

.close-btn {
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid var(--dashboard-border-muted);
  border-radius: 999px;
  background: var(--dashboard-surface-raised);
  color: var(--dashboard-control-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.close-btn:focus-visible {
  outline: 2px solid var(--dashboard-accent);
  outline-offset: 2px;
}

.room-media {
  width: 100%;
  max-width: 100%;
  aspect-ratio: 16 / 9;
  margin-top: 0.62rem;
  max-height: 11.5rem;
  border: 1px solid var(--dashboard-border-soft);
  border-radius: 8px;
  overflow: hidden;
  background: var(--dashboard-surface-info);
}

.room-media img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.room-media.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--dashboard-text-muted);
  font-size: 0.76rem;
  text-align: center;
  padding: 0.8rem;
  box-sizing: border-box;
}

.close-btn svg {
  width: 1rem;
  height: 1rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}

.fact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.38rem;
  margin-top: 0.62rem;
}

.fact {
  border: 1px solid var(--dashboard-border-soft);
  border-radius: 8px;
  padding: 0.48rem;
  background: var(--dashboard-surface-raised);
  min-width: 0;
}

.fact span,
.owner,
.empty {
  color: var(--dashboard-text-subtle);
  font-size: 0.78rem;
}

.fact strong {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.88rem;
  overflow-wrap: anywhere;
}

.section {
  margin-top: 0.62rem;
  border-top: 1px solid var(--dashboard-border-soft);
  padding-top: 0.6rem;
}

.section-head span {
  min-width: 1.6rem;
  height: 1.6rem;
  border-radius: 999px;
  background: var(--dashboard-accent-soft);
  color: var(--dashboard-accent-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 800;
}

.schedule-list,
.chip-list {
  display: grid;
  gap: 0.35rem;
  margin-top: 0.45rem;
}

.schedule-card {
  border-left: 1px solid var(--dashboard-accent);
  border-radius: 8px;
  padding: 0.43rem 0.52rem;
  background: var(--dashboard-surface-info);
  min-width: 0;
}

.time {
  font-size: 0.78rem;
  color: var(--dashboard-accent-strong);
  font-weight: 800;
}

.subject {
  margin-top: 0.25rem;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.chip-list {
  grid-template-columns: repeat(auto-fit, minmax(6.5rem, 1fr));
}

.chip {
  min-height: 2rem;
  border-radius: 0.45rem;
  background: var(--dashboard-surface-muted);
  border: 1px solid var(--dashboard-border);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.32rem 0.55rem;
  font-size: 0.74rem;
  font-weight: 700;
  text-align: center;
  overflow-wrap: anywhere;
  min-width: 0;
}

.state-box,
.error-box,
.empty {
  margin-top: 1rem;
}

.state-box,
.error-box {
  border-radius: 8px;
  padding: 0.85rem;
  font-size: 0.85rem;
}

.state-box {
  background: var(--dashboard-surface-muted);
  color: var(--dashboard-text-soft);
}

.error-box {
  background: var(--dashboard-error-bg);
  color: var(--dashboard-error-text);
  border: 1px solid var(--dashboard-error-border);
}

@media (max-width: 520px) {
  .room-panel {
    padding: 0.65rem;
  }

  .room-media {
    max-height: none;
  }

  .room-header {
    align-items: flex-start;
  }

  h2 {
    font-size: 1.15rem;
  }

  .fact-grid {
    grid-template-columns: 1fr;
  }

  .chip-list {
    grid-template-columns: repeat(auto-fit, minmax(5.75rem, 1fr));
  }
}
</style>
