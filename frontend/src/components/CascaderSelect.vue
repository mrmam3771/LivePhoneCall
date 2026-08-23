<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from 'vue'
import { Check, ChevronDown, Search, X } from '@lucide/vue'

const props = defineProps({
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Select a model' },
  searchPlaceholder: { type: String, default: 'Search providers and models' },
  emptyText: { type: String, default: 'No matching models' },
  disabled: { type: Boolean, default: false },
  sortByLatest: { type: Boolean, default: true },
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['change', 'open', 'close'])
const model = defineModel({ type: String, default: '' })
const root = useTemplateRef('root')
const trigger = useTemplateRef('trigger')
const panel = useTemplateRef('panel')
const searchInput = useTemplateRef('searchInput')
const open = ref(false)
const query = ref('')
const activeProviderId = ref('')
const panelStyle = ref({})

function timestamp(item) {
  const value = item?.releasedAt || item?.updatedAt || item?.createdAt || 0
  const parsed = typeof value === 'number' ? value : Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function latestInProvider(provider) {
  return Math.max(timestamp(provider), ...((provider.children || []).map(timestamp)), 0)
}

function sortLatest(items, getter = timestamp) {
  if (!props.sortByLatest) return [...items]
  return [...items].sort((a, b) => getter(b) - getter(a) || String(a.label).localeCompare(String(b.label)))
}

const normalizedOptions = computed(() => sortLatest(
  props.options.map((provider) => ({ ...provider, children: sortLatest(provider.children || []) })),
  latestInProvider,
))

const selectedPath = computed(() => {
  for (const provider of normalizedOptions.value) {
    const child = provider.children.find((item) => item.value === model.value)
    if (child) return { provider, child }
  }
  return null
})

const filteredOptions = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return normalizedOptions.value
  return normalizedOptions.value.flatMap((provider) => {
    const providerMatches = `${provider.label} ${provider.description || ''}`.toLocaleLowerCase().includes(needle)
    const children = providerMatches
      ? provider.children
      : provider.children.filter((item) => `${item.label} ${item.value} ${item.description || ''}`.toLocaleLowerCase().includes(needle))
    return children.length ? [{ ...provider, children }] : []
  })
})

const activeProvider = computed(() => filteredOptions.value.find((item) => item.value === activeProviderId.value) || filteredOptions.value[0])

function updatePosition() {
  if (!trigger.value) return
  const rect = trigger.value.getBoundingClientRect()
  const width = Math.min(Math.max(rect.width, 560), window.innerWidth - 20)
  const left = Math.min(Math.max(10, rect.left), window.innerWidth - width - 10)
  const availableBelow = window.innerHeight - rect.bottom - 10
  const placeAbove = availableBelow < 330 && rect.top > availableBelow
  panelStyle.value = {
    width: `${width}px`,
    left: `${left}px`,
    top: placeAbove ? 'auto' : `${rect.bottom + 7}px`,
    bottom: placeAbove ? `${window.innerHeight - rect.top + 7}px` : 'auto',
  }
}

async function show() {
  if (props.disabled || open.value) return
  open.value = true
  query.value = ''
  activeProviderId.value = selectedPath.value?.provider.value || normalizedOptions.value[0]?.value || ''
  updatePosition()
  emit('open')
  await nextTick()
  searchInput.value?.focus()
}

function hide({ restoreFocus = false } = {}) {
  if (!open.value) return
  open.value = false
  query.value = ''
  emit('close')
  if (restoreFocus) nextTick(() => trigger.value?.focus())
}

function choose(provider, child) {
  model.value = child.value
  emit('change', { provider, model: child, value: child.value })
  hide({ restoreFocus: true })
}

function handleDocumentPointer(event) {
  if (!open.value || root.value?.contains(event.target) || panel.value?.contains(event.target)) return
  hide()
}

function handleKeydown(event) {
  if (event.key === 'Escape') hide({ restoreFocus: true })
  if (!open.value && ['Enter', ' ', 'ArrowDown'].includes(event.key) && document.activeElement === trigger.value) {
    event.preventDefault()
    show()
  }
}

function handleViewportChange() {
  if (open.value) updatePosition()
}

watch(filteredOptions, (items) => {
  if (!items.some((item) => item.value === activeProviderId.value)) activeProviderId.value = items[0]?.value || ''
})
document.addEventListener('pointerdown', handleDocumentPointer)
document.addEventListener('keydown', handleKeydown)
window.addEventListener('resize', handleViewportChange)
window.addEventListener('scroll', handleViewportChange, true)
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointer)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleViewportChange)
  window.removeEventListener('scroll', handleViewportChange, true)
})
</script>

<template>
  <div ref="root" class="cascade-select" :class="{ disabled, open, compact }">
    <button
      ref="trigger"
      class="cascade-trigger"
      type="button"
      role="combobox"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :disabled="disabled"
      @click="open ? hide() : show()"
    >
      <span v-if="selectedPath" class="cascade-value">
        <span class="cascade-provider-mark">{{ selectedPath.provider.shortLabel || selectedPath.provider.label.slice(0, 1) }}</span>
        <span class="cascade-value-copy"><strong>{{ selectedPath.child.label }}</strong><small>{{ selectedPath.provider.label }}</small></span>
      </span>
      <span v-else class="cascade-placeholder">{{ placeholder }}</span>
      <ChevronDown :size="16" :class="{ rotated: open }" />
    </button>

    <Teleport to="body">
      <Transition name="cascade-pop">
        <section v-if="open" ref="panel" class="cascade-panel" :style="panelStyle" aria-label="Provider and model selector">
          <header class="cascade-search">
            <Search :size="16" />
            <input ref="searchInput" v-model="query" type="search" :placeholder="searchPlaceholder" aria-label="Search providers and models" />
            <button v-if="query" type="button" aria-label="Clear search" @click="query = ''"><X :size="14" /></button>
          </header>

          <div v-if="filteredOptions.length" class="cascade-columns">
            <div class="cascade-providers" role="listbox" aria-label="Providers">
              <button
                v-for="provider in filteredOptions"
                :key="provider.value"
                type="button"
                role="option"
                :aria-selected="provider.value === activeProvider?.value"
                :class="{ active: provider.value === activeProvider?.value }"
                @mouseenter="activeProviderId = provider.value"
                @focus="activeProviderId = provider.value"
                @click="activeProviderId = provider.value"
              >
                <span class="cascade-provider-mark">{{ provider.shortLabel || provider.label.slice(0, 1) }}</span>
                <span><strong>{{ provider.label }}</strong><small>{{ provider.children.length }} models</small></span>
                <span v-if="provider.badge" class="cascade-badge">{{ provider.badge }}</span>
              </button>
            </div>

            <div class="cascade-models" role="listbox" :aria-label="`${activeProvider?.label || ''} models`">
              <div class="cascade-model-heading"><strong>{{ activeProvider?.label }}</strong><span>Latest first</span></div>
              <button
                v-for="child in activeProvider?.children || []"
                :key="child.value"
                type="button"
                role="option"
                :aria-selected="child.value === model"
                :class="{ selected: child.value === model }"
                @click="choose(activeProvider, child)"
              >
                <span class="cascade-model-copy"><strong>{{ child.label }}</strong><small>{{ child.description || child.value }}</small></span>
                <span v-if="child.badge" class="cascade-badge">{{ child.badge }}</span>
                <Check v-if="child.value === model" :size="16" />
              </button>
            </div>
          </div>
          <div v-else class="cascade-empty">{{ emptyText }}</div>
        </section>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.cascade-select { min-width: 0; position: relative; }
.cascade-trigger { width: 100%; min-width: 0; height: 42px; display: flex; align-items: center; gap: 9px; padding: 0 10px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); color: var(--text); cursor: pointer; text-align: left; }
.cascade-select.compact .cascade-trigger { height: 40px; background: var(--surface-muted); }
.cascade-trigger:hover, .cascade-select.open .cascade-trigger { border-color: var(--accent); }
.cascade-trigger:disabled { cursor: not-allowed; opacity: .55; }
.cascade-trigger > svg { margin-left: auto; flex: 0 0 auto; color: var(--text-faint); transition: transform 160ms ease; }
.cascade-trigger > svg.rotated { transform: rotate(180deg); }
.cascade-value { min-width: 0; display: flex; align-items: center; gap: 9px; }
.cascade-value-copy { min-width: 0; display: flex; flex-direction: column; }
.cascade-value-copy strong, .cascade-value-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cascade-value-copy strong { font-size: 11px; }
.cascade-value-copy small { margin-top: 2px; color: var(--text-faint); font-size: 9px; }
.cascade-placeholder { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-faint); font-size: 11px; }
.cascade-provider-mark { width: 28px; height: 28px; flex: 0 0 auto; display: grid; place-items: center; border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--border)); border-radius: 6px; background: var(--accent-soft); color: var(--accent-strong); font-size: 10px; font-weight: 800; }
.cascade-panel { position: fixed; z-index: 140; max-height: min(470px, calc(100dvh - 20px)); display: grid; grid-template-rows: 48px minmax(0, 1fr); overflow: hidden; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); }
.cascade-search { display: grid; grid-template-columns: 18px minmax(0, 1fr) 28px; align-items: center; gap: 7px; padding: 0 10px 0 13px; border-bottom: 1px solid var(--border); color: var(--text-faint); }
.cascade-search input { min-width: 0; height: 100%; border: 0; outline: 0; background: transparent; color: var(--text); font-size: 11px; }
.cascade-search input::placeholder { color: var(--text-faint); }
.cascade-search input::-webkit-search-cancel-button { display: none; }
.cascade-search button { width: 28px; height: 28px; display: grid; place-items: center; border: 0; border-radius: 5px; background: transparent; color: var(--text-faint); cursor: pointer; }
.cascade-search button:hover { background: var(--surface-muted); color: var(--text); }
.cascade-columns { min-height: 0; display: grid; grid-template-columns: minmax(190px, .78fr) minmax(280px, 1.22fr); }
.cascade-providers, .cascade-models { min-height: 0; overflow-y: auto; padding: 7px; }
.cascade-providers { border-right: 1px solid var(--border); background: var(--sidebar); }
.cascade-providers > button { width: 100%; min-width: 0; height: 48px; display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 8px; padding: 0 8px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; text-align: left; }
.cascade-providers > button:hover, .cascade-providers > button.active { border-color: var(--border); background: var(--surface-muted); }
.cascade-providers > button > span:nth-child(2), .cascade-model-copy { min-width: 0; display: flex; flex-direction: column; }
.cascade-providers strong, .cascade-providers small, .cascade-model-copy strong, .cascade-model-copy small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cascade-providers strong, .cascade-model-copy strong { font-size: 11px; }
.cascade-providers small, .cascade-model-copy small { margin-top: 3px; color: var(--text-faint); font-size: 9px; }
.cascade-model-heading { height: 38px; display: flex; align-items: center; padding: 0 7px; color: var(--text); }
.cascade-model-heading strong { font-size: 11px; }
.cascade-model-heading span { margin-left: auto; color: var(--text-faint); font-size: 9px; text-transform: uppercase; }
.cascade-models > button { width: 100%; min-width: 0; min-height: 52px; display: grid; grid-template-columns: minmax(0, 1fr) auto 18px; align-items: center; gap: 8px; padding: 7px 9px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--text); cursor: pointer; text-align: left; }
.cascade-models > button:hover { background: var(--surface-muted); }
.cascade-models > button.selected { border-color: color-mix(in srgb, var(--accent) 42%, var(--border)); background: var(--accent-soft); }
.cascade-models > button > svg { color: var(--accent-strong); }
.cascade-badge { max-width: 84px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 3px 5px; border: 1px solid var(--border); border-radius: 999px; color: var(--text-soft); font-size: 8px; text-transform: uppercase; }
.cascade-empty { min-height: 170px; display: grid; place-items: center; padding: 20px; color: var(--text-faint); font-size: 11px; }
.cascade-pop-enter-active, .cascade-pop-leave-active { transition: opacity 140ms ease, transform 140ms ease; transform-origin: top; }
.cascade-pop-enter-from, .cascade-pop-leave-to { opacity: 0; transform: translateY(-4px) scale(.99); }
@media (max-width: 620px) {
  .cascade-panel { max-height: min(70dvh, 560px); }
  .cascade-columns { grid-template-columns: 1fr; grid-template-rows: minmax(108px, 34%) minmax(180px, 1fr); }
  .cascade-providers { border-right: 0; border-bottom: 1px solid var(--border); }
  .cascade-providers > button { height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .cascade-pop-enter-active, .cascade-pop-leave-active, .cascade-trigger > svg { transition: none; }
}
</style>
