<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Menu, Moon, Sun } from '@lucide/vue'
import CallPanel from './components/CallPanel.vue'
import ChatComposer from './components/ChatComposer.vue'
import MessageList from './components/MessageList.vue'
import SessionSidebar from './components/SessionSidebar.vue'
import { useChatDatabase } from './composables/useChatDatabase'

const database = useChatDatabase()
const sessions = ref([])
const messages = ref([])
const activeSessionId = ref('')
const loading = ref(true)
const errorMessage = ref('')
const sidebarOpen = ref(false)
const callPanelOpen = ref(false)
const theme = ref(localStorage.getItem('qwen-chat-theme') || 'dark')

const activeSession = computed(() =>
  sessions.value.find((session) => session.id === activeSessionId.value),
)

function applyTheme(value) {
  theme.value = value
  document.documentElement.dataset.theme = value
  try { localStorage.setItem('qwen-chat-theme', value) } catch { /* Theme still applies for this tab. */ }
}

function reportError(error) {
  errorMessage.value = `Local storage error: ${error?.message || error}`
}

async function refreshSessions() {
  sessions.value = await database.listSessions()
}

async function selectSession(id) {
  activeSessionId.value = id
  sidebarOpen.value = false
  try {
    const selectedMessages = await database.listMessages(id)
    if (activeSessionId.value === id) messages.value = selectedMessages
    await nextTick()
  } catch (error) { reportError(error) }
}

async function createSession() {
  try {
    const session = await database.createSession()
    await refreshSessions()
    await selectSession(session.id)
  } catch (error) { reportError(error) }
}

async function deleteSession(id) {
  try {
    await database.deleteSession(id)
    await refreshSessions()
    if (!sessions.value.length) await createSession()
    else if (id === activeSessionId.value) await selectSession(sessions.value[0].id)
  } catch (error) { reportError(error) }
}

async function addMessage(payload) {
  if (!activeSessionId.value) return
  const targetSessionId = activeSessionId.value
  try {
    await database.addMessage(targetSessionId, payload)
    const targetMessages = await database.listMessages(targetSessionId)
    if (activeSessionId.value === targetSessionId) messages.value = targetMessages
    await refreshSessions()
  } catch (error) { reportError(error) }
}

async function sendMessage(content) {
  await addMessage({ role: 'user', type: 'text', content })
}

async function saveRecording(recording) {
  await addMessage({
    role: 'user',
    type: 'audio',
    content: 'Voice note / 语音留言',
    audio: recording.blob,
    mimeType: recording.mimeType,
    duration: recording.duration,
  })
  callPanelOpen.value = false
}

onMounted(async () => {
  applyTheme(theme.value)
  try {
    await database.open()
    await refreshSessions()
    if (!sessions.value.length) await createSession()
    else await selectSession(sessions.value[0].id)
  } catch (error) { reportError(error) }
  finally { loading.value = false }
})
</script>

<template>
  <div class="app-shell" :class="{ 'sidebar-is-open': sidebarOpen }">
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="activeSessionId"
      @create="createSession"
      @select="selectSession"
      @delete="deleteSession"
    />
    <button class="sidebar-backdrop" type="button" aria-label="Close conversations" @click="sidebarOpen = false" />

    <main class="chat-workspace">
      <header class="chat-header">
        <button class="icon-button mobile-menu" type="button" title="Open conversations" aria-label="Open conversations" @click="sidebarOpen = true">
          <Menu :size="19" />
        </button>
        <div class="chat-heading">
          <h1>{{ activeSession?.title || 'New conversation / 新会话' }}</h1>
          <span>Saved locally / 本地保存</span>
        </div>
        <div class="header-actions">
          <span class="preview-status"><i /> Frontend preview</span>
          <button class="icon-button theme-toggle" type="button" :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" @click="applyTheme(theme === 'dark' ? 'light' : 'dark')">
            <Sun v-if="theme === 'dark'" :size="18" />
            <Moon v-else :size="18" />
          </button>
        </div>
      </header>

      <MessageList :messages="messages" :loading="loading" :error="errorMessage" />
      <div class="interaction-dock">
        <CallPanel v-if="callPanelOpen" @close="callPanelOpen = false" @recording-complete="saveRecording" />
        <ChatComposer :call-panel-open="callPanelOpen" @send="sendMessage" @toggle-call="callPanelOpen = !callPanelOpen" />
      </div>
    </main>
  </div>
</template>
