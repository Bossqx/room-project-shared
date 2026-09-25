<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../../stores/user'
import config from "../../assets/config.json"

const API_BASE = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

const route       = useRoute()
const userStore   = useUserStore()
const userName    = ref((route.query.user as string) || userStore.userName || '')
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
    <form class="card" @submit.prevent="changePin">
      <header class="form-header">
        <span class="header-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="5" y="10" width="14" height="10" rx="2" />
            <path stroke-linecap="round" d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2" />
          </svg>
        </span>
        <div>
          <h2>เปลี่ยนรหัสพิน</h2>
          <p>ตั้งรหัสใหม่เพื่อรักษาความปลอดภัยของบัญชี</p>
        </div>
      </header>

      <div class="account-summary">
        <span>บัญชีที่กำลังเปลี่ยนรหัส</span>
        <strong>{{ userName || 'บัญชีของคุณ' }}</strong>
      </div>

      <div class="form-field">
        <label class="field-label" for="user-name">ชื่อผู้ใช้</label>
        <input
          id="user-name"
          v-model="userName"
          type="text"
          autocomplete="username"
          placeholder="ชื่อผู้ใช้"
          class="pwd-input"
          :disabled="state === 'loading'"
        />
      </div>

      <div class="form-field">
        <label class="field-label" for="new-pin">รหัสพินใหม่</label>
        <input
          id="new-pin"
          v-model="newPin"
          type="password"
          inputmode="numeric"
          pattern="[0-9]*"
          autocomplete="new-password"
          placeholder="กรอกรหัสพินใหม่"
          class="pwd-input"
          :disabled="state === 'loading'"
          aria-describedby="pin-hint"
          @input="newPin = newPin.replace(/\D/g, '')"
        />
        <p id="pin-hint" class="field-hint">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path stroke-linecap="round" d="M12 10v6M12 7h.01" />
          </svg>
          ใช้ตัวเลขอย่างน้อย 6 หลัก
        </p>
      </div>

      <div class="form-field">
        <label class="field-label" for="confirm-pin">ยืนยันรหัสพินใหม่</label>
        <input
          id="confirm-pin"
          v-model="confirmPin"
          type="password"
          inputmode="numeric"
          pattern="[0-9]*"
          autocomplete="new-password"
          placeholder="กรอกรหัสพินอีกครั้ง"
          class="pwd-input"
          :disabled="state === 'loading'"
          @input="confirmPin = confirmPin.replace(/\D/g, '')"
        />
      </div>

      <div v-if="message" class="result" :class="state" role="status" aria-live="polite">
        <svg v-if="state === 'ok'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path stroke-linecap="round" stroke-linejoin="round" d="m8 12 2.5 2.5L16 9" />
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path stroke-linecap="round" d="M12 7v6M12 17h.01" />
        </svg>
        <span>{{ message }}</span>
      </div>

      <button
        class="btn btn-block"
        type="submit"
        :disabled="!userName || !newPin || !confirmPin || state === 'loading'"
      >
        <span v-if="state === 'loading'" class="spinner" aria-hidden="true"></span>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M13 6l6 6-6 6" />
        </svg>
        {{ state === 'loading' ? 'กำลังบันทึก…' : 'ยืนยันการเปลี่ยนรหัสพิน' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.page {
  width: 100%;
  background: transparent;
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.card {
  background: var(--bg-surface);
  border-radius: 1rem;
  padding: 1.75rem;
  width: 100%;
  box-sizing: border-box;
  box-shadow: var(--dashboard-shadow);
}

.form-header {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding-right: 2.4rem;
  margin-bottom: 1.25rem;
}

.header-icon {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex: 0 0 auto;
  border-radius: 0.8rem;
  background: var(--dashboard-accent-soft);
  color: var(--accent-link);
}

.header-icon svg { width: 1.35rem; height: 1.35rem; }

.form-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1.25rem;
  font-weight: 750;
  letter-spacing: -0.015em;
}

.form-header p {
  margin: 0.18rem 0 0;
  color: var(--text-secondary);
  font-size: 0.82rem;
  line-height: 1.45;
}

.account-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.2rem;
  padding: 0.72rem 0.85rem;
  border: 1px solid color-mix(in srgb, var(--accent-link) 20%, var(--border));
  border-radius: 0.65rem;
  background: var(--dashboard-accent-soft);
  font-size: 0.78rem;
}

.account-summary span { color: var(--text-secondary); }
.account-summary strong { color: var(--text-primary); font-size: 0.86rem; }

.form-field { margin-bottom: 0.95rem; }

.field-label {
  display: block;
  margin-bottom: 0.38rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 650;
}

.pwd-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--input-bg);
  border: 1px solid var(--border);
  border-radius: 0.65rem;
  color: var(--text-primary);
  font: inherit;
  font-size: 0.92rem;
  padding: 0.72rem 0.85rem;
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease, background .15s ease;
}

.pwd-input::placeholder { color: var(--text-muted); opacity: 0.82; }
.pwd-input:hover:not(:disabled) { border-color: color-mix(in srgb, var(--accent-link) 45%, var(--border)); }
.pwd-input:focus {
  border-color: var(--accent-link);
  background: var(--bg-surface);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-link) 16%, transparent);
}
.pwd-input:disabled { opacity: 0.5; }

.field-hint {
  display: flex;
  align-items: center;
  gap: 0.32rem;
  margin: 0.38rem 0 0;
  color: var(--text-muted);
  font-size: 0.72rem;
}

.field-hint svg { width: 0.85rem; height: 0.85rem; flex: 0 0 auto; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  background: var(--brand-primary);
  color: var(--brand-on-primary);
  border: none;
  border-radius: 0.65rem;
  padding: 0.75rem 1.1rem;
  font: inherit;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
}
.btn svg { width: 1rem; height: 1rem; }
.btn:hover:not(:disabled) { background: color-mix(in srgb, var(--brand-primary) 84%, #000); box-shadow: 0 5px 14px color-mix(in srgb, var(--brand-primary) 24%, transparent); }
.btn:active:not(:disabled) { transform: translateY(1px); }
.btn:focus-visible { outline: 3px solid color-mix(in srgb, var(--accent-link) 28%, transparent); outline-offset: 2px; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }

.btn-block {
  width: 100%;
  margin-top: 0.2rem;
}

.result {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.95rem;
  padding: 0.62rem 0.75rem;
  border-radius: 0.6rem;
  font-size: 0.8rem;
  font-weight: 650;
}
.result svg { width: 1rem; height: 1rem; flex: 0 0 auto; }
.result.ok   { background: var(--pill-success-bg); color: var(--pill-success-text); border: 1px solid var(--status-free); }
.result.fail { background: var(--pill-error-bg); color: var(--pill-error-text); border: 1px solid var(--status-busy); }

.spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid color-mix(in srgb, var(--brand-on-primary) 36%, transparent);
  border-top-color: var(--brand-on-primary);
  border-radius: 50%;
  animation: spin .65s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 520px) {
  .card { padding: 1.3rem; }
  .form-header { align-items: flex-start; padding-right: 2rem; }
  .account-summary { align-items: flex-start; flex-direction: column; gap: 0.15rem; }
}

@media (prefers-reduced-motion: reduce) {
  .btn,
  .pwd-input { transition: none; }
  .spinner { animation-duration: 1.2s; }
}
</style>
