<script setup lang="ts">
import { ref } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'https://cosai.nrru.ac.th:8000').replace(/\/$/, '')

const clearState = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const clearMsg    = ref('')

const form = ref({
  start_date: new Date().toISOString().slice(0, 10),
  end_date:   '',
  delta_day:  14,
})

const createState = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const createMsg    = ref('')

async function clearData() {
  clearState.value = 'loading'
  clearMsg.value   = ''
  try {
    const res  = await fetch(`${apiBase}/migration/remove_schedule/`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    clearState.value = 'done'
    clearMsg.value   = `Cleared successfully (${data?.affected_rows ?? 0} row(s) removed)`
  } catch (e) {
    clearState.value = 'error'
    clearMsg.value   = `Failed to clear data: ${e}`
  }
}

async function createSchedules() {
  if (!form.value.start_date || !form.value.end_date) return
  createState.value = 'loading'
  createMsg.value   = ''
  try {
    const params = new URLSearchParams({
      start_date: form.value.start_date,
      end_date:   form.value.end_date,
      delta_day:  String(form.value.delta_day),
    })
    const res = await fetch(`${apiBase}/migration/set_schedules/?${params}`, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    createState.value = 'done'
    createMsg.value   = `Created successfully (${data?.affected_rows ?? 0} row(s) inserted)`
  } catch (e) {
    createState.value = 'error'
    createMsg.value   = `Failed to create schedules: ${e}`
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <p class="card-title">Step 1 — Clear Schedule Data</p>
      <p class="hint">Removes all existing rows from the schedules table before migrating new data.</p>

      <button class="btn btn-danger" @click="clearData" :disabled="clearState === 'loading'">
        <span v-if="clearState === 'loading'" class="spinner"></span>
        {{ clearState === 'loading' ? 'Clearing…' : 'Clear Data' }}
      </button>

      <div v-if="clearMsg" class="msg" :class="clearState === 'error' ? 'error-box' : 'ok-box'">
        {{ clearMsg }}
      </div>
    </div>

    <div class="card">
      <p class="card-title">Step 2 — Create Schedules</p>
      <p class="hint">Fetches schedule data from the source system and repeats it forward to the end date.</p>

      <form class="form" @submit.prevent="createSchedules">
        <div class="field">
          <label class="lbl">Start Date</label>
          <input v-model="form.start_date" type="date" class="input" required />
        </div>

        <div class="field">
          <label class="lbl">End Date</label>
          <input v-model="form.end_date" type="date" class="input" required />
        </div>

        <div class="field" v-show="false">
          <label class="lbl">Delta Day</label>
          <input v-model.number="form.delta_day" type="number" min="1" class="input" />
        </div>

        <button class="btn" type="submit" :disabled="createState === 'loading'">
          <span v-if="createState === 'loading'" class="spinner"></span>
          {{ createState === 'loading' ? 'Creating…' : 'Create Schedules' }}
        </button>
      </form>

      <div v-if="createMsg" class="msg" :class="createState === 'error' ? 'error-box' : 'ok-box'">
        {{ createMsg }}
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
  padding: 1.25rem 1%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  width: 98%;
  margin: 0 auto;
  box-sizing: border-box;
}

.card-title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-link-hover);
  margin: 0 0 0.4rem;
}

.hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0 0 1rem;
}

.form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.85rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.lbl {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}

.input {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  color: var(--text-primary);
  padding: 0.5rem 0.7rem;
  font-size: 0.85rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: #2563eb;
  border: none;
  border-radius: 0.5rem;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.55rem 1.1rem;
  cursor: pointer;
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn:hover:not(:disabled) { background: #1d4ed8; }

.btn-danger { background: #dc2626; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; }

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg {
  margin-top: 1rem;
  font-size: 0.8rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.5rem;
}
.ok-box    { background: rgba(34,197,94,.12);  color: var(--pill-success-text); border: 1px solid rgba(34,197,94,.35); }
.error-box { background: rgba(239,68,68,.12);  color: var(--pill-error-text); border: 1px solid rgba(239,68,68,.35); }
</style>
