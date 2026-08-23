<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Check, ChevronRight, CopyPlus, Eye, EyeOff, KeyRound, Search, Server, Trash2, X } from '@lucide/vue'
import { PROVIDER_CATALOG } from '../lib/providerCatalog'

const props = defineProps({ providers: { type: Array, default: () => [] } })
const emit = defineEmits(['close', 'save', 'delete'])
const LOCAL_PROVIDERS = new Set(['ollama', 'lmstudio', 'vllm'])
const blank = () => ({ id: '', name: '', api: 'openai-completions', baseUrl: '', apiKey: '', builtIn: false, catalogId: 'custom' })
const draft = reactive(blank())
const query = ref('')
const showApiKey = ref(false)

function normalizeEndpoint(value = '') { return value.trim().toLocaleLowerCase().replace(/\/$/, '') }
function catalogIdForProvider(provider) {
  return Object.entries(PROVIDER_CATALOG).find(([id, preset]) => (
    id !== 'custom' && (provider.id === id || normalizeEndpoint(provider.baseUrl) === normalizeEndpoint(preset.baseUrl) || provider.name?.toLocaleLowerCase() === preset.name.toLocaleLowerCase())
  ))?.[0] || 'custom'
}
function providerReady(provider) { return LOCAL_PROVIDERS.has(catalogIdForProvider(provider)) || Boolean(provider.apiKey) }
function connectedProvider(catalogId) {
  return [...props.providers]
    .filter((provider) => catalogIdForProvider(provider) === catalogId)
    .sort((a, b) => Number(Boolean(b.apiKey)) - Number(Boolean(a.apiKey)) || (b.updatedAt || 0) - (a.updatedAt || 0))[0]
}

const editing = computed(() => Boolean(draft.id))
const isCustom = computed(() => draft.catalogId === 'custom')
const isLocal = computed(() => LOCAL_PROVIDERS.has(draft.catalogId))
const connectionReady = computed(() => isLocal.value || Boolean(draft.apiKey))
const valid = computed(() => draft.name.trim() && draft.baseUrl.trim())
const protocolLabel = computed(() => ({ 'openai-completions': 'OpenAI-compatible', anthropic: 'Anthropic Messages', google_genai: 'Google Gen AI' }[draft.api] || draft.api))
const searchTerm = computed(() => query.value.trim().toLocaleLowerCase())
const filteredProviders = computed(() => props.providers.filter((provider) => !searchTerm.value || `${provider.name} ${provider.baseUrl}`.toLocaleLowerCase().includes(searchTerm.value)))
const catalogEntries = computed(() => Object.entries(PROVIDER_CATALOG)
  .filter(([id]) => id !== 'custom')
  .filter(([, preset]) => !searchTerm.value || `${preset.name} ${preset.baseUrl}`.toLocaleLowerCase().includes(searchTerm.value)))

function edit(item) { Object.assign(draft, blank(), item, { catalogId: catalogIdForProvider(item) }); showApiKey.value = false }
function create(kind = 'custom') {
  if (kind !== 'custom') {
    const existing = connectedProvider(kind)
    if (existing) return edit(existing)
  }
  const preset = PROVIDER_CATALOG[kind] || PROVIDER_CATALOG.custom
  Object.assign(draft, blank(), { name: kind === 'custom' ? '' : preset.name, baseUrl: preset.baseUrl, api: preset.api, catalogId: kind })
  showApiKey.value = false
}
function submit() { if (valid.value) emit('save', { ...draft, name: draft.name.trim(), baseUrl: draft.baseUrl.trim() }) }
watch(() => props.providers, (items) => {
  if (!draft.id && items?.length) edit(items[0])
  else if (!items?.length) create('openai')
}, { immediate: true })
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop" @mousedown.self="$emit('close')">
      <section class="agent-modal provider-modal" role="dialog" aria-modal="true" aria-labelledby="provider-title">
        <header class="agent-modal-header">
          <div><h2 id="provider-title">Model providers</h2><p>Credentials and endpoints</p></div>
          <span class="provider-total">{{ providers.length }} configured</span>
          <button class="icon-button" type="button" aria-label="Close providers" @click="$emit('close')"><X :size="18" /></button>
        </header>

        <div class="agent-modal-layout provider-layout">
          <aside class="provider-browser">
            <label class="provider-search"><Search :size="15" /><input v-model="query" type="search" placeholder="Search providers" aria-label="Search providers" /><button v-if="query" type="button" aria-label="Clear provider search" @click="query = ''"><X :size="13" /></button></label>

            <section class="provider-section">
              <header><strong>Connected</strong><span>{{ filteredProviders.length }}</span></header>
              <div v-if="filteredProviders.length" class="connected-list">
                <button v-for="item in filteredProviders" :key="item.id" class="connected-provider" :class="{ active: draft.id === item.id }" type="button" @click="edit(item)">
                  <span class="provider-mark">{{ item.name.slice(0, 1).toUpperCase() }}</span>
                  <span class="provider-copy"><strong>{{ item.name }}</strong><small :class="{ ready: providerReady(item) }"><i />{{ providerReady(item) ? 'Ready' : 'API key required' }}</small></span>
                  <Check v-if="draft.id === item.id" :size="15" /><ChevronRight v-else :size="15" />
                </button>
              </div>
              <p v-else class="provider-empty">No configured providers</p>
            </section>

            <section class="provider-section provider-directory">
              <header><strong>Available</strong><span>{{ catalogEntries.length }}</span></header>
              <div class="provider-grid">
                <button v-for="([id, preset]) in catalogEntries" :key="id" class="provider-tile" :class="{ selected: draft.catalogId === id, connected: connectedProvider(id) }" type="button" :title="preset.baseUrl" @click="create(id)">
                  <span class="provider-mark">{{ preset.name.slice(0, 1).toUpperCase() }}</span>
                  <span><strong>{{ preset.name }}</strong><small>{{ connectedProvider(id) ? 'Connected' : 'Add provider' }}</small></span>
                  <Check v-if="connectedProvider(id)" :size="13" /><CopyPlus v-else :size="13" />
                </button>
              </div>
              <button class="custom-provider" type="button" @click="create('custom')"><CopyPlus :size="15" /><span><strong>Custom provider</strong><small>OpenAI-compatible or custom protocol</small></span><ChevronRight :size="15" /></button>
            </section>
          </aside>

          <form class="agent-form provider-form" @submit.prevent="submit">
            <div class="provider-identity">
              <span class="provider-mark large">{{ (draft.name || 'C').slice(0, 1).toUpperCase() }}</span>
              <div><h3>{{ draft.name || 'Custom provider' }}</h3><p>{{ editing ? 'Configured connection' : 'New connection' }}</p></div>
              <span class="connection-state" :class="{ ready: connectionReady }"><i />{{ connectionReady ? 'Ready' : 'Not connected' }}</span>
            </div>

            <div v-if="!isCustom" class="connection-summary">
              <div><Server :size="15" /><span><small>Endpoint</small><strong>{{ draft.baseUrl }}</strong></span></div>
              <div><span class="protocol-icon">API</span><span><small>Protocol</small><strong>{{ protocolLabel }}</strong></span></div>
            </div>

            <div v-if="isCustom" class="field-grid two-columns provider-fields">
              <label><span>Provider name</span><input v-model="draft.name" required placeholder="My provider" /></label>
              <label><span>Protocol</span><select v-model="draft.api"><option value="openai-completions">OpenAI-compatible</option><option value="anthropic">Anthropic</option><option value="google_genai">Google Gen AI</option></select></label>
              <label class="full-width"><span>Base URL</span><input v-model="draft.baseUrl" required type="url" placeholder="https://api.example.com/v1" /></label>
            </div>

            <div v-if="!isLocal" class="credential-block">
              <div class="credential-heading"><KeyRound :size="15" /><div><strong>API key</strong><small>{{ draft.apiKey ? 'A key is saved for this provider' : 'No key saved' }}</small></div></div>
              <div class="secret-input"><input v-model="draft.apiKey" :type="showApiKey ? 'text' : 'password'" name="provider-api-key" autocomplete="new-password" :placeholder="`Paste ${draft.name || 'provider'} API key`" aria-label="API Key" /><button type="button" :aria-label="showApiKey ? 'Hide API key' : 'Show API key'" @click="showApiKey = !showApiKey"><EyeOff v-if="showApiKey" :size="16" /><Eye v-else :size="16" /></button></div>
            </div>

            <footer class="agent-form-actions provider-actions">
              <button v-if="editing && !draft.builtIn" class="danger-action" type="button" @click="$emit('delete', draft.id)"><Trash2 :size="16" /> Delete</button>
              <button class="primary-action" type="submit" :disabled="!valid"><Check :size="16" /> {{ editing ? 'Save connection' : 'Connect provider' }}</button>
            </footer>
          </form>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.provider-modal { width: min(1040px, 100%); }
.provider-total { margin-left: auto; margin-right: 10px; padding: 4px 7px; border: 1px solid var(--border); border-radius: 999px; color: var(--text-faint); font-size: 9px; }
.provider-layout { grid-template-columns: 340px minmax(0, 1fr); }
.provider-browser { min-height: 0; overflow-y: auto; padding: 12px; border-right: 1px solid var(--border); background: var(--sidebar); }
.provider-search { height: 38px; display: grid; grid-template-columns: 17px minmax(0, 1fr) 26px; align-items: center; gap: 7px; padding: 0 7px 0 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text-faint); }
.provider-search:focus-within { border-color: var(--accent); }
.provider-search input { min-width: 0; height: 100%; border: 0; outline: 0; background: transparent; color: var(--text); font-size: 11px; }
.provider-search input::-webkit-search-cancel-button { display: none; }
.provider-search button { width: 26px; height: 26px; display: grid; place-items: center; border: 0; border-radius: 5px; background: transparent; color: var(--text-faint); cursor: pointer; }
.provider-section { margin-top: 15px; }
.provider-section > header { height: 25px; display: flex; align-items: center; color: var(--text-soft); }
.provider-section > header strong { font-size: 10px; text-transform: uppercase; }
.provider-section > header span { margin-left: auto; min-width: 20px; padding: 2px 5px; border-radius: 999px; background: var(--surface-muted); color: var(--text-faint); font-size: 9px; text-align: center; }
.connected-list { display: grid; gap: 5px; }
.connected-provider { width: 100%; min-width: 0; height: 52px; display: grid; grid-template-columns: 32px minmax(0, 1fr) 16px; align-items: center; gap: 9px; padding: 0 9px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); cursor: pointer; text-align: left; }
.connected-provider:hover, .connected-provider.active { border-color: color-mix(in srgb, var(--accent) 55%, var(--border)); background: var(--accent-soft); }
.connected-provider > svg { color: var(--text-faint); }
.connected-provider.active > svg { color: var(--accent-strong); }
.provider-mark { width: 30px; height: 30px; display: grid; place-items: center; flex: 0 0 auto; border: 1px solid color-mix(in srgb, var(--accent) 32%, var(--border)); border-radius: 6px; background: var(--accent-soft); color: var(--accent-strong); font-size: 10px; font-weight: 800; }
.provider-mark.large { width: 42px; height: 42px; font-size: 14px; }
.provider-copy, .provider-tile > span:nth-child(2), .custom-provider > span, .credential-heading > div { min-width: 0; display: flex; flex-direction: column; }
.provider-copy strong, .provider-copy small, .provider-tile strong, .provider-tile small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.provider-copy strong { font-size: 11px; }
.provider-copy small { display: flex; align-items: center; gap: 5px; margin-top: 4px; color: var(--warning); font-size: 9px; }
.provider-copy small.ready { color: var(--success); }
.provider-copy i, .connection-state i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.provider-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.provider-tile { min-width: 0; height: 50px; display: grid; grid-template-columns: 28px minmax(0, 1fr) 14px; align-items: center; gap: 7px; padding: 0 7px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; text-align: left; }
.provider-tile:hover, .provider-tile.selected { border-color: var(--border-strong); background: var(--surface-muted); }
.provider-tile.connected > svg { color: var(--success); }
.provider-tile > .provider-mark { width: 28px; height: 28px; }
.provider-tile strong { font-size: 10px; }
.provider-tile small { margin-top: 3px; color: var(--text-faint); font-size: 8px; }
.provider-tile > svg { color: var(--text-faint); }
.custom-provider { width: 100%; min-width: 0; height: 48px; display: grid; grid-template-columns: 18px minmax(0, 1fr) 16px; align-items: center; gap: 8px; margin-top: 8px; padding: 0 10px; border: 1px dashed var(--border-strong); border-radius: 6px; background: transparent; color: var(--text-soft); cursor: pointer; text-align: left; }
.custom-provider:hover { border-color: var(--accent); color: var(--accent-strong); background: var(--accent-soft); }
.custom-provider strong { font-size: 10px; }
.custom-provider small { margin-top: 2px; color: var(--text-faint); font-size: 8px; }
.provider-empty { margin: 5px 0 0; padding: 14px; border: 1px dashed var(--border); border-radius: 6px; color: var(--text-faint); font-size: 10px; text-align: center; }
.provider-form { display: flex; flex-direction: column; padding: 24px; }
.provider-identity { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; align-items: center; gap: 11px; padding-bottom: 18px; border-bottom: 1px solid var(--border); }
.provider-identity h3 { margin: 0; color: var(--text); font-size: 16px; }
.provider-identity p { margin: 4px 0 0; color: var(--text-faint); font-size: 9px; }
.connection-state { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border: 1px solid var(--border); border-radius: 999px; color: var(--text-faint); font-size: 9px; }
.connection-state.ready { border-color: color-mix(in srgb, var(--success) 38%, var(--border)); color: var(--success); }
.connection-summary { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(160px, .65fr); gap: 8px; margin-top: 18px; }
.connection-summary > div { min-width: 0; min-height: 58px; display: flex; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface-muted); color: var(--text-faint); }
.connection-summary > div > span:last-child { min-width: 0; display: flex; flex-direction: column; }
.connection-summary small { color: var(--text-faint); font-size: 8px; text-transform: uppercase; }
.connection-summary strong { margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-soft); font: 9px ui-monospace, SFMono-Regular, Consolas, monospace; }
.protocol-icon { width: 27px; height: 27px; display: grid; place-items: center; flex: 0 0 auto; border: 1px solid var(--border); border-radius: 5px; color: var(--accent-strong); font-size: 7px; font-weight: 800; }
.provider-fields { margin-top: 18px; }
.credential-block { margin-top: 18px; padding: 14px; border: 1px solid var(--border); border-radius: 6px; }
.credential-heading { display: flex; align-items: center; gap: 9px; color: var(--accent-strong); }
.credential-heading strong { color: var(--text); font-size: 11px; }
.credential-heading small { margin-top: 3px; color: var(--text-faint); font-size: 9px; }
.secret-input { display: grid; grid-template-columns: minmax(0, 1fr) 38px; margin-top: 11px; }
.secret-input input { min-width: 0; height: 40px; padding: 0 11px; border: 1px solid var(--border); border-radius: 6px 0 0 6px; outline: 0; background: var(--page); color: var(--text); font-size: 11px; }
.secret-input input:focus { border-color: var(--accent); }
.secret-input button { width: 38px; height: 40px; display: grid; place-items: center; border: 1px solid var(--border); border-left: 0; border-radius: 0 6px 6px 0; background: var(--surface-muted); color: var(--text-faint); cursor: pointer; }
.provider-actions { margin-top: auto; }
@media (max-width: 760px) {
  .provider-total { display: none; }
  .provider-layout { grid-template-columns: 1fr; grid-template-rows: minmax(230px, 42dvh) minmax(0, 1fr); }
  .provider-browser { border-right: 0; border-bottom: 1px solid var(--border); }
  .provider-form { padding: 16px 13px; }
  .connection-summary { grid-template-columns: 1fr; }
}
@media (max-width: 420px) {
  .provider-grid { grid-template-columns: 1fr; }
  .provider-identity { grid-template-columns: 38px minmax(0, 1fr); }
  .provider-mark.large { width: 38px; height: 38px; }
  .connection-state { grid-column: 1 / -1; justify-self: start; }
}
</style>
