<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import config from "../assets/config.json";
// import type { RoomBinding } from "../types/roomBinding";
// import { useUserStore } from "../stores/user";

const API_BASE = (config.apiRoute ?? "https://cosai.nrru.ac.th:8000").replace(
  /\/$/,
  "",
);

interface ScheduleInfo {
  id: string;
  subject_code: string;
  room_code: string;
  weekday: string;
  start_time: string;
  finish_time: string;
  year_no: string;
  semester: string;
  date: string;
  user_login: string;
  isExist: boolean;
}

const route = useRoute();
const router = useRouter();
// const userStore = useUserStore();
const roomNo = (route.query.room as string) ?? "";
const rowId = (route.query.rowId as string) ?? "";
const objective = (route.query.objective as string) ?? "";
const schedule = ref<ScheduleInfo | null>(null);
const password = ref("");
const loadError = ref("");
const verifyState = ref<"idle" | "loading" | "ok" | "fail">("idle");
const verifyMsg = ref("");
const roomUsageId = ref<number | null>(null);
const cancelState = ref<"idle" | "loading">("idle");
const showCancel = ref(false);

const showChangePin = ref(false);
const newPin = ref("");
const changePinState = ref<"idle" | "loading" | "ok" | "fail">("idle");
const changePinMsg = ref("");

const alreadyConfirmedMsg = ref("");

// schedule_id is base64url("subject_code_room_code_weekday_start_time_finish_time_year_no_semester_date_user_login"),
// produced server-side (see schedule.py schedule_decode) — decode it locally instead of round-tripping to the API.
// function decodeScheduleId(id: string): ScheduleInfo | null {
//   try {
//     const b64 = id.replace(/-/g, "+").replace(/_/g, "/");
//     const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
//     const fields = atob(padded).split("_");
//     if (fields.length !== 9) return null;
//     const [subject_code, room_code, weekday, start_time, finish_time, year_no, semester, date, user_login] = fields;
//     return {
//       id,
//       subject_code,
//       room_code,
//       weekday,
//       start_time,
//       finish_time,
//       year_no,
//       semester,
//       date,
//       user_login,
//       isExist: false,
//     };
//   } catch {
//     return null;
//   }
// }

// Fallback for QR codes that carry a raw rowId (e.g. the AP-device flow)
// instead of the base64url schedule_id — looks the row up by id server-side.
async function fetchScheduleById(id: string): Promise<ScheduleInfo | null> {
  if (!rowId) return null;
  try {
    const sourceType = objective === "booking" ? "booking" : "schedule";
    const params = new URLSearchParams({ schedule_id: rowId, source_type: sourceType });
    const res = await fetch(`${API_BASE}/schedule/get_schedule_by_id/?${params}`);
    if (!res.ok) return null;
    const api = await res.json();
    return {
      id,
      subject_code: api.coursecode,
      room_code: api.roomcode,
      weekday: String(new Date(api.schedule_date).getDay()),
      start_time: api.startTime,
      finish_time: api.finishTime,
      year_no: api.yearNo,
      semester: api.semester,
      date: (api.schedule_date as string).slice(0, 10),
      user_login: api.userCode,
      isExist: false,
    };
  } catch {
    return null;
  }
}

async function checkUsageStatus(scheduleId: string, sourceType: string): Promise<number | null> {
  try {
    const params = new URLSearchParams({ schedule_id: scheduleId, source_type: sourceType });
    const res = await fetch(`${API_BASE}/schedule/check_usage_status/?${params}`);
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data?.usage_status === "number" ? data.usage_status : null;
  } catch {
    return null;
  }
}

onMounted(async () => {
  const id =
    (route.query.schedule_id as string) ?? (route.params.schedule_id as string) ?? "";
  //showCancel.value = route.query.flag === '1'

  // const decoded = id ? decodeScheduleId(id) : null;
  // if (decoded) {
  //   schedule.value = decoded;
  // } else {
  //   const fetched = await fetchScheduleById(id || rowId);
  //   if (!fetched) {
  //     loadError.value = id ? "Invalid schedule ID." : "No schedule_id provided.";
  //     return;
  //   }
  //   schedule.value = fetched;
  // }
  const fetched = await fetchScheduleById(id || rowId);
  if (!fetched) {
      loadError.value = id ? "Invalid schedule ID." : "No schedule_id provided.";
      return;
    }
    schedule.value = fetched;

  detectAllowCancel(schedule.value);

  if (rowId) {
    const sourceType = objective === "booking" ? "booking" : "schedule";
    const usageStatus = await checkUsageStatus(rowId, sourceType);
    if (usageStatus !== null && usageStatus >= 3) {
      alreadyConfirmedMsg.value = "ตารางเรียนนี้ได้รับการยืนยันไปแล้ว ไม่สามารถยืนยันซ้ำได้";
    }
  }
});

function detectAllowCancel(item: ScheduleInfo) {
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  const toMin = (t: string) => {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
  };
  const startMin = toMin(item.start_time);
  const finishMin = toMin(item.finish_time);

  const isActive = nowMinutes >= startMin && nowMinutes <= finishMin;
  const pastGrace = nowMinutes > startMin + 15;

  showCancel.value = isActive && pastGrace && item.isExist === false;
}

// async function generateUUID(
//   subjectCode: string,
//   userCode: string,
// ): Promise<string> {
//   const params = new URLSearchParams({
//     subject_code: subjectCode,
//     user_code: userCode,
//   });
//   const res = await fetch(`${API_BASE}/room-usage/generate_uuid/?${params}`);
//   const data = await res.json();
//   return data.uuid as string;
// }


async function increasePinCount(userName: string) {
  try {
    await fetch(
      `${API_BASE}/staff_access/increase_pin_count/${encodeURIComponent(userName)}`,
      { method: "GET" },
    );
  } catch {
    /* non-critical */
  }
}

async function checkPinCount(userName: string): Promise<boolean> {
  try {
    const res = await fetch(
      `${API_BASE}/staff_access/check_pin_count/${encodeURIComponent(userName)}`,
    );
    const data = await res.json();
    return data?.can_access !== false;
  } catch {
    return true; // check endpoint unreachable — don't block verify on it
  }
}




//control device by staff
// async function managebyAdminGet(roomCode: string) {
//   await fetch(
//     `${API_BASE}/send_2_device/admin_access_get/${encodeURIComponent(roomCode)}`,
//   );
// }

async function changeUsageStatus(): Promise<{ message: string }> {

  const url=objective==="schedule"?`${config.apiRoute}room-usage/set_status_schedules/${rowId}?usage_status=3`
  :`${config.apiRoute}room-usage/set_status_booking/${rowId}?usage_status=3`;
  
  //console.log(url);
  const res = await fetch(url);
  const data = await res.json();
  return data as { message: string };
}

//When request by aschedule
async function manageBySchedulePost(
  roomCode: string,
  subjectCode: string,
  userName: string,
  status: "on" | "off" = "on",
) {
  try {
    //Send to host server cosai.nrru.ac.th mq broker
    await fetch(`${API_BASE}/send_2_device/schedule_access_post/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        room_no: roomCode,
        status: status,
        subject_code: subjectCode,
        user_name: userName,
      }),
    });

    //await confirmDeviceByStaff(roomCode, "on");
  } catch {
    /* non-critical */
  }
}





async function addRoomUsage() {
  if (!schedule.value) return;
  const s = schedule.value;
  const url = `${API_BASE}/room-usage/add`;
  const payload = JSON.stringify({
    user_name: s.user_login,
    room_no: s.room_code,
    subject_code: s.subject_code,
    objective: "MIS Schedule",
    weekday: Number(s.weekday),
    start_time: s.start_time,
    finish_time: s.finish_time,
    year_no: s.year_no,
    semester: s.semester,
    uuid: route.query.uuid,
    created_date: new Date().toISOString(),
    usage_status: 1,
  });
  //console.log(payload);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
  });
  const data = await res.json();
  if (data.id) roomUsageId.value = data.id;
}

async function cancelBooking() {
  cancelState.value = "loading";
  if (roomUsageId.value !== null) {
    await fetch(`${API_BASE}/room-usage/delete/${roomUsageId.value}`, {
      method: "DELETE",
    });
    roomUsageId.value = null;
  }
  router.push("/");
}



async function notifyTogglePopup(roomCode: string, status: 'on' | 'off') {
  try {
    //console.log("Notify Room code ", roomCode, status);
    const url=`${API_BASE}/send_2_device/toggle_popup/${encodeURIComponent(roomCode)}?status=${status}`
    //console.log(url)
    await fetch(url)
  } catch { /* non-critical */ }
}

const PIN_MAX_LENGTH = 6;

function pressPasswordDigit(digit: string) {
  if (verifyState.value === "loading" || verifyState.value === "ok") return;
  if (password.value.length >= PIN_MAX_LENGTH) return;
  password.value += digit;
}

function backspacePassword() {
  if (verifyState.value === "loading" || verifyState.value === "ok") return;
  password.value = password.value.slice(0, -1);
}

function clearPassword() {
  if (verifyState.value === "loading" || verifyState.value === "ok") return;
  password.value = "";
}

function pressNewPinDigit(digit: string) {
  if (changePinState.value === "loading") return;
  if (newPin.value.length >= PIN_MAX_LENGTH) return;
  newPin.value += digit;
}

function backspaceNewPin() {
  if (changePinState.value === "loading") return;
  newPin.value = newPin.value.slice(0, -1);
}

function clearNewPin() {
  if (changePinState.value === "loading") return;
  newPin.value = "";
}

async function verify() {
  if (alreadyConfirmedMsg.value) return;
  if (!schedule.value) {
    const params = new URLSearchParams({
      user_name: "staff",
      pwd: password.value,
    });

    const res = await fetch(`${API_BASE}/room-usage/verify_access?${params}`);
    const data = await res.json();

    if (data.access === true) {
      //await managebyAdminGet(roomNo);
      await notifyTogglePopup(roomNo, "on");
      await changeUsageStatus();
      verifyState.value = "ok";
      verifyMsg.value = "Access granted";
    } else {
      verifyState.value = "fail";
      verifyMsg.value = "Incorrect password";
    }
    return;
  }
  const s = schedule.value;
  verifyState.value = "loading";
  verifyMsg.value = "";

  const canAccess = await checkPinCount(s.user_login);
  if (!canAccess) {
    verifyState.value = "fail";
    verifyMsg.value =
      "Too many failed attempts — access locked. Please change your PIN below.";
    //showChangePin.value = true
    return;
  }

  try {
    const scheduleId = route.query.schedule_id;
    const isValidScheduleId =
      typeof scheduleId === "string" && scheduleId.length > 0;

    if (isValidScheduleId) {
      const params = new URLSearchParams({
        user_name: s.user_login,
        pwd: password.value,
      });

      const res = await fetch(`${API_BASE}/room-usage/verify_access?${params}`);
      const data = await res.json();
      if (data.access === true) {
        await addRoomUsage();
        await changeUsageStatus();
        //Confirm open room by staff
        await manageBySchedulePost(s.room_code, s.subject_code, s.user_login);
        await increasePinCount(s.user_login);
        await notifyTogglePopup(s.room_code, "on");

        verifyState.value = "ok";
        verifyMsg.value = "Access granted";
      } else {
        verifyState.value = "fail";
        verifyMsg.value = "Incorrect password";
      }

    }
  } catch (err) {
    verifyState.value = "fail";
    verifyMsg.value = `Error: ${err}`;
  }
}

async function changePin() {
  if (!schedule.value || !newPin.value) return;
  changePinState.value = "loading";
  changePinMsg.value = "";
  try {
    const params = new URLSearchParams({ new_pin: newPin.value });
    const url= `${API_BASE}/user_access/change_pin/${encodeURIComponent(schedule.value.user_login)}?${params}`
    const res = await fetch(
      url
    );
    const data = await res.json();
    if (data?.Flag) {
      changePinState.value = "ok";
      changePinMsg.value = "PIN changed. You can verify again.";
      showChangePin.value = false;
      newPin.value = "";
      verifyState.value = "idle";
      verifyMsg.value = "";
    } else {
      changePinState.value = "fail";
      changePinMsg.value = "Failed to change PIN";
    }
  } catch (err) {
    changePinState.value = "fail";
    changePinMsg.value = `Error: ${err}`;
  }
}
</script>

<template>
  <div class="page">
    <!-- Loading error -->
    <div v-if="loadError" class="error-box">{{ loadError }}</div>

    <!-- Loading -->
    <div v-else-if="!schedule" class="center-msg">Loading schedule…</div>

    <template v-else>
      <!-- Schedule info card -->
      <div class="card">
        <p class="card-title">Schedule Confirmation</p>

        <div class="info-grid">
          <span class="lbl">Subject</span>
          <span class="val mono">{{ schedule.subject_code }}</span>

          <span class="lbl">Room</span>
          <span class="val mono">{{ schedule.room_code }}</span>

          <span class="lbl">Time</span>
          <span class="val mono"
            >{{ schedule.start_time }} – {{ schedule.finish_time }}</span
          >

          <span class="lbl">Date</span>
          <span class="val mono">{{ schedule.date }}</span>

          <span class="lbl">Semester</span>
          <span class="val mono"
            >{{ schedule.year_no }} / {{ schedule.semester }}</span
          >

          <span class="lbl">Instructor</span>
          <span class="val mono">{{ schedule.user_login }}</span>
        </div>
      </div>

      <!-- Password verify card -->
      <div class="card">
        <p class="card-title">Verify Access</p>
        <p class="sub">
          Enter password for <strong>{{ schedule.user_login }}</strong>
        </p>

        <p v-if="alreadyConfirmedMsg" class="already-confirmed-alert">
          {{ alreadyConfirmedMsg }}
        </p>

        <div class="pin-display" role="status" aria-label="PIN entered">
          <span
            v-for="i in PIN_MAX_LENGTH"
            :key="i"
            class="pin-dot"
            :class="{ filled: i <= password.length }"
          ></span>
        </div>

        <div class="keypad">
          <button
            v-for="n in 9"
            :key="n"
            type="button"
            class="key"
            :disabled="verifyState === 'loading' || verifyState === 'ok' || !!alreadyConfirmedMsg"
            @click="pressPasswordDigit(String(n))"
          >{{ n }}</button>
          <button type="button" class="key key-aux" :disabled="verifyState === 'loading' || verifyState === 'ok' || !!alreadyConfirmedMsg" @click="clearPassword">Clear</button>
          <button type="button" class="key" :disabled="verifyState === 'loading' || verifyState === 'ok' || !!alreadyConfirmedMsg" @click="pressPasswordDigit('0')">0</button>
          <button type="button" class="key key-aux" aria-label="Backspace" :disabled="verifyState === 'loading' || verifyState === 'ok' || !!alreadyConfirmedMsg" @click="backspacePassword">⌫</button>
        </div>

        <button
          class="btn btn-confirm"
          @click="verify"
          :disabled="!password || verifyState === 'loading' || verifyState === 'ok' || !!alreadyConfirmedMsg"
        >
          {{ verifyState === "loading" ? "Checking…" : "Verify" }}
        </button>

        <div v-if="verifyMsg" class="result" :class="verifyState">
          <span class="dot"></span>{{ verifyMsg }}
        </div>
      </div>

      <!-- Change PIN card (shown after lockout) -->
      <div v-if="showChangePin" class="card">
        <p class="card-title">Change PIN</p>
        <p class="sub">
          Set a new PIN for <strong>{{ schedule.user_login }}</strong>
        </p>

        <div class="pin-display" role="status" aria-label="New PIN entered">
          <span
            v-for="i in PIN_MAX_LENGTH"
            :key="i"
            class="pin-dot"
            :class="{ filled: i <= newPin.length }"
          ></span>
        </div>

        <div class="keypad">
          <button
            v-for="n in 9"
            :key="n"
            type="button"
            class="key"
            :disabled="changePinState === 'loading'"
            @click="pressNewPinDigit(String(n))"
          >{{ n }}</button>
          <button type="button" class="key key-aux" :disabled="changePinState === 'loading'" @click="clearNewPin">Clear</button>
          <button type="button" class="key" :disabled="changePinState === 'loading'" @click="pressNewPinDigit('0')">0</button>
          <button type="button" class="key key-aux" aria-label="Backspace" :disabled="changePinState === 'loading'" @click="backspaceNewPin">⌫</button>
        </div>

        <button
          class="btn btn-confirm"
          @click="changePin"
          :disabled="!newPin || changePinState === 'loading'"
        >
          {{ changePinState === "loading" ? "Saving…" : "Change PIN" }}
        </button>

        <div v-if="changePinMsg" class="result" :class="changePinState">
          <span class="dot"></span>{{ changePinMsg }}
        </div>
      </div>

      <button
        v-if="showCancel"
        class="btn btn-cancel"
        @click="cancelBooking"
        :disabled="cancelState === 'loading'"
      >
        {{ verifyState === "ok" ? "New Booking" : "New booking" }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #0f172a;
  color: #f1f5f9;
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 2rem;
  gap: 1rem;
}

.card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 1rem;
  padding: 1.5rem;
  width: 100%;
  max-width: 480px;
}

.card-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin-bottom: 1rem;
}

.info-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.45rem 1rem;
  align-items: baseline;
}
.lbl {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.val {
  font-size: 0.95rem;
  font-weight: 600;
  color: #f1f5f9;
}
.mono {
  font-family: monospace;
}

.sub {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 0.9rem;
}
.sub strong {
  color: #f1f5f9;
}

.pin-display {
  display: flex;
  justify-content: center;
  gap: 0.85rem;
  margin: 0.4rem 0 1.1rem;
}
.pin-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid #334155;
  background: transparent;
  transition: background .12s, border-color .12s;
}
.pin-dot.filled {
  background: #3b82f6;
  border-color: #3b82f6;
}

.keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.6rem;
  margin-bottom: 1rem;
}
.key {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 0.6rem;
  color: #f1f5f9;
  font-size: 1.3rem;
  font-weight: 600;
  padding: 0.85rem 0;
  cursor: pointer;
  transition: background .12s, border-color .12s;
}
.key:hover:not(:disabled) { background: #263449; border-color: #475569; }
.key:active:not(:disabled) { background: #334155; }
.key:disabled { opacity: 0.4; cursor: not-allowed; }
.key-aux { font-size: 0.85rem; color: #94a3b8; }

.btn-confirm { width: 100%; }

.btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 0.5rem;
  padding: 0.55rem 1.1rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-cancel {
  background: transparent;
  border: 1px solid #ef4444;
  color: #ef4444;
  width: 100%;
  max-width: 480px;
}

.result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.9rem;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
}
.result .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.result.ok {
  background: #052e16;
  color: #4ade80;
  border: 1px solid #22c55e;
}
.result.ok .dot {
  background: #22c55e;
}
.result.fail {
  background: #450a0a;
  color: #f87171;
  border: 1px solid #ef4444;
}
.result.fail .dot {
  background: #ef4444;
}
.error-box {
  background: #450a0a;
  color: #f87171;
  border: 1px solid #ef4444;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
  max-width: 480px;
  width: 100%;
}
.already-confirmed-alert {
  background: #422006;
  color: #fbbf24;
  border: 1px solid #f59e0b;
  border-radius: 0.5rem;
  padding: 0.65rem 0.9rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  font-weight: 700;
  text-align: center;
}
.center-msg {
  color: #64748b;
}
</style>
