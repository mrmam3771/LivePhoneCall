<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { AudioLines, MessageCircle, ShieldCheck } from '@lucide/vue'
import { formatDuration } from '../composables/useChatDatabase'
import { buildChatBlocks } from '../lib/chatBlocks'
import { createAutoScrollPolicy } from '../lib/autoScrollPolicy'

const props = defineProps({ messages: { type: Array, required: true }, loading: { type: Boolean, default: false }, error: { type: String, default: '' }, pending: { type: Boolean, default: false } })
const audioUrls = new Map()
const autoScroll = createAutoScrollPolicy()
const stream = ref(null)
const blocks = computed(() => buildChatBlocks(props.messages, props.pending))
function scrollToBottom() {
  if (stream.value) stream.value.scrollTop = stream.value.scrollHeight
}
function pauseAutoScroll() {
  autoScroll.pause()
}
function handleScroll() {
  if (!stream.value) return
  const distanceFromBottom = stream.value.scrollHeight - stream.value.clientHeight - stream.value.scrollTop
  if (distanceFromBottom > 4) autoScroll.pause()
}
defineExpose({ scrollToBottom })
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
watch(
  () => props.messages.map((message) => `${message.id}:${message.content?.length || 0}`).join('|'),
  async () => {
    await nextTick()
    if (autoScroll.shouldFollow()) scrollToBottom()
  },
)
watch(() => props.loading, async (loading) => {
  if (!loading) {
    await nextTick()
    scrollToBottom()
  }
})
watch(() => props.pending, async (pending, previousPending) => {
  if (pending && !previousPending) autoScroll.startTask()
  await nextTick()
  if (pending && autoScroll.shouldFollow()) scrollToBottom()
})
</script>

<template>
  <section ref="stream" class="message-stream" aria-live="polite" @wheel.passive="pauseAutoScroll" @touchmove.passive="pauseAutoScroll" @scroll.passive="handleScroll">
    <div v-if="loading" class="loading-state">Loading local conversations...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="!messages.length && !pending" class="empty-chat">
      <div class="empty-icon"><MessageCircle :size="28" /></div><h2>Start a conversation</h2><p>Type a message or open the phone controls to start a live call.</p><div class="privacy-note"><ShieldCheck :size="15" /> Saved in local SQLite</div>
    </div>
    <div v-else class="message-column">
      <article v-for="block in blocks" :key="block.id" class="message" :class="block.role" :aria-label="block.pending ? 'AI is thinking' : undefined">
        <div class="message-meta"><span>{{ block.role === 'user' ? 'You' : 'Qwen Voice' }}</span><time v-if="block.message || block.thinking">{{ messageTime((block.message || block.thinking).createdAt) }}</time></div>
        <details v-if="block.thinking" class="thinking-message"><summary>Thinking process / 思维链</summary><div>{{ block.thinking.content }}</div></details>
        <template v-if="block.message">
          <div v-if="block.message.type === 'audio'" class="audio-message"><AudioLines :size="18" /><div><strong>{{ block.message.content }}</strong><span>{{ formatDuration(block.message.duration) }}</span></div><audio controls preload="metadata" :src="audioSource(block.message)" /></div>
          <div v-else class="message-bubble">{{ block.message.content }}</div>
        </template>
        <div v-if="block.pending && !block.message" class="thinking-placeholder"><span>AI is thinking / AI 思考中</span><span class="thinking-grid" aria-hidden="true"><i v-for="index in 9" :key="index"/></span></div>
      </article>
    </div>
  </section>
</template>
