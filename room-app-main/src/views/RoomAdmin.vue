<script setup lang="ts">
import { ref, onMounted } from 'vue'
import config from '../assets/config.json'

const apiBase = (config.apiRoute ?? 'http://localhost:8000').replace(/\/$/, '')

interface RoomImage {
  image: string
}

interface Room {
  id: number
  room_no: string
  panorama: string | null
  room_type: string | null
  floor_no: number | null
  building: string | null
  computer_no: number | null
  seat_no: number | null
  images?: RoomImage[]
}

const rooms      = ref<Room[]>([])
const listState  = ref<'idle' | 'loading' | 'error'>('idle')
const listErrMsg = ref('')
const imageVersion = ref(0)
const previewImage = ref<{ src: string; alt: string } | null>(null)
const deletingImagePath = ref<string | null>(null)
const imageDeleteState = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const imageDeleteMessage = ref('')
const imageManagerRoom = ref<Room | null>(null)
const deletingPanoramaRoom = ref<string | null>(null)
const panoramaDeleteState = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const panoramaDeleteMessage = ref('')

function panoramaUrl(room: Room): string {
  return `${apiBase}/room/get_panorama/${encodeURIComponent(room.room_no)}?v=${imageVersion.value}`
}

function roomImageUrl(imagePath: string): string {
  return `${apiBase}/room/get_room_image/${encodeURIComponent(imagePath)}?v=${imageVersion.value}`
}

function openImagePreview(src: string, alt: string) {
  previewImage.value = { src, alt }
}

function closeImagePreview() {
  previewImage.value = null
}

function openImageManager(room: Room) {
  imageManagerRoom.value = room
  imageUploadState.value = 'idle'
  imageErrMsg.value = ''
  imageDeleteState.value = 'idle'
  imageDeleteMessage.value = ''
  panoramaDeleteState.value = 'idle'
  panoramaDeleteMessage.value = ''
}

function closeImageManager() {
  if (deletingImagePath.value !== null || deletingPanoramaRoom.value !== null || imageUploadState.value === 'loading') return
  imageManagerRoom.value = null
}

async function deleteRoomImage(room: Room, item: RoomImage, index: number) {
  if (deletingImagePath.value !== null) return
  if (!confirm(`ลบภาพที่ ${index + 1} ของห้อง ${room.room_no} หรือไม่?\nเมื่อลบแล้วจะกู้คืนไม่ได้`)) return

  deletingImagePath.value = item.image
  imageDeleteState.value = 'loading'
  imageDeleteMessage.value = ''

  try {
    const res = await fetch(`${apiBase}/room/delete_image/${encodeURIComponent(item.image)}`, {
      method: 'DELETE',
    })

    if (!res.ok) {
      if (res.status === 404 || res.status === 405) {
        throw new Error('เซิร์ฟเวอร์ยังไม่รองรับ API สำหรับลบรูป')
      }
      throw new Error(`เซิร์ฟเวอร์ตอบกลับ HTTP ${res.status}`)
    }

    room.images = room.images?.filter(image => image.image !== item.image) ?? []
    imageVersion.value += 1
    imageDeleteState.value = 'done'
    imageDeleteMessage.value = `ลบภาพที่ ${index + 1} ของห้อง ${room.room_no} แล้ว`
  } catch (e) {
    imageDeleteState.value = 'error'
    imageDeleteMessage.value = e instanceof Error ? e.message : 'ไม่สามารถลบรูปได้ กรุณาลองใหม่'
  } finally {
    deletingImagePath.value = null
  }
}

async function deletePanorama(room: Room) {
  if (deletingPanoramaRoom.value !== null) return
  if (!confirm(`ลบ Panorama ของห้อง ${room.room_no} หรือไม่?\nเมื่อลบแล้วจะกู้คืนไม่ได้`)) return

  deletingPanoramaRoom.value = room.room_no
  panoramaDeleteState.value = 'loading'
  panoramaDeleteMessage.value = ''

  try {
    const res = await fetch(`${apiBase}/room/delete_panorama/${encodeURIComponent(room.room_no)}`, {
      method: 'DELETE',
    })

    if (!res.ok) {
      if (res.status === 404 || res.status === 405) {
        throw new Error('เซิร์ฟเวอร์ยังไม่รองรับ API สำหรับลบ Panorama')
      }
      throw new Error(`เซิร์ฟเวอร์ตอบกลับ HTTP ${res.status}`)
    }

    room.panorama = null
    imageVersion.value += 1
    panoramaDeleteState.value = 'done'
    panoramaDeleteMessage.value = `ลบ Panorama ของห้อง ${room.room_no} แล้ว`
  } catch (e) {
    panoramaDeleteState.value = 'error'
    panoramaDeleteMessage.value = e instanceof Error ? e.message : 'ไม่สามารถลบ Panorama ได้ กรุณาลองใหม่'
  } finally {
    deletingPanoramaRoom.value = null
  }
}

async function fetchRooms() {
  listState.value  = 'loading'
  listErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/room/get_all_rooms`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const roomList: Room[] = await res.json()
    rooms.value = await Promise.all(roomList.map(async room => {
      try {
        const detailRes = await fetch(`${apiBase}/room/get_room/${encodeURIComponent(room.room_no)}`)
        if (!detailRes.ok) return { ...room, images: [] }
        const detail = await detailRes.json() as Room
        return { ...room, ...detail, images: Array.isArray(detail.images) ? detail.images : [] }
      } catch {
        return { ...room, images: [] }
      }
    }))
    listState.value = 'idle'
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to load rooms: ${e}`
  }
}

onMounted(fetchRooms)

// ---------------------------------------------------------------------------
// Add / edit room modal
// ---------------------------------------------------------------------------
const showFormModal = ref(false)
const formMode       = ref<'add' | 'edit'>('add')
const editingId       = ref<number | null>(null)
const formState       = ref<'idle' | 'loading' | 'error'>('idle')
const formErrMsg      = ref('')

const emptyForm = () => ({
  room_no:     '',
  panorama:    '',
  room_type:   '',
  floor_no:    0,
  building:    '',
  computer_no: 0,
  seat_no:     0,
})

const form = ref(emptyForm())

function openAddModal() {
  formMode.value  = 'add'
  editingId.value = null
  form.value      = emptyForm()
  formState.value  = 'idle'
  formErrMsg.value = ''
  showFormModal.value = true
}

function openEditModal(room: Room) {
  formMode.value  = 'edit'
  editingId.value = room.id
  form.value = {
    room_no:     room.room_no ?? '',
    panorama:    room.panorama ?? '',
    room_type:   room.room_type ?? '',
    floor_no:    room.floor_no ?? 0,
    building:    room.building ?? '',
    computer_no: room.computer_no ?? 0,
    seat_no:     room.seat_no ?? 0,
  }
  formState.value  = 'idle'
  formErrMsg.value = ''
  showFormModal.value = true
}

function closeFormModal() {
  showFormModal.value = false
}

async function submitForm() {
  if (!form.value.room_no) return
  formState.value  = 'loading'
  formErrMsg.value = ''

  const now = new Date().toISOString()
  const payload = {
    room_no:     form.value.room_no,
    panorama:    form.value.panorama,
    room_type:   form.value.room_type,
    floor_no:    Number(form.value.floor_no) || 0,
    building:    form.value.building,
    computer_no: Number(form.value.computer_no) || 0,
    seat_no:     Number(form.value.seat_no) || 0,
    created_at:  now,
    updated_at:  now,
  }

  try {
    const url    = formMode.value === 'add' ? `${apiBase}/room/add` : `${apiBase}/room/update/${editingId.value}`
    const method = formMode.value === 'add' ? 'POST' : 'PUT'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    showFormModal.value = false
    await fetchRooms()
  } catch (e) {
    formState.value  = 'error'
    formErrMsg.value = `Failed to save room: ${e}`
  }
}

// ---------------------------------------------------------------------------
// Delete room
// ---------------------------------------------------------------------------
const deletingId = ref<number | null>(null)

async function deleteRoom(room: Room) {
  if (deletingId.value !== null) return
  if (!confirm(`Delete room ${room.room_no}? This cannot be undone.`)) return
  deletingId.value = room.id
  try {
    const res = await fetch(`${apiBase}/room/delete/${room.id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    await fetchRooms()
  } catch (e) {
    listState.value  = 'error'
    listErrMsg.value = `Failed to delete room: ${e}`
  } finally {
    deletingId.value = null
  }
}

// ---------------------------------------------------------------------------
// Upload panorama — popup + dropzone
// ---------------------------------------------------------------------------
const showPanoModal = ref(false)
const panoRoom       = ref<Room | null>(null)
const panoDragOver    = ref(false)
const panoState       = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const panoErrMsg      = ref('')
const panoFileInput   = ref<HTMLInputElement | null>(null)

function openPanoModal(room: Room) {
  panoRoom.value    = room
  panoDragOver.value = false
  panoState.value    = 'idle'
  panoErrMsg.value   = ''
  showPanoModal.value = true
}

function closePanoModal() {
  showPanoModal.value = false
}

function onPanoDragOver(e: DragEvent) {
  e.preventDefault()
  panoDragOver.value = true
}

function onPanoDragLeave() {
  panoDragOver.value = false
}

function onPanoDrop(e: DragEvent) {
  e.preventDefault()
  panoDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadPanoramaFile(file)
}

function onPanoBrowse() {
  panoFileInput.value?.click()
}

function onPanoFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) uploadPanoramaFile(file)
}

async function uploadPanoramaFile(file: File) {
  if (!panoRoom.value) return
  const roomNo = panoRoom.value.room_no
  if (!/\.(png|jpe?g)$/i.test(file.name)) {
    panoState.value  = 'error'
    panoErrMsg.value = 'Only PNG and JPG files are allowed.'
    return
  }

  panoState.value  = 'loading'
  panoErrMsg.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    const res = await fetch(`${apiBase}/room/upload_panorama/${roomNo}`, {
      method: 'POST',
      body,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    panoState.value = 'done'
    imageVersion.value += 1
    await fetchRooms()
    if (imageManagerRoom.value?.room_no === roomNo) {
      imageManagerRoom.value = rooms.value.find(room => room.room_no === roomNo) ?? null
    }
    setTimeout(() => { showPanoModal.value = false }, 700)
  } catch (e) {
    panoState.value  = 'error'
    panoErrMsg.value = `Failed to upload panorama: ${e}`
  }
}

// ---------------------------------------------------------------------------
// Upload a single room image
// ---------------------------------------------------------------------------
const imageFileInput   = ref<HTMLInputElement | null>(null)
const imageTargetRoom  = ref<string | null>(null)
const imageUploadState = ref<'idle' | 'loading' | 'error' | 'done'>('idle')
const imageErrMsg      = ref('')

function triggerImageUpload(room: Room) {
  imageTargetRoom.value  = room.room_no
  imageUploadState.value = 'idle'
  imageErrMsg.value      = ''
  imageFileInput.value?.click()
}

async function onImageFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file  = input.files?.[0]
  const roomNo = imageTargetRoom.value
  input.value = ''
  if (!file || !roomNo) return

  if (!/\.(png|jpe?g)$/i.test(file.name)) {
    imageUploadState.value = 'error'
    imageErrMsg.value      = 'Only PNG and JPG files are allowed.'
    return
  }

  imageUploadState.value = 'loading'
  imageErrMsg.value      = ''
  try {
    const body = new FormData()
    body.append('file', file)
    const res = await fetch(`${apiBase}/room/upload_image/${roomNo}`, {
      method: 'POST',
      body,
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    imageUploadState.value = 'done'
    imageVersion.value += 1
    await fetchRooms()
    if (imageManagerRoom.value?.room_no === roomNo) {
      imageManagerRoom.value = rooms.value.find(room => room.room_no === roomNo) ?? null
    }
  } catch (e) {
    imageUploadState.value = 'error'
    imageErrMsg.value      = `Failed to upload image for ${roomNo}: ${e}`
  } finally {
    imageTargetRoom.value = null
  }
}

// ---------------------------------------------------------------------------
// Accessory (application) popup
// ---------------------------------------------------------------------------
interface AppItem {
  code: string
  application: string
  icon: string
  usage: boolean
}

const showAppModal   = ref(false)
const appRoom         = ref<Room | null>(null)
const appList          = ref<AppItem[]>([])
const appListState     = ref<'idle' | 'loading' | 'error'>('idle')
const appListErrMsg    = ref('')
const togglingApp       = ref<string | null>(null)
const toggleErrMsg      = ref('')

function openAppModal(room: Room) {
  appRoom.value       = room
  toggleErrMsg.value  = ''
  showAppModal.value  = true
  fetchAppList()
}

function closeAppModal() {
  showAppModal.value = false
}

async function fetchAppList() {
  if (!appRoom.value) return
  appListState.value  = 'loading'
  appListErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/application/get_list_application/?room_no=${appRoom.value.room_no}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    appList.value = await res.json()
    appListState.value = 'idle'
  } catch (e) {
    appList.value        = []
    appListState.value   = 'error'
    appListErrMsg.value  = `Failed to load applications: ${e}`
  }
}

async function toggleApp(app: AppItem) {
  if (!appRoom.value || togglingApp.value !== null) return
  togglingApp.value  = app.code
  toggleErrMsg.value = ''
  try {
    if (!app.usage) {
      const res = await fetch(`${apiBase}/application/set_application/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_no: appRoom.value.room_no, application: app.code }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
    } else {
      const params = new URLSearchParams({ room_no: appRoom.value.room_no, application: app.code })
      const res = await fetch(`${apiBase}/application/unset_application/?${params}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
    }
    app.usage = !app.usage
  } catch (e) {
    toggleErrMsg.value = `Failed to update ${app.application.trim()}: ${e}`
  } finally {
    togglingApp.value = null
  }
}

// ---------------------------------------------------------------------------
// Accessory (physical equipment) popup
// ---------------------------------------------------------------------------
interface AccessoryItem {
  code: string
  accessory: string
  icon: string
  usage: boolean
}

const showAccessoryModal   = ref(false)
const accessoryRoom         = ref<Room | null>(null)
const accessoryList          = ref<AccessoryItem[]>([])
const accessoryListState     = ref<'idle' | 'loading' | 'error'>('idle')
const accessoryListErrMsg    = ref('')
const togglingAccessory       = ref<string | null>(null)
const accessoryToggleErrMsg   = ref('')

// The API's "icon" field is an HTML credit link (e.g. Flaticon attribution),
// not an image URL — extract href/text instead of rendering the HTML directly
// to avoid injecting untrusted markup.
function parseIconCredit(html: string): { href: string; text: string } | null {
  const match = html.match(/<a\s+href="([^"]+)"[^>]*>([^<]*)<\/a>/i)
  if (!match) return null
  return { href: match[1], text: match[2] }
}

function openAccessoryModal(room: Room) {
  accessoryRoom.value       = room
  accessoryToggleErrMsg.value = ''
  showAccessoryModal.value  = true
  fetchAccessoryList()
}

function closeAccessoryModal() {
  showAccessoryModal.value = false
}

async function fetchAccessoryList() {
  if (!accessoryRoom.value) return
  accessoryListState.value  = 'loading'
  accessoryListErrMsg.value = ''
  try {
    const res = await fetch(`${apiBase}/accessory/get_list_accessory/?room_no=${accessoryRoom.value.room_no}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    accessoryList.value = await res.json()
    accessoryListState.value = 'idle'
  } catch (e) {
    accessoryList.value        = []
    accessoryListState.value   = 'error'
    accessoryListErrMsg.value  = `Failed to load accessories: ${e}`
  }
}

async function toggleAccessory(item: AccessoryItem) {
  if (!accessoryRoom.value || togglingAccessory.value !== null) return
  togglingAccessory.value     = item.code
  accessoryToggleErrMsg.value = ''
  try {
    if (!item.usage) {
      const res = await fetch(`${apiBase}/accessory/set_accessory/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_no: accessoryRoom.value.room_no, accessory: item.code }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
    } else {
      const params = new URLSearchParams({ room_no: accessoryRoom.value.room_no, accessory: item.code })
      const res = await fetch(`${apiBase}/accessory/unset_accessory/?${params}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
    }
    item.usage = !item.usage
  } catch (e) {
    accessoryToggleErrMsg.value = `Failed to update ${item.accessory}: ${e}`
  } finally {
    togglingAccessory.value = null
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <div class="card-header">
        <p class="card-title">Rooms</p>
        <button class="btn" @click="openAddModal">+ Add Room</button>
      </div>

      <div v-if="listState === 'loading'" class="hint">Loading…</div>
      <div v-else-if="listState === 'error'" class="msg error-box">{{ listErrMsg }}</div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>Room No</th>
            <th>Type</th>
            <th>Floor</th>
            <th>Building</th>
            <th>PCs</th>
            <th>Seats</th>
            <th>Panorama</th>
            <th>Images</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rooms.length === 0">
            <td colspan="9" class="empty">No rooms found.</td>
          </tr>
          <tr v-for="room in rooms" :key="room.id">
            <td>{{ room.room_no }}</td>
            <td>{{ room.room_type ?? '—' }}</td>
            <td>{{ room.floor_no ?? '—' }}</td>
            <td>{{ room.building ?? '—' }}</td>
            <td>{{ room.computer_no ?? '—' }}</td>
            <td>{{ room.seat_no ?? '—' }}</td>
            <td class="media-cell">
              <button
                v-if="room.panorama"
                type="button"
                class="image-thumbnail panorama-thumbnail"
                :aria-label="`ดูภาพ Panorama ห้อง ${room.room_no}`"
                @click="openImagePreview(panoramaUrl(room), `Panorama ห้อง ${room.room_no}`)"
              >
                <img :src="panoramaUrl(room)" :alt="`Panorama ห้อง ${room.room_no}`" loading="lazy" />
              </button>
              <span v-else class="badge badge-inactive">Not set</span>
            </td>
            <td class="media-cell">
              <div v-if="room.images?.length" class="image-thumbnails">
                <button
                  v-for="(item, index) in room.images.slice(0, 3)"
                  :key="item.image"
                  type="button"
                  class="image-thumbnail"
                  :aria-label="`ดูภาพห้อง ${room.room_no} ภาพที่ ${index + 1}`"
                  @click="openImagePreview(roomImageUrl(item.image), `ห้อง ${room.room_no} ภาพที่ ${index + 1}`)"
                >
                  <img :src="roomImageUrl(item.image)" :alt="`ห้อง ${room.room_no} ภาพที่ ${index + 1}`" loading="lazy" />
                </button>
                <span v-if="room.images.length > 3" class="image-count">+{{ room.images.length - 3 }}</span>
              </div>
              <span v-else class="badge badge-inactive">No images</span>
            </td>
            <td>
              <div class="actions">
                <button type="button" class="action-btn" @click="openEditModal(room)">Edit</button>
                <button
                  type="button"
                  class="action-btn action-danger"
                  :disabled="deletingId === room.id"
                  @click="deleteRoom(room)"
                >
                  {{ deletingId === room.id ? 'Deleting…' : 'Delete' }}
                </button>
                <button type="button" class="action-btn" @click="openImageManager(room)">
                  Media ({{ (room.panorama ? 1 : 0) + (room.images?.length ?? 0) }})
                </button>
                <button type="button" class="action-btn" @click="openAppModal(room)">Applications</button>
                <button type="button" class="action-btn" @click="openAccessoryModal(room)">Accessory</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

    </div>

    <!-- Hidden input shared by the "+ Image" buttons -->
    <input
      ref="imageFileInput"
      type="file"
      accept=".png,.jpg,.jpeg"
      class="hidden-input"
      @change="onImageFileSelect"
    />

    <!-- Room image manager -->
    <Teleport to="body">
      <div v-if="imageManagerRoom" class="overlay" @click.self="closeImageManager">
        <div class="modal image-manager-modal" role="dialog" aria-modal="true" aria-labelledby="image-manager-title">
          <button class="modal-close" aria-label="ปิดหน้าต่างจัดการรูป" @click="closeImageManager">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <div class="image-manager-heading">
            <div>
              <p id="image-manager-title" class="card-title">Manage Media — {{ imageManagerRoom.room_no }}</p>
              <p>Panorama and {{ imageManagerRoom.images?.length ?? 0 }} room images</p>
            </div>
          </div>

          <section class="media-manager-section" aria-labelledby="panorama-manager-title">
            <div class="media-manager-section-heading">
              <div>
                <h3 id="panorama-manager-title">Panorama</h3>
                <p>ภาพมุมกว้างหลักของห้อง</p>
              </div>
              <button type="button" class="action-btn" @click="openPanoModal(imageManagerRoom)">
                {{ imageManagerRoom.panorama ? 'Replace Panorama' : '+ Add Panorama' }}
              </button>
            </div>

            <div v-if="imageManagerRoom.panorama" class="managed-panorama-card">
              <button
                type="button"
                class="managed-panorama-preview"
                :aria-label="`ดู Panorama ห้อง ${imageManagerRoom.room_no}`"
                @click="openImagePreview(panoramaUrl(imageManagerRoom), `Panorama ห้อง ${imageManagerRoom.room_no}`)"
              >
                <img :src="panoramaUrl(imageManagerRoom)" :alt="`Panorama ห้อง ${imageManagerRoom.room_no}`" />
              </button>
              <button
                type="button"
                class="managed-image-delete"
                :disabled="deletingPanoramaRoom !== null"
                @click="deletePanorama(imageManagerRoom)"
              >
                <span v-if="deletingPanoramaRoom === imageManagerRoom.room_no" class="mini-spinner" aria-hidden="true" />
                <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" /></svg>
                {{ deletingPanoramaRoom === imageManagerRoom.room_no ? 'Deleting…' : 'Delete Panorama' }}
              </button>
            </div>
            <div v-else class="panorama-empty">No panorama uploaded.</div>

            <div v-if="panoramaDeleteState === 'error'" class="msg error-box" role="alert">{{ panoramaDeleteMessage }}</div>
            <div v-else-if="panoramaDeleteState === 'done'" class="msg ok-box" role="status">{{ panoramaDeleteMessage }}</div>
          </section>

          <section class="media-manager-section" aria-labelledby="room-images-manager-title">
            <div class="media-manager-section-heading">
              <div>
                <h3 id="room-images-manager-title">Room Images</h3>
                <p>{{ imageManagerRoom.images?.length ?? 0 }} uploaded images</p>
              </div>
            <button
              type="button"
              class="btn image-manager-add"
              :disabled="imageUploadState === 'loading'"
              @click="triggerImageUpload(imageManagerRoom)"
            >
              <span v-if="imageUploadState === 'loading'" class="spinner" aria-hidden="true" />
              {{ imageUploadState === 'loading' ? 'Uploading…' : '+ Add Image' }}
            </button>
          </div>

          <div v-if="!imageManagerRoom.images?.length" class="image-manager-empty">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5M9 9h.01" /></svg>
            <p>No uploaded images.</p>
            <span>Use “Add Image” to upload the first image for this room.</span>
          </div>

          <div v-else class="image-manager-grid">
            <article v-for="(item, index) in imageManagerRoom.images" :key="item.image" class="managed-image-card">
              <button
                type="button"
                class="managed-image-preview"
                :aria-label="`ดูภาพที่ ${index + 1} ของห้อง ${imageManagerRoom.room_no}`"
                @click="openImagePreview(roomImageUrl(item.image), `ห้อง ${imageManagerRoom.room_no} ภาพที่ ${index + 1}`)"
              >
                <img :src="roomImageUrl(item.image)" :alt="`ห้อง ${imageManagerRoom.room_no} ภาพที่ ${index + 1}`" loading="lazy" />
              </button>
              <footer>
                <span>Image {{ index + 1 }}</span>
                <button
                  type="button"
                  class="managed-image-delete"
                  :disabled="deletingImagePath !== null"
                  :aria-label="`ลบภาพที่ ${index + 1} ของห้อง ${imageManagerRoom.room_no}`"
                  @click="deleteRoomImage(imageManagerRoom, item, index)"
                >
                  <span v-if="deletingImagePath === item.image" class="mini-spinner" aria-hidden="true" />
                  <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" /></svg>
                  {{ deletingImagePath === item.image ? 'Deleting…' : 'Delete' }}
                </button>
              </footer>
            </article>
          </div>

          <div v-if="imageUploadState === 'error'" class="msg error-box" role="alert">{{ imageErrMsg }}</div>
          <div v-else-if="imageUploadState === 'done'" class="msg ok-box" role="status">Image uploaded successfully.</div>
          <div v-if="imageDeleteState === 'error'" class="msg error-box" role="alert">{{ imageDeleteMessage }}</div>
          <div v-else-if="imageDeleteState === 'done'" class="msg ok-box" role="status">{{ imageDeleteMessage }}</div>
          </section>
        </div>
      </div>
    </Teleport>

    <!-- Add / edit room popup -->
    <Teleport to="body">
      <div v-if="showFormModal" class="overlay" @click.self="closeFormModal">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="closeFormModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">{{ formMode === 'add' ? 'Add Room' : 'Edit Room' }}</p>

          <form class="form" @submit.prevent="submitForm">
            <div class="field">
              <label class="lbl">Room No</label>
              <input v-model="form.room_no" type="text" class="input" required :disabled="formMode === 'edit'" />
            </div>

            <div class="field">
              <label class="lbl">Room Type</label>
              <select v-model="form.room_type" class="input">
                <option value="" disabled>Select a type</option>
                <option value="class room">class room</option>
                <option value="meeting room">meeting room</option>
                <option value="other">other</option>
              </select>
            </div>

            <div class="field-row">
              <div class="field">
                <label class="lbl">Floor No</label>
                <input v-model.number="form.floor_no" type="number" class="input" />
              </div>
              <div class="field">
                <label class="lbl">Building</label>
                <input v-model="form.building" type="text" class="input" />
              </div>
            </div>

            <div class="field-row">
              <div class="field">
                <label class="lbl">Computer No</label>
                <input v-model.number="form.computer_no" type="number" class="input" />
              </div>
              <div class="field">
                <label class="lbl">Seat No</label>
                <input v-model.number="form.seat_no" type="number" class="input" />
              </div>
            </div>

            <button class="btn" type="submit" :disabled="formState === 'loading'">
              <span v-if="formState === 'loading'" class="spinner"></span>
              {{ formState === 'loading' ? 'Saving…' : (formMode === 'add' ? 'Create' : 'Save') }}
            </button>
          </form>

          <div v-if="formState === 'error'" class="msg error-box">{{ formErrMsg }}</div>
        </div>
      </div>
    </Teleport>

    <!-- Upload panorama popup + dropzone -->
    <Teleport to="body">
      <div v-if="showPanoModal" class="overlay" @click.self="closePanoModal">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="closePanoModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">Upload Panorama — {{ panoRoom?.room_no }}</p>

          <div
            class="dropzone"
            :class="{ 'drag-over': panoDragOver, uploading: panoState === 'loading' }"
            @dragover="onPanoDragOver"
            @dragleave="onPanoDragLeave"
            @drop="onPanoDrop"
            @click="onPanoBrowse"
          >
            <span v-if="panoState === 'loading'" class="spinner spinner-dark"></span>
            <template v-else>
              <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 7.5m0 0L7.5 12M12 7.5V16.5" />
              </svg>
              <p class="dropzone-text">Drag &amp; drop an image here, or click to browse</p>
              <p class="dropzone-hint">PNG or JPG</p>
            </template>
          </div>
          <input
            ref="panoFileInput"
            type="file"
            accept=".png,.jpg,.jpeg"
            class="hidden-input"
            @change="onPanoFileSelect"
          />

          <div v-if="panoState === 'error'" class="msg error-box">{{ panoErrMsg }}</div>
          <div v-else-if="panoState === 'done'" class="msg ok-box">Panorama uploaded successfully.</div>
        </div>
      </div>
    </Teleport>

    <!-- Uploaded image preview -->
    <Teleport to="body">
      <div v-if="previewImage" class="overlay image-preview-overlay" @click.self="closeImagePreview">
        <div class="image-preview-modal" role="dialog" aria-modal="true" :aria-label="previewImage.alt">
          <button class="modal-close" aria-label="Close image preview" @click="closeImagePreview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <img :src="previewImage.src" :alt="previewImage.alt" class="preview-image" />
          <p class="preview-caption">{{ previewImage.alt }}</p>
        </div>
      </div>
    </Teleport>

    <!-- Applications popup -->
    <Teleport to="body">
      <div v-if="showAppModal" class="overlay" @click.self="closeAppModal">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="closeAppModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">Applications — {{ appRoom?.room_no }}</p>

          <div v-if="appListState === 'loading'" class="hint">Loading…</div>
          <div v-else-if="appListState === 'error'" class="msg error-box">{{ appListErrMsg }}</div>

          <ul v-else class="app-list">
            <li v-if="appList.length === 0" class="empty">No applications found.</li>
            <li v-for="app in appList" :key="app.code" class="app-row">
              <img :src="app.icon" :alt="app.application.trim()" class="app-icon" />
              <span class="app-name">{{ app.application.trim() }}</span>
              <input
                type="checkbox"
                class="app-checkbox"
                :checked="app.usage"
                :disabled="togglingApp === app.code"
                @change="toggleApp(app)"
              />
            </li>
          </ul>

          <div v-if="toggleErrMsg" class="msg error-box">{{ toggleErrMsg }}</div>
        </div>
      </div>
    </Teleport>

    <!-- Accessory (physical equipment) popup -->
    <Teleport to="body">
      <div v-if="showAccessoryModal" class="overlay" @click.self="closeAccessoryModal">
        <div class="modal">
          <button class="modal-close" aria-label="Close" @click="closeAccessoryModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>

          <p class="card-title">Accessory — {{ accessoryRoom?.room_no }}</p>

          <div v-if="accessoryListState === 'loading'" class="hint">Loading…</div>
          <div v-else-if="accessoryListState === 'error'" class="msg error-box">{{ accessoryListErrMsg }}</div>

          <ul v-else class="app-list">
            <li v-if="accessoryList.length === 0" class="empty">No accessories found.</li>
            <li v-for="item in accessoryList" :key="item.code" class="app-row">
              <img :src="`${apiBase}/accessory/get_picture/${item.icon}`" :alt="item.accessory" class="app-icon" />
              <span class="app-name">
                {{ item.accessory }}
                <a
                  v-if="parseIconCredit(item.icon)"
                  :href="parseIconCredit(item.icon)!.href"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="app-icon-credit"
                >{{ parseIconCredit(item.icon)!.text }}</a>
              </span>
              <input
                type="checkbox"
                class="app-checkbox"
                :checked="item.usage"
                :disabled="togglingAccessory === item.code"
                @change="toggleAccessory(item)"
              />
            </li>
          </ul>

          <div v-if="accessoryToggleErrMsg" class="msg error-box">{{ accessoryToggleErrMsg }}</div>
        </div>
      </div>
    </Teleport>
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

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.card-title {
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-link-hover);
  margin: 0;
}

.hint {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.table th {
  text-align: left;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.table td {
  padding: 0.6rem;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.media-cell {
  width: 1%;
  min-width: 5.5rem;
  white-space: normal;
}

.image-thumbnails {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.18rem 0.1rem;
}

.image-thumbnail {
  display: inline-flex;
  width: 3rem;
  height: 2.35rem;
  flex: 0 0 auto;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 0.45rem;
  background: var(--bg-page);
  cursor: zoom-in;
}

.image-thumbnail:hover,
.image-thumbnail:focus-visible {
  border-color: var(--accent-link-hover);
}

.image-thumbnail:focus-visible {
  outline: 2px solid var(--accent-link-hover);
  outline-offset: 2px;
}

.image-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mini-spinner {
  width: 0.55rem;
  height: 0.55rem;
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.65s linear infinite;
}

.panorama-thumbnail {
  width: 4.5rem;
}

.image-count {
  color: var(--text-secondary);
  font-size: 0.7rem;
  font-weight: 700;
}

.modal.image-manager-modal { max-width: 760px; }
.image-manager-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding-right: 2.5rem; }
.image-manager-heading p { margin: 0.22rem 0 0; color: var(--text-secondary); font-size: 0.76rem; }
.image-manager-add { flex: 0 0 auto; }
.media-manager-section { margin-top: 1rem; padding-top: 0.9rem; border-top: 1px solid var(--border); }
.media-manager-section-heading { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.media-manager-section-heading h3 { margin: 0; color: var(--text-primary); font-size: 0.86rem; }
.media-manager-section-heading p { margin: 0.15rem 0 0; color: var(--text-secondary); font-size: 0.72rem; }
.managed-panorama-card { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 0.75rem; margin-top: 0.65rem; padding: 0.55rem; border: 1px solid var(--border); border-radius: 0.7rem; background: var(--bg-page); }
.managed-panorama-preview { display: block; width: 100%; height: 7rem; padding: 0; overflow: hidden; border: 0; border-radius: 0.5rem; background: var(--bg-surface-alt); cursor: zoom-in; }
.managed-panorama-preview img { width: 100%; height: 100%; object-fit: cover; }
.managed-panorama-preview:focus-visible { outline: 2px solid var(--accent-link-hover); outline-offset: 2px; }
.panorama-empty { margin-top: 0.65rem; padding: 1rem; border: 1px dashed var(--border); border-radius: 0.7rem; background: var(--bg-page); color: var(--text-secondary); font-size: 0.76rem; text-align: center; }
.image-manager-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: 0.8rem; margin-top: 1rem; }
.managed-image-card { min-width: 0; overflow: hidden; border: 1px solid var(--border); border-radius: 0.7rem; background: var(--bg-page); }
.managed-image-preview { display: block; width: 100%; height: 8.2rem; padding: 0; overflow: hidden; border: 0; background: var(--bg-surface-alt); cursor: zoom-in; }
.managed-image-preview img { width: 100%; height: 100%; object-fit: cover; }
.managed-image-preview:focus-visible { outline: 2px solid var(--accent-link-hover); outline-offset: -3px; }
.managed-image-card footer { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.55rem 0.62rem; }
.managed-image-card footer > span { overflow: hidden; color: var(--text-secondary); font-size: 0.74rem; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.managed-image-delete { display: inline-flex; align-items: center; gap: 0.28rem; flex: 0 0 auto; padding: 0.3rem 0.48rem; border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 0.4rem; background: rgba(239, 68, 68, 0.08); color: var(--pill-error-text); font: inherit; font-size: 0.7rem; font-weight: 700; cursor: pointer; }
.managed-image-delete:hover:not(:disabled) { background: rgba(239, 68, 68, 0.16); }
.managed-image-delete:focus-visible { outline: 2px solid #ef4444; outline-offset: 2px; }
.managed-image-delete:disabled { cursor: wait; opacity: 0.65; }
.managed-image-delete svg { width: 0.82rem; height: 0.82rem; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
.image-manager-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 13rem; margin-top: 1rem; border: 1px dashed var(--border); border-radius: 0.7rem; background: var(--bg-page); color: var(--text-secondary); text-align: center; }
.image-manager-empty svg { width: 2.8rem; height: 2.8rem; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.image-manager-empty p { margin: 0.65rem 0 0.15rem; color: var(--text-primary); font-weight: 700; }
.image-manager-empty span { font-size: 0.76rem; }

.empty {
  text-align: center;
  color: #64748b;
  padding: 1.25rem 0.6rem;
}

.actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.action-btn {
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  color: var(--accent-link);
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.3rem 0.55rem;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s;
}
.action-btn:hover:not(:disabled) { background: var(--bg-surface-alt); }
.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.action-danger { color: var(--pill-error-text); }

.badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
}
.badge-active   { background: rgba(34,197,94,.12);  color: var(--pill-success-text); }
.badge-inactive { background: rgba(148,163,184,.15); color: var(--text-secondary); }

.image-preview-overlay {
  padding: 1.5rem;
}

.image-preview-modal {
  position: relative;
  width: min(72rem, 94vw);
  max-height: 90vh;
  padding: 2.75rem 1rem 1rem;
  overflow: hidden;
  border-radius: 0.9rem;
  background: var(--bg-surface);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
}

.preview-image {
  display: block;
  width: 100%;
  max-height: calc(90vh - 6rem);
  border-radius: 0.6rem;
  object-fit: contain;
  background: var(--bg-page);
}

.preview-caption {
  margin: 0.65rem 0 0;
  color: var(--text-secondary);
  font-size: 0.78rem;
  font-weight: 650;
  text-align: center;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-top: 0.75rem;
}

.field-row {
  display: flex;
  gap: 0.75rem;
}
.field-row .field { flex: 1; }

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
  width: 100%;
  box-sizing: border-box;
}
.input:disabled { opacity: 0.6; cursor: not-allowed; }

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
.spinner-dark {
  border: 2px solid rgba(37,99,235,.25);
  border-top-color: var(--accent-link-hover);
}
@keyframes spin { to { transform: rotate(360deg); } }

.msg {
  margin-top: 1rem;
  font-size: 0.8rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.5rem;
}
.error-box { background: rgba(239,68,68,.12); color: var(--pill-error-text); border: 1px solid rgba(239,68,68,.35); }
.ok-box    { background: rgba(34,197,94,.12); color: var(--pill-success-text); border: 1px solid rgba(34,197,94,.35); }

.hidden-input { display: none; }

/* ── Dropzone ── */
.dropzone {
  margin-top: 0.85rem;
  border: 2px dashed var(--border);
  border-radius: 0.75rem;
  padding: 2rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  cursor: pointer;
  background: #f8fafc;
  transition: background .15s, border-color .15s;
  min-height: 140px;
}
.dropzone:hover,
.dropzone.drag-over {
  background: #eff6ff;
  border-color: var(--accent-link-hover);
}
.dropzone.uploading { cursor: wait; }

.dropzone-icon {
  width: 32px;
  height: 32px;
  color: var(--accent-link-hover);
}

.dropzone-text {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  text-align: center;
}

.dropzone-hint {
  font-size: 0.72rem;
  color: #64748b;
  margin: 0;
}

/* ── Popup ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, .65);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  z-index: 500;
}

.modal {
  position: relative;
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 25px 60px rgba(0,0,0,.5);
  box-sizing: border-box;
}

.modal-close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-primary);
  cursor: pointer;
}
.modal-close svg { width: 16px; height: 16px; }
.modal-close:hover { background: var(--bg-surface-alt); }

/* ── Accessory list ── */
.app-list {
  list-style: none;
  margin: 0.85rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.app-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--border);
  border-radius: 0.6rem;
}

.app-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  object-fit: contain;
}

.app-name {
  flex: 1;
  font-size: 0.85rem;
  color: var(--text-primary);
}

.app-icon-credit {
  display: block;
  font-size: 0.65rem;
  color: #64748b;
  text-decoration: none;
}
.app-icon-credit:hover { text-decoration: underline; }

.app-checkbox {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  accent-color: #2563eb;
  cursor: pointer;
}
.app-checkbox:disabled { cursor: not-allowed; opacity: 0.6; }

@media (max-width: 720px) {
  .field-row { flex-direction: column; }
  .table { font-size: 0.78rem; }
  .image-manager-heading { align-items: flex-start; flex-direction: column; }
  .media-manager-section-heading { align-items: flex-start; flex-direction: column; }
  .managed-panorama-card { grid-template-columns: 1fr; }
  .image-manager-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 460px) {
  .image-manager-grid { grid-template-columns: 1fr; }
}
</style>
