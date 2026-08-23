<script setup>
import { nextTick, ref } from 'vue'
import { ArrowUp, Phone, Square } from '@lucide/vue'
import CascaderSelect from './CascaderSelect.vue'

defineProps({
  callPanelOpen: { type: Boolean, default: false },
  modelId: { type: String, default: '' },
  modelOptions: { type: Array, default: () => [] },
  generating: { type: Boolean, default: false },
})
const emit = defineEmits(['send', 'stop', 'toggle-call', 'select-model'])
const text = ref('')
const input = ref(null)
function resize() { if (input.value) { input.value.style.height = '0px'; input.value.style.height = `${Math.min(input.value.scrollHeight, 156)}px` } }
async function submit() { const content = text.value.trim(); if (!content) return; emit('send', content); text.value = ''; await nextTick(); resize() }
function handleKeydown(event) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }
</script>

<template>
  <div class="composer-wrap">
    <form class="composer" @submit.prevent="submit">
      <textarea ref="input" v-model="text" rows="1" maxlength="4000" placeholder="Message Qwen Voice..." aria-label="Message" @input="resize" @keydown="handleKeydown" />
      <button class="composer-tool" :class="{ active: callPanelOpen }" type="button" title="Open phone controls" aria-label="Open phone controls" @click="$emit('toggle-call')"><Phone :size="19" /></button>
      <CascaderSelect
        class="composer-model-select"
        compact
        :model-value="modelId"
        :options="modelOptions"
        :disabled="!modelOptions.length"
        placeholder="Choose model"
        @update:model-value="$emit('select-model', $event)"
      />
      <button v-if="generating" class="send-button stop-generation" type="button" title="Stop generating and speech" aria-label="Stop generating and speech" @click="$emit('stop')"><Square :size="13" fill="currentColor" /></button>
      <button v-else class="send-button" type="submit" title="Send message" aria-label="Send message" :disabled="!text.trim()"><ArrowUp :size="18" :stroke-width="2.4" /></button>
    </form>
    <p>Local workspace · Messages save to SQLite</p>
  </div>
</template>
