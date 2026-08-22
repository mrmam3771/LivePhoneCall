<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { Bot, Check, CopyPlus, Save, Trash2, X } from '@lucide/vue'

const props = defineProps({
  agents: { type: Array, required: true },
  selectedAgentId: { type: String, required: true },
  busy: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'delete', 'save', 'select'])
const emptyAgent = () => ({ id: '', name: '', description: '', systemPrompt: '', provider: 'deepseek', baseUrl: '', requestPath: '/chat/completions', apiKey: '', model: 'deepseek-chat', language: 'Auto', voice: 'Vivian', builtIn: false })
const draft = reactive(emptyAgent())
const editingExisting = computed(() => Boolean(draft.id))
const canSave = computed(() => draft.name.trim() && draft.systemPrompt.trim() && draft.model.trim() && (draft.provider !== 'custom' || draft.baseUrl.trim()))

function editAgent(agent) { Object.assign(draft, emptyAgent(), agent) }
function createAgent() { Object.assign(draft, emptyAgent()) }
function duplicateAgent() { Object.assign(draft, { ...draft, id: '', name: `${draft.name} Copy`, builtIn: false }) }
function submit() { if (canSave.value && !props.busy) emit('save', { ...draft, name: draft.name.trim(), description: draft.description.trim(), systemPrompt: draft.systemPrompt.trim(), model: draft.model.trim() }) }
function closeOnEscape(event) { if (event.key === 'Escape' && !props.busy) emit('close') }

watch(() => props.selectedAgentId, (id) => {
  editAgent(props.agents.find((agent) => agent.id === id) || props.agents[0] || emptyAgent())
}, { immediate: true })
onMounted(() => window.addEventListener('keydown', closeOnEscape))
onBeforeUnmount(() => window.removeEventListener('keydown', closeOnEscape))
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop" @mousedown.self="$emit('close')">
      <section class="agent-modal" role="dialog" aria-modal="true" aria-labelledby="agent-manager-title">
        <header class="agent-modal-header">
          <div><h2 id="agent-manager-title">Model Settings</h2><p>Configure model connections, then assign an Agent to each conversation.</p></div>
          <button class="icon-button" type="button" title="Close Agent manager" aria-label="Close Agent manager" :disabled="busy" @click="$emit('close')"><X :size="18" /></button>
        </header>

        <div class="agent-modal-layout">
          <aside class="agent-catalog">
            <button class="new-agent" type="button" :disabled="busy" @click="createAgent"><CopyPlus :size="16" /> New model Agent</button>
            <button v-for="agent in agents" :key="agent.id" class="agent-list-item" :class="{ active: draft.id === agent.id }" type="button" :disabled="busy" @click="editAgent(agent)">
              <span class="agent-avatar"><Bot :size="16" /></span>
              <span><strong>{{ agent.name }}</strong><small>{{ agent.provider }} · {{ agent.model }}</small></span>
              <Check v-if="agent.id === selectedAgentId" :size="14" />
            </button>
          </aside>

          <form class="agent-form" @submit.prevent="submit">
            <div class="form-heading"><div><h3>{{ editingExisting ? draft.name : 'Create model Agent' }}</h3><p>Provider, model, API Key and endpoint are stored in local SQLite.</p></div><span v-if="draft.builtIn" class="built-in-label">Built-in</span></div>

            <div class="field-grid two-columns">
              <label><span>Name</span><input v-model="draft.name" maxlength="48" required :disabled="draft.builtIn" placeholder="e.g. Sales assistant" /></label>
              <label><span>Description</span><input v-model="draft.description" maxlength="100" :disabled="draft.builtIn" placeholder="What this Agent is for" /></label>
            </div>
            <label class="prompt-field"><span>System instructions</span><textarea v-model="draft.systemPrompt" rows="6" maxlength="6000" required :disabled="draft.builtIn" placeholder="Define role, tone, constraints and desired behavior..." /><small>{{ draft.systemPrompt.length }} / 6000</small></label>
            <div class="field-grid two-columns">
              <label><span>Provider</span><select v-model="draft.provider" :disabled="draft.builtIn"><option value="deepseek">DeepSeek</option><option value="dashscope">Alibaba DashScope</option><option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="google">Google Gemini</option><option value="ollama">Ollama</option><option value="custom">OpenAI-compatible</option></select></label>
              <label><span>Model</span><input v-model="draft.model" required :disabled="draft.builtIn" placeholder="Model identifier" /></label>
              <label class="full-width"><span>Base URL</span><input v-model="draft.baseUrl" :required="draft.provider === 'custom'" type="url" :disabled="draft.builtIn" placeholder="https://api.example.com/v1" /></label>
              <label><span>API Key</span><input v-model="draft.apiKey" type="password" autocomplete="off" :disabled="draft.builtIn" placeholder="Stored locally" /></label>
              <label><span>Request path</span><input v-model="draft.requestPath" :disabled="draft.builtIn" placeholder="/chat/completions" /></label>
              <label><span>Response language</span><select v-model="draft.language" :disabled="draft.builtIn"><option>Auto</option><option>Chinese</option><option>English</option></select></label>
              <label><span>Reply voice</span><select v-model="draft.voice" :disabled="draft.builtIn"><option>Vivian</option><option>Serena</option><option>Ryan</option><option>Aiden</option><option>Dylan</option><option>Eric</option><option>Sohee</option></select></label>
            </div>

            <footer class="agent-form-actions">
              <button v-if="editingExisting" class="secondary-action" type="button" :disabled="busy" @click="$emit('select', draft.id)"><Bot :size="16" /> Use Agent</button>
              <button v-if="draft.builtIn" class="secondary-action" type="button" :disabled="busy" @click="duplicateAgent"><CopyPlus :size="16" /> Duplicate</button>
              <button v-if="editingExisting && !draft.builtIn" class="danger-action" type="button" :disabled="busy" @click="$emit('delete', draft.id)"><Trash2 :size="16" /> Delete</button>
              <button v-if="!draft.builtIn" class="primary-action" type="submit" :disabled="!canSave || busy"><Save :size="16" /> {{ busy ? 'Saving...' : (editingExisting ? 'Save changes' : 'Create Agent') }}</button>
            </footer>
          </form>
        </div>
      </section>
    </div>
  </Teleport>
</template>
