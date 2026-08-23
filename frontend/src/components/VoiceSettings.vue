<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Check, Play, Save, Square, Volume2, X } from '@lucide/vue'
import { AUTO_VOICE_ID, VOICE_OPTIONS, resolveVoiceForText } from '../lib/voiceCatalog'

const props = defineProps({ agent: { type: Object, required: true }, busy: { type: Boolean, default: false }, error: { type: String, default: '' } })
const emit = defineEmits(['close', 'save'])
const selectedVoice = ref(AUTO_VOICE_ID)
const previewing = ref('')
const previewError = ref('')
let previewAudio, previewUrl = '', previewController

const selectedLabel = computed(() => VOICE_OPTIONS.find((voice) => voice.id === selectedVoice.value)?.name || 'Automatic')
watch(() => props.agent?.voice, (voice) => { selectedVoice.value = voice || AUTO_VOICE_ID }, { immediate: true })

function stopPreview() {
  previewController?.abort(); previewController = undefined
  if (previewAudio) { previewAudio.pause(); previewAudio.src = ''; previewAudio = undefined }
  if (previewUrl) URL.revokeObjectURL(previewUrl)
  previewUrl = ''; previewing.value = ''
}

async function preview(voice) {
  if (previewing.value === voice.id) { stopPreview(); return }
  stopPreview(); previewError.value = ''; previewing.value = voice.id; previewController = new AbortController()
  const sample = voice.sample || 'Good afternoon. How can I help you today?'
  try {
    const response = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: sample, language: voice.nativeLanguage.startsWith('English') ? 'English' : 'Auto', speaker: resolveVoiceForText(sample, voice.id) }), signal: previewController.signal })
    if (!response.ok) throw new Error('Voice preview is unavailable')
    previewUrl = URL.createObjectURL(await response.blob()); previewAudio = new Audio(previewUrl); previewAudio.onended = stopPreview
    await previewAudio.play()
  } catch (error) { if (error.name !== 'AbortError') previewError.value = error.message; stopPreview() }
}

function closeOnEscape(event) { if (event.key === 'Escape' && !props.busy) emit('close') }
onMounted(() => window.addEventListener('keydown', closeOnEscape))
onBeforeUnmount(() => { window.removeEventListener('keydown', closeOnEscape); stopPreview() })
</script>

<template>
  <Teleport to="body">
    <div class="modal-backdrop" @mousedown.self="$emit('close')">
      <section class="voice-modal" role="dialog" aria-modal="true" aria-labelledby="voice-settings-title">
        <header class="agent-modal-header">
          <div><h2 id="voice-settings-title">Voice Settings</h2><p>Choose the voice used for live phone replies.</p></div>
          <button class="icon-button" type="button" title="Close voice settings" aria-label="Close voice settings" :disabled="busy" @click="$emit('close')"><X :size="18" /></button>
        </header>
        <div class="voice-settings-body">
          <div class="voice-settings-intro">
            <span class="voice-settings-icon"><Volume2 :size="20" /></span>
            <div><strong>{{ selectedLabel }}</strong><p>Automatic mode uses Aiden for faster, natural English conversation.</p></div>
          </div>
          <div class="voice-option-list" role="radiogroup" aria-label="Reply voice">
            <label v-for="voice in VOICE_OPTIONS" :key="voice.id" class="voice-option" :class="{ selected: selectedVoice === voice.id }">
              <input v-model="selectedVoice" type="radio" name="reply-voice" :value="voice.id" />
              <span class="voice-option-check"><Check v-if="selectedVoice === voice.id" :size="14" /></span>
              <span class="voice-option-copy"><strong>{{ voice.name }} <em v-if="voice.recommended">Recommended</em></strong><small>{{ voice.nativeLanguage }}</small><span>{{ voice.description }}</span></span>
              <button class="voice-preview" type="button" :title="previewing === voice.id ? `Stop ${voice.name} preview` : `Preview ${voice.name}`" :aria-label="previewing === voice.id ? `Stop ${voice.name} preview` : `Preview ${voice.name}`" @click.prevent="preview(voice)"><Square v-if="previewing === voice.id" :size="13" /><Play v-else :size="14" /></button>
            </label>
          </div>
        </div>
        <footer class="voice-settings-footer">
          <p v-if="previewError || error" role="alert">{{ previewError || error }}</p>
          <button class="secondary-action" type="button" :disabled="busy" @click="$emit('close')">Cancel</button>
          <button class="primary-action" type="button" :disabled="busy" @click="$emit('save', selectedVoice)"><Save :size="16" /> {{ busy ? 'Saving...' : 'Save voice' }}</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>
