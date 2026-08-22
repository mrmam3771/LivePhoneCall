<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { Mic, PhoneOff, Radio, X } from '@lucide/vue'
import { formatDuration } from '../composables/useChatDatabase'

const emit = defineEmits(['close', 'recording-complete'])
const recording = ref(false)
const status = ref('Ready to record / 准备录音')
const elapsed = ref(0)
const levels = ref(Array.from({ length: 24 }, () => 0.08))
const finishing = ref(false)
let capture, timer, animationFrame
let requestToken = 0
const formattedTime = computed(() => formatDuration(elapsed.value))
function drawLevels(activeCapture) { if (capture !== activeCapture) return; const data = new Uint8Array(activeCapture.analyser.frequencyBinCount); activeCapture.analyser.getByteFrequencyData(data); const step = Math.max(1, Math.floor(data.length / levels.value.length)); levels.value = levels.value.map((_, index) => Math.max(0.08, data[index * step] / 255)); animationFrame = requestAnimationFrame(() => drawLevels(activeCapture)) }
async function startRecording() {
  if (recording.value || finishing.value) return
  const token = ++requestToken
  try {
    status.value = 'Requesting microphone...'
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: false })
    if (token !== requestToken) { stream.getTracks().forEach((track) => track.stop()); return }
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : ''
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    recorder.start(250)
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    const audioContext = new AudioContextClass()
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 128
    audioContext.createMediaStreamSource(stream).connect(analyser)
    const activeCapture = { analyser, audioContext, chunks: [], duration: 0, recorder, save: false, stream }
    capture = activeCapture
    recorder.ondataavailable = (event) => { if (event.data.size) activeCapture.chunks.push(event.data) }
    recorder.onstop = () => {
      finishing.value = false
      if (capture === activeCapture) capture = undefined
      if (!activeCapture.save) return
      const blob = new Blob(activeCapture.chunks, { type: recorder.mimeType || 'audio/webm' })
      emit('recording-complete', { blob, mimeType: blob.type, duration: activeCapture.duration })
    }
    recording.value = true; status.value = 'Recording / 正在录音'; elapsed.value = 0
    timer = window.setInterval(() => { elapsed.value += 1 }, 1000); drawLevels(activeCapture)
  } catch (error) { status.value = `Microphone unavailable: ${error.message}`; cleanup() }
}
function stopRecording() { if (!recording.value || !capture) return; const activeCapture = capture; activeCapture.save = true; activeCapture.duration = elapsed.value; recording.value = false; finishing.value = true; status.value = 'Saving voice note...'; window.clearInterval(timer); cancelAnimationFrame(animationFrame); activeCapture.recorder.stop(); activeCapture.stream.getTracks().forEach((track) => track.stop()); activeCapture.audioContext.close() }
function cleanup() { requestToken += 1; window.clearInterval(timer); cancelAnimationFrame(animationFrame); if (capture) { capture.save = false; if (capture.recorder.state === 'recording') capture.recorder.stop(); capture.stream.getTracks().forEach((track) => track.stop()); capture.audioContext.close(); capture = undefined } recording.value = false; finishing.value = false }
function closePanel() { cleanup(); emit('close') }
onBeforeUnmount(cleanup)
</script>

<template>
  <section class="call-panel" aria-label="Phone call controls">
    <div class="call-heading"><div class="call-icon"><Radio :size="18" /></div><div><strong>Voice capture</strong><span>Frontend-only preview</span></div><button class="icon-button" type="button" title="Close phone controls" aria-label="Close phone controls" @click="closePanel"><X :size="17" /></button></div>
    <div class="call-body">
      <div class="call-status"><span :class="{ live: recording }" />{{ status }}</div><time>{{ formattedTime }}</time>
      <div class="waveform" :class="{ live: recording }" aria-label="Microphone level"><i v-for="(_, index) in levels" :key="index" :style="{ height: `${4 + levels[index] * 27}px` }" /></div>
      <button v-if="!recording" class="call-action start" type="button" :disabled="finishing" @click="startRecording"><Mic :size="18" /> {{ finishing ? 'Saving...' : 'Start recording' }}</button>
      <button v-else class="call-action stop" type="button" @click="stopRecording"><PhoneOff :size="18" /> Stop & save</button>
    </div>
  </section>
</template>
