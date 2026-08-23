<script setup>
import { Download, X } from '@lucide/vue'
import { useRegisterSW } from 'virtual:pwa-register/vue'

const { offlineReady, needRefresh, updateServiceWorker } = useRegisterSW()
function close() { offlineReady.value = false; needRefresh.value = false }
</script>

<template>
  <aside v-if="offlineReady || needRefresh" class="pwa-update" role="status" aria-live="polite">
    <div><strong>{{ needRefresh ? 'Update available' : 'App ready' }}</strong><span>{{ needRefresh ? 'Reload when the current call is finished.' : 'The chat interface can now open offline.' }}</span></div>
    <button v-if="needRefresh" class="pwa-update-action" type="button" @click="updateServiceWorker(true)"><Download :size="15" /> Update</button>
    <button class="icon-button" type="button" title="Dismiss" aria-label="Dismiss PWA notification" @click="close"><X :size="16" /></button>
  </aside>
</template>
