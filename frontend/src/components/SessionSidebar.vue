<script setup>
import { computed, ref } from 'vue'
import { Database, MessageSquare, Plus, Search, Trash2, Volume2 } from '@lucide/vue'

const props = defineProps({ sessions: { type: Array, required: true }, activeSessionId: { type: String, required: true } })
defineEmits(['create', 'select', 'delete'])
const query = ref('')
const filteredSessions = computed(() => {
  const value = query.value.trim().toLocaleLowerCase()
  return value ? props.sessions.filter((session) => `${session.title} ${session.preview}`.toLocaleLowerCase().includes(value)) : props.sessions
})

function relativeTime(timestamp) {
  const elapsed = Date.now() - timestamp
  if (elapsed < 60_000) return 'Now'
  if (elapsed < 3_600_000) return `${Math.floor(elapsed / 60_000)}m`
  if (elapsed < 86_400_000) return `${Math.floor(elapsed / 3_600_000)}h`
  return new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand-row"><div class="brand-mark"><Volume2 :size="18" /></div><div><strong>Qwen Voice</strong><span>Local workspace</span></div></div>
    <button class="new-session-button" type="button" @click="$emit('create')"><Plus :size="17" /><span>New conversation</span></button>
    <label class="session-search"><Search :size="15" /><input v-model="query" type="search" placeholder="Search conversations" /></label>
    <div class="session-section-heading"><span>Conversations</span><span>{{ filteredSessions.length }}</span></div>
    <nav class="session-list" aria-label="Conversations">
      <div v-for="session in filteredSessions" :key="session.id" class="session-item" :class="{ active: session.id === activeSessionId }">
        <button class="session-select" type="button" @click="$emit('select', session.id)">
          <MessageSquare :size="16" /><span class="session-copy"><span class="session-title">{{ session.title }}</span><span class="session-preview">{{ session.preview }}</span></span><time>{{ relativeTime(session.updatedAt) }}</time>
        </button>
        <button class="session-delete" type="button" :title="`Delete ${session.title}`" :aria-label="`Delete ${session.title}`" @click="$emit('delete', session.id)"><Trash2 :size="14" /></button>
      </div>
    </nav>
    <div class="sidebar-footer"><Database :size="15" /><span>Local conversations</span><span class="storage-note">IndexedDB</span></div>
  </aside>
</template>
