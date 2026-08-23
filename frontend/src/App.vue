<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { Menu, Moon, Settings2, Sun, Volume2 } from '@lucide/vue'
import AgentManager from './components/AgentManager.vue'
import ModelManager from './components/ModelManager.vue'
import ProviderManager from './components/ProviderManager.vue'
import VoiceSettings from './components/VoiceSettings.vue'
import PwaUpdatePrompt from './components/PwaUpdatePrompt.vue'
import CallPanel from './components/CallPanel.vue'
import ChatComposer from './components/ChatComposer.vue'
import MessageList from './components/MessageList.vue'
import SessionSidebar from './components/SessionSidebar.vue'
import { DEFAULT_AGENT_ID, useSqliteChatStore } from './composables/useSqliteChatStore'
import { presetForProvider } from './lib/providerCatalog'
import { buildModelOptions, findModelOption } from './lib/modelCatalog'
import { streamModelReply } from './composables/useModelStream'
import { usePendingReplies } from './composables/usePendingReplies'
import { conversationTitle, removeMessage, replaceMessage } from './lib/optimisticMessages'
import { createSessionMessageQueue } from './lib/sessionMessageQueue'
import { createClientId } from './lib/clientId'

const database = useSqliteChatStore()
const pendingReplies = usePendingReplies()
const responseControllers = new Map()
const messageWrites = new Set()
const sessionMessageQueue = createSessionMessageQueue()
const sessions = ref([])
const messages = ref([])
const agents = ref([])
const providers = ref([])
const models = ref([])
const modelCatalog = ref({})
const activeSessionId = ref('')
const activeAgentId = ref(DEFAULT_AGENT_ID)
const activeModelId = ref('deepseek-chat')
const loading = ref(true)
const errorMessage = ref('')
const sidebarOpen = ref(false)
const callPanelOpen = ref(false)
const callBusy = ref(false)
const callThinking = ref(false)
const agentManagerOpen = ref(false)
const modelManagerOpen = ref(false)
const providerManagerOpen = ref(false)
const voiceSettingsOpen = ref(false)
const agentMutationPending = ref(false)
const messageList = ref(null)
const callPanel = ref(null)
const theme = ref(localStorage.getItem('qwen-chat-theme') || 'dark')

const activeSession = computed(() =>
  sessions.value.find((session) => session.id === activeSessionId.value),
)
const activeAgent = computed(() => agents.value.find((agent) => agent.id === activeAgentId.value) || agents.value[0])
const activeModel = computed(() => models.value.find((model) => model.id === activeModelId.value) || models.value[0])
const activeProvider = computed(() => providers.value.find((provider) => provider.id === activeModel.value?.providerId) || providers.value[0])
const modelOptions = computed(() => buildModelOptions({
  providers: providers.value,
  models: models.value,
  catalog: modelCatalog.value,
  activeModelId: activeModelId.value,
}))

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
async function refreshProviders() { providers.value = await database.listProviders() }
async function refreshModels() { models.value = await database.listModels() }

async function selectSession(id) {
  activeSessionId.value = id
  sidebarOpen.value = false
  try {
    const selectedMessages = await database.listMessages(id)
    if (activeSessionId.value === id) {
      messages.value = selectedMessages
      const session = sessions.value.find((item) => item.id === id)
      activeAgentId.value = session?.agentId || DEFAULT_AGENT_ID
      activeModelId.value = session?.modelId || 'deepseek-chat'
    }
    await nextTick()
    messageList.value?.scrollToBottom()
  } catch (error) { reportError(error) }
}

async function createSession(agentId = activeAgentId.value, modelId = activeModelId.value) {
  try {
    const session = await database.createSession(agentId, modelId)
    await refreshSessions()
    await selectSession(session.id)
  } catch (error) { reportError(error) }
}

async function saveAgent(agent) {
  if (agentMutationPending.value) return
  errorMessage.value = ''
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

async function saveModel(model) { try { model.id ? await database.updateModel(model) : await database.createModel(model); await refreshModels(); modelManagerOpen.value = false } catch (error) { reportError(error) } }
async function deleteModel(id) { try { await database.deleteModel(id); await refreshModels(); await refreshSessions(); modelManagerOpen.value = false } catch (error) { reportError(error) } }
async function selectModel(id) {
  if (!activeSessionId.value) return
  try {
    const option = findModelOption(modelOptions.value, id)
    let storedModelId = id
    if (option && !option.persisted) {
      const saved = await database.createModel({
        providerId: option.providerId,
        name: option.label,
        model: option.modelId,
        requestPath: '/chat/completions',
      })
      storedModelId = saved.id
      await refreshModels()
    }
    await database.setSessionModel(activeSessionId.value, storedModelId)
    await refreshSessions()
    activeModelId.value = storedModelId
    modelManagerOpen.value = false
  } catch (error) { reportError(error) }
}
async function saveProvider(provider) {
  try {
    const isNew = !provider.id
    const saved = provider.id ? await database.updateProvider(provider) : await database.createProvider(provider)
    if (isNew) {
      const firstModel = presetForProvider(saved).models[0]
      if (firstModel) await database.createModel({ providerId: saved.id, name: firstModel[0], model: firstModel[1] })
    }
    await Promise.all([refreshProviders(), refreshModels()])
  } catch (error) { reportError(error) }
}
async function deleteProvider(id) { try { await database.deleteProvider(id); await refreshProviders(); providerManagerOpen.value = false } catch (error) { reportError(error) } }

async function saveVoice(voice) {
  if (!activeAgent.value || agentMutationPending.value) return
  agentMutationPending.value = true
  errorMessage.value = ''
  try {
    await database.updateAgent({ ...activeAgent.value, voice })
    await refreshAgents()
    voiceSettingsOpen.value = false
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

async function persistOptimisticMessage(payload, targetSessionId, optimisticId) {
  if (!targetSessionId) throw new Error('No active conversation')
  const temporaryId = optimisticId || `optimistic-${createClientId()}`
  if (activeSessionId.value === targetSessionId && !messages.value.some((message) => message.id === temporaryId)) {
    messages.value.push({ ...payload, id: temporaryId, createdAt: Date.now() })
  }
  const previousSession = sessions.value.find((session) => session.id === targetSessionId)
  const summary = payload.content.replace(/\s+/g, ' ').trim()
  if (previousSession) {
    sessions.value = sessions.value.map((session) => session.id === targetSessionId ? {
      ...session,
      title: payload.role === 'user' && ['New conversation / 新会话', 'Greeting / 问候'].includes(session.title) ? conversationTitle(payload.content) : session.title,
      preview: summary.slice(0, 62),
      updatedAt: Date.now(),
    } : session)
  }
  try {
    const saved = await sessionMessageQueue.enqueue(
      targetSessionId,
      () => database.addMessage(targetSessionId, payload),
    )
    if (activeSessionId.value === targetSessionId) messages.value = replaceMessage(messages.value, temporaryId, saved)
    await refreshSessions()
    return saved
  } catch (error) {
    if (activeSessionId.value === targetSessionId) messages.value = removeMessage(messages.value, temporaryId)
    if (previousSession) sessions.value = sessions.value.map((session) => session.id === targetSessionId ? previousSession : session)
    reportError(error)
    throw error
  }
}

async function sendMessage(content) {
  const sessionId = activeSessionId.value
  const controller = new AbortController()
  const turnId = createClientId()
  if (!responseControllers.has(sessionId)) responseControllers.set(sessionId, new Set())
  responseControllers.get(sessionId).add(controller)
  const history = messages.value
    .filter((message) => message.type === 'text' && (message.role === 'user' || message.role === 'assistant'))
    .map((message) => ({ role: message.role, content: message.content }))
  const agent = { ...activeAgent.value, ...activeProvider.value, provider: activeProvider.value?.api, model: activeModel.value?.model, requestPath: activeModel.value?.requestPath }
  const userWrite = persistOptimisticMessage({ role: 'user', type: 'text', content }, sessionId)
  pendingReplies.start(sessionId)
  let thinking = ''
  let partialReply = ''
  let userStored = false
  try {
    await userWrite
    userStored = true
    const reply = await streamModelReply({
      text: content,
      conversationId: sessionId,
      history,
      agent,
      signal: controller.signal,
      onToken: (partial) => { partialReply = partial; if (activeSessionId.value === sessionId) updateLiveMessage('assistant', partial, false, 'text', turnId) },
      onThinking: (partial) => { thinking = partial; if (activeSessionId.value === sessionId) updateLiveMessage('assistant', partial, false, 'thinking', turnId) },
    })
    if (activeSessionId.value === sessionId) {
      if (thinking) updateLiveMessage('assistant', thinking, true, 'thinking', turnId)
      updateLiveMessage('assistant', reply, true, 'text', turnId)
    } else {
      if (thinking) await addMessage({ role: 'assistant', type: 'thinking', content: thinking }, sessionId)
      await addMessage({ role: 'assistant', type: 'text', content: reply }, sessionId)
    }
  } catch (error) {
    if (!userStored) return
    if (error?.name === 'AbortError') {
      if (activeSessionId.value === sessionId) {
        if (thinking) updateLiveMessage('assistant', thinking, true, 'thinking', turnId)
        if (partialReply) updateLiveMessage('assistant', partialReply, true, 'text', turnId)
      } else {
        if (thinking) await addMessage({ role: 'assistant', type: 'thinking', content: thinking }, sessionId)
        if (partialReply) await addMessage({ role: 'assistant', type: 'text', content: partialReply }, sessionId)
      }
      return
    }
    const message = `Model request failed: ${error?.message || error}`
    if (activeSessionId.value === sessionId) updateLiveMessage('assistant', message, true, 'text', turnId)
    else await addMessage({ role: 'assistant', type: 'text', content: message }, sessionId)
  } finally {
    responseControllers.get(sessionId)?.delete(controller)
    if (!responseControllers.get(sessionId)?.size) responseControllers.delete(sessionId)
    pendingReplies.finish(sessionId)
  }
}

function stopResponse() {
  responseControllers.get(activeSessionId.value)?.forEach((controller) => controller.abort())
  callPanel.value?.stopResponse()
}

function updateLiveMessage(role, text, complete, type = 'text', turnId = 'default') {
  const id = `live-${turnId}-${type}-${role}`
  const existing = messages.value.find((message) => message.id === id)
  if (existing) existing.content = text
  else messages.value.push({ id, role, type, content: text, createdAt: Date.now() })
  if (complete && !messageWrites.has(id)) {
    messageWrites.add(id)
    persistOptimisticMessage({ role, type, content: text }, activeSessionId.value, id)
      .catch(() => {})
      .finally(() => messageWrites.delete(id))
  }
}

function handleCallTranscript({ text, turnId }) {
  updateLiveMessage('user', text, false, 'text', turnId)
}

function handleCallAssistant({ text, partial, turnId }, type = 'text') {
  updateLiveMessage('assistant', text, !partial, type, turnId)
}

async function commitCallUserMessage({ text, turnId, sessionId }) {
  await sessionMessageQueue.waitFor(sessionId)
  const previousMessages = await database.listMessages(sessionId)
  await persistOptimisticMessage(
    { role: 'user', type: 'text', content: text },
    sessionId,
    `live-${turnId}-text-user`,
  )
  return previousMessages
    .filter((message) => message.type === 'text' && (message.role === 'user' || message.role === 'assistant'))
    .map((message) => ({ role: message.role, content: message.content }))
}

onMounted(async () => {
  applyTheme(theme.value)
  try {
    const bootstrap = await database.open()
    agents.value = bootstrap.agents
    providers.value = bootstrap.providers
    models.value = bootstrap.models
    sessions.value = bootstrap.sessions
    try { modelCatalog.value = await database.getModelCatalog() } catch { modelCatalog.value = {} }
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
          <span>{{ activeAgent?.name || 'Qwen General' }} · {{ activeModel?.name || 'Model' }}</span>
        </div>
        <div class="header-actions">
          <span class="preview-status"><i /> Local workspace</span>
          <button class="agent-chip" type="button" title="Choose Agent for this conversation" @click="agentManagerOpen = true">{{ activeAgent?.name || 'Qwen General' }}</button>
          <button class="agent-chip" type="button" title="Choose model for this conversation" @click="modelManagerOpen = true">{{ activeModel?.name || 'Model' }}</button>
          <button class="icon-button" type="button" title="Voice settings" aria-label="Voice settings" @click="voiceSettingsOpen = true"><Volume2 :size="18" /></button>
          <button class="icon-button" type="button" title="Provider settings" aria-label="Provider settings" @click="providerManagerOpen = true"><Settings2 :size="18" /></button>
          <button class="icon-button theme-toggle" type="button" :title="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" :aria-label="theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'" @click="applyTheme(theme === 'dark' ? 'light' : 'dark')">
            <Sun v-if="theme === 'dark'" :size="18" />
            <Moon v-else :size="18" />
          </button>
        </div>
      </header>

      <MessageList ref="messageList" :messages="messages" :loading="loading" :error="errorMessage" :pending="pendingReplies.has(activeSessionId) || callThinking" />
      <div class="interaction-dock" :class="{ 'has-call-panel': callPanelOpen }">
        <CallPanel ref="callPanel" v-if="callPanelOpen" :session-id="activeSessionId" :agent="{ ...activeAgent, ...activeProvider, provider: activeProvider?.api, model: activeModel?.model, requestPath: activeModel?.requestPath }" :history="messages.filter((message) => message.type === 'text' && (message.role === 'user' || message.role === 'assistant') && !String(message.id).startsWith('live-')).map((message) => ({ role: message.role, content: message.content }))" :commit-user-message="commitCallUserMessage" @close="callPanelOpen = false; callThinking = false" @busy="callBusy = $event" @thinking-state="callThinking = $event" @transcript="handleCallTranscript" @assistant="handleCallAssistant" @thinking="payload => handleCallAssistant(payload, 'thinking')" />
        <ChatComposer
          :call-panel-open="callPanelOpen"
          :model-id="activeModelId"
          :model-options="modelOptions"
          :generating="pendingReplies.has(activeSessionId) || callBusy"
          @send="sendMessage"
          @stop="stopResponse"
          @toggle-call="callPanelOpen = !callPanelOpen"
          @select-model="selectModel"
        />
      </div>
    </main>
    <AgentManager v-if="agentManagerOpen" :agents="agents" :selected-agent-id="activeAgentId" :busy="agentMutationPending" :error="errorMessage" @close="agentManagerOpen = false" @save="saveAgent" @delete="deleteAgent" @select="selectAgent" />
    <ModelManager v-if="modelManagerOpen" :models="models" :providers="providers" :selected-model-id="activeModelId" @close="modelManagerOpen = false" @save="saveModel" @delete="deleteModel" @select="selectModel" />
    <ProviderManager v-if="providerManagerOpen" :providers="providers" @close="providerManagerOpen = false" @save="saveProvider" @delete="deleteProvider" />
    <VoiceSettings v-if="voiceSettingsOpen && activeAgent" :agent="activeAgent" :busy="agentMutationPending" :error="errorMessage" @close="voiceSettingsOpen = false" @save="saveVoice" />
    <PwaUpdatePrompt />
  </div>
</template>
