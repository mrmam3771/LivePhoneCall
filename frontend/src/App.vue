<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Menu, Moon, Sun } from '@lucide/vue'
import AgentManager from './components/AgentManager.vue'
import CallPanel from './components/CallPanel.vue'
import ChatComposer from './components/ChatComposer.vue'
import MessageList from './components/MessageList.vue'
import SessionSidebar from './components/SessionSidebar.vue'
import { DEFAULT_AGENT_ID, useSqliteChatStore } from './composables/useSqliteChatStore'

const database = useSqliteChatStore()
const sessions = ref([])
const messages = ref([])
const agents = ref([])
const activeSessionId = ref('')
const activeAgentId = ref(DEFAULT_AGENT_ID)
const loading = ref(true)
const errorMessage = ref('')
const sidebarOpen = ref(false)
const callPanelOpen = ref(false)
const agentManagerOpen = ref(false)
const agentMutationPending = ref(false)
const theme = ref(localStorage.getItem('qwen-chat-theme') || 'dark')

const activeSession = computed(() =>
  sessions.value.find((session) => session.id === activeSessionId.value),
)
const activeAgent = computed(() => agents.value.find((agent) => agent.id === activeAgentId.value) || agents.value[0])

function applyTheme(value) {
  theme.value = value
  document.documentElement.dataset.theme = value
  try { localStorage.setItem('qwen-chat-theme', value) } catch { /* Theme still applies for this tab. */ }
}

function reportError(error) {
  errorMessage.value = `Chat storage error: ${error?.message || error}`
}

async function refreshSessions() {
  sessions.value = await database.listSessions()
}
async function refreshAgents() { agents.value = await database.listAgents() }

async function selectSession(id) {
  activeSessionId.value = id
  sidebarOpen.value = false
  try {
    const selectedMessages = await database.listMessages(id)
    if (activeSessionId.value === id) {
      messages.value = selectedMessages
      const session = sessions.value.find((item) => item.id === id)
      activeAgentId.value = session?.agentId || DEFAULT_AGENT_ID
    }
    await nextTick()
  } catch (error) { reportError(error) }
}

async function createSession(agentId = activeAgentId.value) {
  try {
    const session = await database.createSession(agentId)
    await refreshSessions()
    await selectSession(session.id)
  } catch (error) { reportError(error) }
}

async function saveAgent(agent) {
  if (agentMutationPending.value) return
  agentMutationPending.value = true
  try {
    const isNewAgent = !agent.id
    const saved = agent.id ? await database.updateAgent(agent) : await database.createAgent(agent)
    await refreshAgents()
    agentManagerOpen.value = false
    if (isNewAgent) {
      activeAgentId.value = saved.id
      await createSession(saved.id)
    }
  } catch (error) { reportError(error) }
  finally { agentMutationPending.value = false }
}

async function deleteAgent(id) {
  if (agentMutationPending.value) return
  agentMutationPending.value = true
  try {
    await database.deleteAgent(id)
    await refreshAgents()
    await refreshSessions()
    if (activeAgentId.value === id) activeAgentId.value = DEFAULT_AGENT_ID
    agentManagerOpen.value = false
  } catch (error) { reportError(error) }
  finally { agentMutationPending.value = false }
}

async function selectAgent(id) {
  if (agentMutationPending.value) return
  if (!activeSessionId.value) return
  agentMutationPending.value = true
  try {
    await database.setSessionAgent(activeSessionId.value, id)
    await refreshSessions()
    activeAgentId.value = id
    agentManagerOpen.value = false
  } catch (error) { reportError(error) }
  finally { agentMutationPending.value = false }
}

async function deleteSession(id) {
  try {
    await database.deleteSession(id)
    await refreshSessions()
    if (!sessions.value.length) await createSession()
    else if (id === activeSessionId.value) await selectSession(sessions.value[0].id)
  } catch (error) { reportError(error) }
}

async function addMessage(payload, targetSessionId = activeSessionId.value) {
  if (!targetSessionId) return
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

function updateLiveMessage(role, text, complete) {
  const id = `live-${role}`
  const existing = messages.value.find((message) => message.id === id)
  if (existing) existing.content = text
  else messages.value.push({ id, role, type: 'text', content: text, createdAt: Date.now() })
  if (complete) {
    messages.value = messages.value.filter((message) => message.id !== id)
    addMessage({ role, type: 'text', content: text })
  }
}

onMounted(async () => {
  applyTheme(theme.value)
  try {
    const bootstrap = await database.open()
    agents.value = bootstrap.agents
    sessions.value = bootstrap.sessions
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
      :active-agent="activeAgent"
      @create="createSession"
      @select="selectSession"
      @delete="deleteSession"
      @manage-agents="agentManagerOpen = true"
    />
    <button class="sidebar-backdrop" type="button" aria-label="Close conversations" @click="sidebarOpen = false" />

    <main class="chat-workspace">
      <header class="chat-header">
        <button class="icon-button mobile-menu" type="button" title="Open conversations" aria-label="Open conversations" @click="sidebarOpen = true">
          <Menu :size="19" />
        </button>
        <div class="chat-heading">
          <h1>{{ activeSession?.title || 'New conversation / 新会话' }}</h1>
          <span>{{ activeAgent?.name || 'Qwen General' }} · Local SQLite</span>
        </div>
        <div class="header-actions">
          <span class="preview-status"><i /> Local workspace</span>
          <button class="agent-chip" type="button" title="Choose Agent for this conversation" @click="agentManagerOpen = true">{{ activeAgent?.name || 'Qwen General' }}</button>
          <button class="icon-button theme-toggle" type="button" :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" @click="applyTheme(theme === 'dark' ? 'light' : 'dark')">
            <Sun v-if="theme === 'dark'" :size="18" />
            <Moon v-else :size="18" />
          </button>
        </div>
      </header>

      <MessageList :messages="messages" :loading="loading" :error="errorMessage" />
      <div class="interaction-dock">
        <CallPanel v-if="callPanelOpen" :session-id="activeSessionId" :agent="activeAgent" :history="messages.filter((message) => message.role === 'user' || message.role === 'assistant').map((message) => ({ role: message.role, content: message.content }))" @close="callPanelOpen = false" @transcript="({ text, partial }) => updateLiveMessage('user', text, !partial)" @assistant="({ text, partial }) => updateLiveMessage('assistant', text, !partial)" />
        <ChatComposer :call-panel-open="callPanelOpen" @send="sendMessage" @toggle-call="callPanelOpen = !callPanelOpen" />
      </div>
    </main>
    <AgentManager v-if="agentManagerOpen" :agents="agents" :selected-agent-id="activeAgentId" :busy="agentMutationPending" @close="agentManagerOpen = false" @save="saveAgent" @delete="deleteAgent" @select="selectAgent" />
  </div>
</template>
