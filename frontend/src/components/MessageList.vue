<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { AudioLines, MessageCircle, ShieldCheck } from '@lucide/vue'
import { formatDuration } from '../composables/useChatDatabase'

const props = defineProps({ messages: { type: Array, required: true }, loading: { type: Boolean, default: false }, error: { type: String, default: '' } })
const audioUrls = new Map()
function audioSource(message) { if (!message.audio) return ''; if (!audioUrls.has(message.id)) audioUrls.set(message.id, URL.createObjectURL(message.audio)); return audioUrls.get(message.id) }
function messageTime(timestamp) { return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
onBeforeUnmount(() => audioUrls.forEach((url) => URL.revokeObjectURL(url)))
watch(() => props.messages.map((message) => message.id), (messageIds) => {
  const currentIds = new Set(messageIds)
  audioUrls.forEach((url, id) => {
    if (!currentIds.has(id)) {
      URL.revokeObjectURL(url)
      audioUrls.delete(id)
    }
  })
})
</script>

<template>
  <section class="message-stream" aria-live="polite">
    <div v-if="loading" class="loading-state">Loading local conversations...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="!messages.length" class="empty-chat">
      <div class="empty-icon"><MessageCircle :size="28" /></div><h2>Start a conversation</h2><p>Type a message or open the phone controls to record a voice note.</p><div class="privacy-note"><ShieldCheck :size="15" /> Stored only in this browser</div>
    </div>
    <div v-else class="message-column">
      <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
        <div class="message-meta"><span>{{ message.role === 'user' ? 'You' : 'Qwen Voice' }}</span><time>{{ messageTime(message.createdAt) }}</time></div>
        <div v-if="message.type === 'audio'" class="audio-message"><AudioLines :size="18" /><div><strong>{{ message.content }}</strong><span>{{ formatDuration(message.duration) }}</span></div><audio controls preload="metadata" :src="audioSource(message)" /></div>
        <div v-else class="message-bubble">{{ message.content }}</div>
      </article>
    </div>
  </section>
</template>
