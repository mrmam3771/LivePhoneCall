<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Mic, PhoneOff, Radio, RefreshCw, Square, X } from '@lucide/vue'
import { createVoiceTurnState } from '../composables/useVoiceTurnState'
import { createSpokenSentenceGuard } from '../lib/spokenSentenceGuard'
import { consumeModelToken } from '../lib/modelTokenParser'
import { resolveVoiceForText } from '../lib/voiceCatalog'
const props = defineProps({ sessionId:String, agent:Object, history:Array, commitUserMessage:Function }); const emit=defineEmits(['close','transcript','assistant','thinking','thinking-state','busy'])
const active=ref(false), responding=ref(false), isThinking=ref(false), status=ref('Connecting microphone...'), microphones=ref([]), selected=ref(localStorage.getItem('qwen-chat-microphone')||''), levels=ref(Array(24).fill(.1))
const voiceTurn=createVoiceTurnState(), callAbort=new AbortController()
let stream,ctx,source,processor,silenceNode,ttsContext,turnAbort,nextTtsAt=0,asrId='',asrStartPromise,pcm=new Float32Array(0),sending=false,spoken=false,silence=0,ended=false,starting=false,audioChain=Promise.resolve()
const SPEAKER_ECHO_COOLDOWN_MS=900
const join=(a,b)=>{const x=new Float32Array(a.length+b.length);x.set(a);x.set(b,a.length);return x}
function resample(a,rate){if(rate===16000)return a;const out=new Float32Array(Math.round(a.length*16000/rate));for(let i=0;i<out.length;i++){const p=i*rate/16000,j=Math.floor(p),n=Math.min(j+1,a.length-1);out[i]=a[j]*(1-p+j)+a[n]*(p-j)}return out}
async function devices(){if(!navigator.mediaDevices?.enumerateDevices){microphones.value=[];status.value='Microphone requires HTTPS on LAN';return}microphones.value=(await navigator.mediaDevices.enumerateDevices()).filter(x=>x.kind==='audioinput');if(!microphones.value.some(x=>x.deviceId===selected.value))selected.value=microphones.value[0]?.deviceId||''}
function release(){processor?.disconnect();source?.disconnect();silenceNode?.disconnect();ctx?.close();stream?.getTracks().forEach(x=>x.stop());processor=source=silenceNode=ctx=stream=undefined;active.value=false}
function setMicrophoneEnabled(enabled){stream?.getAudioTracks().forEach(track=>{track.enabled=enabled})}
async function ensureAsrSession(){if(asrId)return asrId;if(!asrStartPromise)asrStartPromise=fetch('/api/start',{method:'POST',signal:callAbort.signal}).then(async r=>{if(!r.ok)throw Error('ASR session unavailable');const id=(await r.json()).session_id;if(voiceTurn.shouldCapture())asrId=id;return id}).finally(()=>{asrStartPromise=undefined});await asrStartPromise;return asrId}
async function chunk(){if(sending||!voiceTurn.shouldCapture()||!asrId||pcm.length<8000)return;sending=true;const part=pcm.slice(0,8000);pcm=pcm.slice(8000);try{const r=await fetch(`/api/chunk?session_id=${encodeURIComponent(asrId)}`,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:part.buffer,signal:callAbort.signal}),j=await r.json();if(!r.ok)throw Error(j.error);if(j.text)emit('transcript',{text:j.text,partial:true,turnId:asrId})}catch(e){if(e.name!=='AbortError'){status.value=e.message;release()}}finally{sending=false;if(active.value&&voiceTurn.shouldCapture())chunk()}}
function abortableDelay(ms,signal){return new Promise((resolve,reject)=>{const timer=setTimeout(done,ms);function done(){signal?.removeEventListener('abort',cancel);resolve()}function cancel(){clearTimeout(timer);signal?.removeEventListener('abort',cancel);reject(new DOMException('Stopped','AbortError'))}signal?.addEventListener('abort',cancel,{once:true});if(signal?.aborted)cancel()})}
async function tts(text,signal){const r=await fetch('/api/tts/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,language:props.agent?.language||'Auto',speaker:resolveVoiceForText(text,props.agent?.voice)}),signal});if(!r.ok||!r.body)throw Error('TTS unavailable');const rate=Number(r.headers.get('X-Sample-Rate'))||24000;ttsContext||=new AudioContext();const audioContext=ttsContext;if(audioContext.state==='suspended')await audioContext.resume();const reader=r.body.getReader();let pending=new Uint8Array(0),lastEnd=Math.max(nextTtsAt,audioContext.currentTime);while(true){const {done,value}=await reader.read();if(done)break;const bytes=new Uint8Array(pending.length+value.length);bytes.set(pending);bytes.set(value,pending.length);const usable=bytes.length-bytes.length%4;pending=bytes.slice(usable);if(!usable)continue;const samples=new Float32Array(usable/4);samples.set(new Float32Array(bytes.buffer,bytes.byteOffset,usable/4));const buffer=audioContext.createBuffer(1,samples.length,rate);buffer.copyToChannel(samples,0);const audioSource=audioContext.createBufferSource();audioSource.buffer=buffer;audioSource.connect(audioContext.destination);const start=Math.max(audioContext.currentTime+.03,lastEnd);audioSource.start(start);lastEnd=start+buffer.duration}nextTtsAt=lastEnd;const wait=Math.max(0,(lastEnd-audioContext.currentTime)*1000);if(wait)await abortableDelay(wait,signal)}
function queueTts(text,signal){const clean=text.replace(/<\/?think(?:ing)?>/gi,'').trim();if(clean){isThinking.value=false;voiceTurn.beginPlayback();status.value='Assistant is speaking...';audioChain=audioChain.catch(()=>{}).then(()=>tts(clean,signal))}return audioChain}
async function turn(){
  if(!asrId||sending||!voiceTurn.beginTurn())return
  const controller=new AbortController(),sentenceGuard=createSpokenSentenceGuard()
  turnAbort=controller;responding.value=true;emit('busy',true);setMicrophoneEnabled(false)
  const turnAsrId=asrId,turnId=turnAsrId
  asrId='';pcm=new Float32Array(0);spoken=false;silence=0;status.value='Recognizing...'
  let reply='',spokenReply='',finalEmitted=false
  const state={raw:'',thought:'',inThinking:false}
  try{
    const r=await fetch(`/api/finish?session_id=${encodeURIComponent(turnAsrId)}`,{method:'POST',signal:controller.signal}),j=await r.json()
    if(!r.ok)throw Error(j.error||'Recognition failed')
    if(!j.text?.trim())return
    const transcript=j.text.trim()
    emit('transcript',{text:transcript,partial:false,turnId})
    const history=props.commitUserMessage
      ? await props.commitUserMessage({text:transcript,turnId,sessionId:props.sessionId})
      : (props.history||[])
    isThinking.value=true;emit('thinking-state',true);status.value='Waiting for response...'
    const response=await fetch('/api/agent/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:transcript,conversation_id:props.sessionId,history,agent:props.agent}),signal:controller.signal})
    if(!response.ok||!response.body)throw Error('Model request failed')
    const reader=response.body.getReader(),decoder=new TextDecoder();let raw=''
    while(true){
      const {done,value}=await reader.read();if(done)break
      raw+=decoder.decode(value,{stream:true});const blocks=raw.split('\n\n');raw=blocks.pop()
      for(const block of blocks){
        const kind=block.match(/^event: (.+)$/m)?.[1],data=block.match(/^data: (.+)$/m)?.[1]
        if(!kind||!data)continue
        try{
          const piece=JSON.parse(data).text||''
          if(kind==='thinking'){state.thought+=piece;emit('thinking',{text:state.thought,partial:true,turnId})}
          if(kind==='token'){const visible=consumeModelToken(piece,state);if(visible){if(!reply){isThinking.value=false;emit('thinking-state',false);status.value='Assistant is replying...'}reply+=visible}}
        }catch{}
      }
      if(state.thought)emit('thinking',{text:state.thought,partial:true,turnId})
      emit('assistant',{text:reply,partial:true,turnId})
      const match=reply.slice(spokenReply.length).match(/^(.+?[。！？.!?])/)
      if(match){
        if(!sentenceGuard.accept(match[1])){reply=reply.slice(0,spokenReply.length).trimEnd();await reader.cancel();break}
        spokenReply+=match[1];queueTts(match[1],controller.signal)
      }
    }
    if(!state.inThinking&&state.raw)reply+=state.raw
    if(reply.slice(spokenReply.length))await queueTts(reply.slice(spokenReply.length),controller.signal);else await audioChain
    if(state.thought)emit('thinking',{text:state.thought,partial:false,turnId})
    emit('assistant',{text:reply,partial:false,turnId});finalEmitted=true
    if(voiceTurn.phase()==='speaking'){voiceTurn.beginCooldown();status.value='Preparing microphone...';await abortableDelay(SPEAKER_ECHO_COOLDOWN_MS,controller.signal)}
  }catch(e){
    if(e.name==='AbortError'){
      if(state.thought)emit('thinking',{text:state.thought,partial:false,turnId})
      if(reply&&!finalEmitted)emit('assistant',{text:reply,partial:false,turnId})
    }else status.value=e.message
  }finally{
    if(turnAbort===controller){
      turnAbort=undefined;responding.value=false;emit('busy',false);isThinking.value=false;emit('thinking-state',false);spoken=false;silence=0;pcm=new Float32Array(0);setMicrophoneEnabled(true);voiceTurn.finishTurn();if(!ended)status.value='Listening...'
    }
  }
}
async function start(){if(starting)return;starting=true;try{await devices();if(!navigator.mediaDevices?.getUserMedia)return;const nextStream=await navigator.mediaDevices.getUserMedia({audio:{...(selected.value?{deviceId:{exact:selected.value}}:{}),echoCancellation:true,noiseSuppression:true,autoGainControl:true}});if(ended){nextStream.getTracks().forEach(track=>track.stop());return}stream=nextStream;ctx=new AudioContext();source=ctx.createMediaStreamSource(stream);processor=ctx.createScriptProcessor(4096,1,1);silenceNode=ctx.createGain();silenceNode.gain.value=0;active.value=true;processor.onaudioprocess=async e=>{if(!voiceTurn.shouldCapture())return;const input=e.inputBuffer.getChannelData(0),rms=Math.sqrt(input.reduce((s,x)=>s+x*x,0)/input.length);levels.value=levels.value.map((_,i)=>Math.max(.08,Math.min(1,Math.abs(input[(i*137)%input.length])*9)));pcm=join(pcm,resample(input,ctx.sampleRate));await ensureAsrSession();if(!voiceTurn.shouldCapture())return;if(rms>.012){spoken=true;silence=0}else if(spoken)silence+=input.length/ctx.sampleRate;chunk();if(spoken&&silence>.9&&!sending)turn()};source.connect(processor);processor.connect(silenceNode);silenceNode.connect(ctx.destination);status.value='Listening...'}catch(e){if(e.name!=='AbortError')status.value=`Microphone unavailable: ${e.message}`}finally{starting=false}}
async function switchMicrophone(){localStorage.setItem('qwen-chat-microphone',selected.value);if(!active.value)return;status.value='Switching microphone...';const oldSession=asrId;asrId='';pcm=new Float32Array(0);spoken=false;silence=0;release();if(oldSession)fetch(`/api/finish?session_id=${encodeURIComponent(oldSession)}`,{method:'POST'}).catch(()=>{});await start()}
function stopResponse(){if(!turnAbort||turnAbort.signal.aborted)return;const controller=turnAbort;turnAbort=undefined;controller.abort();responding.value=false;isThinking.value=false;emit('thinking-state',false);audioChain=Promise.resolve();nextTtsAt=0;const audioContext=ttsContext;ttsContext=undefined;audioContext?.close().catch(()=>{});setMicrophoneEnabled(true);voiceTurn.interruptTurn();emit('busy',false);if(!ended)status.value='Listening...'}
function close(){if(ended)return;stopResponse();ended=true;voiceTurn.close();callAbort.abort();release();ttsContext?.close();ttsContext=undefined;emit('close')};defineExpose({stopResponse});onMounted(start);onBeforeUnmount(close)
</script>
<template><section class="call-panel"><div class="call-heading"><div class="call-icon"><Radio :size="18" /></div><div><strong>Live phone call</strong><span>Audio is not recorded</span></div><button class="icon-button" type="button" aria-label="End call" @click="close"><X :size="17" /></button></div><label class="microphone-picker"><Mic :size="15"/><span>Microphone</span><select v-model="selected" @change="switchMicrophone"><option v-for="(d,i) in microphones" :key="d.deviceId" :value="d.deviceId">{{ d.label||`Microphone ${i+1}` }}</option></select><button type="button" title="Refresh microphones" aria-label="Refresh microphones" @click="devices"><RefreshCw :size="14"/></button></label><div class="call-body"><div class="call-status"><span :class="{live:active}"/><span class="call-status-text">{{status}}</span></div><div class="waveform" :class="{live:active}"><i v-for="(_,i) in levels" :key="i" :style="{height:`${4+levels[i]*27}px`} "/></div><button class="call-action interrupt" type="button" :disabled="!responding" @click="stopResponse"><Square :size="14" fill="currentColor"/> Stop AI</button><button class="call-action stop" type="button" @click="close"><PhoneOff :size="18"/> End call</button></div></section></template>
