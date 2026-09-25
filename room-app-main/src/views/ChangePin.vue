<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import config from "../assets/config.json"

const API_BASE = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

const route       = useRoute()
const userName    = ref((route.query.user as string) ?? '')
const newPin      = ref('')
const confirmPin  = ref('')
const state       = ref<'idle' | 'loading' | 'ok' | 'fail'>('idle')
const message     = ref('')

async function changePin() {
  if (!userName.value || !newPin.value) return
  if (newPin.value.length < 6) {
    state.value   = 'fail'
    message.value = 'รหัสพินใหม่ต้องมีอย่างน้อย 6 หลัก'
    return
  }
  if (newPin.value !== confirmPin.value) {
    state.value   = 'fail'
    message.value = 'รหัสพินทั้งสองช่องไม่ตรงกัน'
    return
  }
  state.value   = 'loading'
  message.value = ''
  try {
    const params = new URLSearchParams({ new_pin: newPin.value })
    const res  = await fetch(`${API_BASE}/user_access/change_pin/${encodeURIComponent(userName.value)}?${params}`)
    const data = await res.json()
    if (data?.Flag) {
      state.value   = 'ok'
      message.value = 'เปลี่ยนรหัสพินสำเร็จ'
      newPin.value     = ''
      confirmPin.value = ''
    } else {
      state.value   = 'fail'
      message.value = data?.message || 'ไม่สามารถเปลี่ยนรหัสพินได้'
    }
  } catch (err) {
    state.value   = 'fail'
    message.value = `เกิดข้อผิดพลาด: ${err}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">เปลี่ยนรหัสพิน</p>
      <p class="sub">ตั้งรหัสพินใหม่สำหรับ <strong>{{ userName || 'บัญชีของคุณ' }}</strong></p>

      <label class="field-label" for="user-name">ชื่อผู้ใช้</label>
      <input
        id="user-name"
        v-model="userName"
        type="text"
        placeholder="ชื่อผู้ใช้"
        class="pwd-input full-input"
        :disabled="state === 'loading'"
      />

      <label class="field-label" for="new-pin">รหัสพินใหม่</label>
      <input
        id="new-pin"
        v-model="newPin"
        type="password"
        inputmode="numeric"
        pattern="[0-9]*"
        autocomplete="off"
        placeholder="รหัสพินใหม่"
        class="pwd-input full-input"
        :disabled="state === 'loading'"
        @input="newPin = newPin.replace(/\D/g, '')"
      />

      <label class="field-label" for="confirm-pin">ยืนยันรหัสพิน</label>
      <input
        id="confirm-pin"
        v-model="confirmPin"
        type="password"
        inputmode="numeric"
        pattern="[0-9]*"
        autocomplete="off"
        placeholder="ยืนยันรหัสพิน"
        class="pwd-input full-input"
        @keyup.enter="changePin"
        :disabled="state === 'loading'"
        @input="confirmPin = confirmPin.replace(/\D/g, '')"
      />

      <button
        class="btn btn-block"
        @click="changePin"
        :disabled="!userName || !newPin || !confirmPin || state === 'loading'"
      >
        {{ state === 'loading' ? 'กำลังบันทึก…' : 'เปลี่ยนรหัสพิน' }}
      </button>

      <div v-if="message" class="result" :class="state">
        <span class="dot"></span>{{ message }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 1rem;
  box-sizing: border-box;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  width: 100%;
  max-width: 420px;
  box-sizing: border-box;
}

.card-title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #64748b;
  margin-bottom: 1rem;
}

.sub { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.9rem; }
.sub strong { color: var(--text-primary); }

.field-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 0.3rem;
}

.full-input {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 0.9rem;
}

.pwd-input {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  font-size: 1rem;
  padding: 0.65rem 0.85rem;
  outline: none;
}
.pwd-input:focus { border-color: #3b82f6; }
.pwd-input:disabled { opacity: 0.5; }

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
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-block {
  width: 100%;
  padding: 0.7rem 1.1rem;
  font-size: 0.95rem;
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
.result .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.result.ok   { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid #22c55e; }
.result.ok   .dot { background: #22c55e; }
.result.fail { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid #ef4444; }
.result.fail .dot { background: #ef4444; }
</style>
