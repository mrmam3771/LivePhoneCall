# coding=utf-8
# Copyright 2026 The Alibaba Qwen team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Minimal web demo for Qwen3ASRModel Streaming Inference (vLLM backend).

Install:
  pip install qwen-asr[vllm]

Run:
  python streaming/demo_qwen3_asr_vllm_streaming.py
Open:
  http://127.0.0.1:7860
"""
import argparse
import ipaddress
import json
import os
import time
import uuid
from dataclasses import dataclass
from functools import wraps
from typing import Dict, Optional

import numpy as np
from flask import Flask, Response, jsonify, request
from qwen_asr import Qwen3ASRModel
from qwen_asr.model_settings import ModelSettingsError
from qwen_asr.settings_page import SETTINGS_HTML
from qwen_asr.voice_agent import LangChainVoiceAgent, TTSClient, VoiceServiceError


@dataclass
class Session:
    state: object
    created_at: float
    last_seen: float


app = Flask(__name__)

global asr
global UNFIXED_CHUNK_NUM
global UNFIXED_TOKEN_NUM
global CHUNK_SIZE_SEC

SESSIONS: Dict[str, Session] = {}
SESSION_TTL_SEC = 10 * 60
TTS_CLIENT = TTSClient(os.getenv("TTS_SERVICE_URL", "http://127.0.0.1:8001"))
VOICE_AGENT = LangChainVoiceAgent()
TTS_LANGUAGES = {"Auto", "Chinese", "English"}
TTS_SPEAKERS = {
    "Vivian", "Serena", "Ryan", "Aiden", "Dylan", "Eric", "Uncle_Fu", "Ono_Anna", "Sohee"
}


def _gc_sessions():
    now = time.time()
    dead = [sid for sid, s in SESSIONS.items() if now - s.last_seen > SESSION_TTL_SEC]
    for sid in dead:
        try:
            asr.finish_streaming_transcribe(SESSIONS[sid].state)
        except Exception:
            pass
        SESSIONS.pop(sid, None)


def _get_session(session_id: str) -> Optional[Session]:
    _gc_sessions()
    s = SESSIONS.get(session_id)
    if s:
        s.last_seen = time.time()
    return s


def local_settings_only(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        host_header = request.host.lower()
        host = host_header[1:].split("]", 1)[0] if host_header.startswith("[") else host_header.split(":", 1)[0]
        try:
            is_loopback = ipaddress.ip_address(request.remote_addr or "").is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback or host not in {"127.0.0.1", "localhost", "::1"}:
            return jsonify({"error": "settings are only available from localhost"}), 403
        return view(*args, **kwargs)

    return wrapped


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Qwen3 Voice Agent</title>
  <style>
    :root{
      --bg:#090b0f;
      --card:#11151b;
      --panel:#151a21;
      --surface:#0d1117;
      --muted:#a6b0bf;
      --text:#f2f5f9;
      --border:#2a323d;
      --ok:#34d399;
      --warn:#fbbf24;
      --danger:#fb7185;
    }

    html, body { height: 100%; }

    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Noto Sans";
      background: var(--bg);
      color:var(--text);
    }

    .wrap{
      height: 100vh;
      max-width: none;
      margin: 0;
      padding: 16px;
      box-sizing: border-box;
      display: flex;
    }

    .card{
      width: 100%;
      height: 100%;
      background: var(--card);
      border:1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      box-sizing: border-box;
      box-shadow: 0 12px 36px rgba(0,0,0,.34);

      display: flex;
      flex-direction: column;
      gap: 12px;
      min-height: 0;
    }

    h1{ font-size: 16px; margin: 0; color:#ffffff; letter-spacing:.2px;}
    .page-head{display:flex;align-items:center;gap:12px;}
    .page-head a{margin-left:auto;border:1px solid var(--border);border-radius:6px;padding:7px 10px;background:var(--panel);}

    .row{ display:flex; gap:12px; align-items:center; flex-wrap: wrap; }

    .recording-info{
      display:flex;
      align-items:center;
      gap:10px;
      min-height: 24px;
      color:var(--muted);
      font-size:12px;
    }
    .microphone-row{
      display:flex;
      align-items:center;
      gap:10px;
      color:var(--muted);
      font-size:12px;
    }
    select{
      min-width:280px;
      max-width:100%;
      border:1px solid var(--border);
      border-radius:8px;
      padding:8px 10px;
      color:var(--text);
      background:#1b222c;
    }
    select:disabled{ opacity:.6; }
    .level-track{
      width:120px;
      height:6px;
      border-radius:999px;
      overflow:hidden;
      background:#252d38;
    }
    .level-fill{
      width:100%;
      height:100%;
      transform:scaleX(0);
      transform-origin:left center;
      background:var(--ok);
      transition:transform .08s linear;
    }

    button{
      border:1px solid var(--border); border-radius: 8px;
      padding: 10px 14px; cursor:pointer; color:var(--text);
      background: #1b222c;
      transition: transform .05s ease, background .15s ease, border-color .15s ease;
      font-weight: 700;
    }
    button:hover{ background: #262f3b; border-color:#4b5868; }
    button:active{ transform: translateY(1px); }
    button.primary{ color:#d1fae5; border-color: rgba(52,211,153,.5); background: rgba(16,185,129,.14); }
    button.danger{ color:#ffe4e6; border-color: rgba(251,113,133,.5); background: rgba(244,63,94,.14); }
    button:disabled{ opacity:.5; cursor:not-allowed; }

    .pill{
      font-size: 12px; padding: 6px 10px; border-radius: 999px;
      border:1px solid var(--border); color: var(--muted);
      background: #1b222c;
      user-select:none;
    }
    .pill.ok{ color: #a7f3d0; border-color: rgba(52,211,153,.5); background: rgba(16,185,129,.14); }
    .pill.warn{ color: #fde68a; border-color: rgba(251,191,36,.5); background: rgba(245,158,11,.14); }
    .pill.err{ color: #fecdd3; border-color: rgba(251,113,133,.5); background: rgba(244,63,94,.14); }

    .panel{
      border:1px solid var(--border);
      border-radius: 8px;
      background: var(--panel);
      padding: 12px;
    }

    .panel.textpanel{
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }

    .label{ color:var(--muted); font-size: 12px; margin-bottom: 6px; }
    .mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New"; }

    #text, #agentText{
      flex: 1;
      min-height: 0;
      white-space: pre-wrap;
      line-height: 1.6;
      font-size: 15px;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--surface);
      overflow: auto;
    }

    .conversation-grid{
      flex: 1;
      display:grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap:12px;
      min-height:0;
    }
    .agent-controls{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    .agent-controls input[type="text"]{
      flex:1;
      min-width:220px;
      border:1px solid var(--border);
      border-radius:8px;
      padding:9px 10px;
      color:var(--text);
      background:var(--surface);
    }
    .agent-controls select{ min-width:120px; }
    audio{ width:min(420px, 100%); height:36px; }
    @media (max-width: 760px){
      .conversation-grid{ grid-template-columns:1fr; }
      .card{ overflow:auto; }
      .textpanel{ min-height:180px; }
      .microphone-row{ flex-wrap:wrap; }
      .microphone-row select{ width:100%; min-width:0; }
    }

    a{ color: #7dd3fc; text-decoration:none; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="page-head">
        <h1>Qwen3 Voice Agent</h1>
        <a href="/settings">Settings / 设置</a>
      </div>

      <div class="microphone-row">
        <label for="micSelect">Microphone / 麦克风</label>
        <select id="micSelect"><option value="">Loading microphones / 正在读取麦克风</option></select>
      </div>

      <div class="row">
        <button id="btnStart" class="primary">Start / 开始</button>
        <button id="btnStop" class="danger" disabled>Stop / 停止</button>
        <span id="status" class="pill warn">Idle / 未开始</span>
        <a href="javascript:void(0)" id="btnClear" class="mono" style="margin-left:auto;">Clear / 清空</a>
      </div>

      <div class="recording-info" aria-live="polite">
        <span id="recordingState">Microphone idle / 麦克风未启动</span>
        <div class="level-track" aria-label="Microphone level"><div id="levelFill" class="level-fill"></div></div>
        <span id="recordingTime" class="mono">00:00</span>
        <span id="serverState" class="mono">Server input: waiting</span>
      </div>

      <div class="panel">
        <div class="label">Language / 语言</div>
        <div id="lang" class="mono">—</div>
      </div>

      <div class="agent-controls">
        <label><input id="autoAgent" type="checkbox" checked /> Agent reply + speech / 自动回复并朗读</label>
        <span id="voiceStatus" class="pill warn">Voice service / 语音服务</span>
      </div>

      <div class="conversation-grid">
        <div class="panel textpanel">
          <div class="label">Caller / 来电者</div>
          <div id="text"></div>
        </div>
        <div class="panel textpanel">
          <div class="label">Agent / 智能体</div>
          <div id="agentText"></div>
        </div>
      </div>

      <div class="panel agent-controls">
        <input id="ttsInput" type="text" value="你好，这是 Qwen3-TTS 电话语音测试。" aria-label="Text to speak" />
        <select id="ttsLanguage" aria-label="TTS language">
          <option value="Auto">Auto</option>
          <option value="Chinese">中文</option>
          <option value="English">English</option>
        </select>
        <select id="ttsSpeaker" aria-label="TTS speaker">
          <option>Vivian</option><option>Serena</option><option>Ryan</option><option>Aiden</option>
          <option>Dylan</option><option>Eric</option><option>Uncle_Fu</option><option>Ono_Anna</option><option>Sohee</option>
        </select>
        <button id="btnSpeak">Speak / 试听</button>
        <audio id="player" controls></audio>
      </div>
    </div>
  </div>

<script>
(() => {
  const $ = (id) => document.getElementById(id);

  const btnStart = $("btnStart");
  const btnStop  = $("btnStop");
  const btnClear = $("btnClear");
  const statusEl = $("status");
  const langEl   = $("lang");
  const textEl   = $("text");
  const recordingStateEl = $("recordingState");
  const recordingTimeEl = $("recordingTime");
  const levelFillEl = $("levelFill");
  const serverStateEl = $("serverState");
  const micSelect = $("micSelect");
  const autoAgent = $("autoAgent");
  const voiceStatusEl = $("voiceStatus");
  const agentTextEl = $("agentText");
  const ttsInput = $("ttsInput");
  const ttsLanguage = $("ttsLanguage");
  const ttsSpeaker = $("ttsSpeaker");
  const btnSpeak = $("btnSpeak");
  const player = $("player");

  const CHUNK_MS = 500;
  const TARGET_SR = 16000;

  let audioCtx = null;
  let processor = null;
  let source = null;
  let mediaStream = null;

  let sessionId = null;
  let running = false;
  let conversationId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());

  let buf = new Float32Array(0);
  let pushing = false;
  let recordedSamples = 0;
  let activeMicLabel = "";

  function isVirtualMicrophone(label){
    return /virtual|虚拟|网易|voicemeeter|stereo mix|立体声混音|cable/i.test(label || "");
  }

  async function refreshMicrophones(){
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices){
      micSelect.innerHTML = '<option value="">Microphone API unavailable / 麦克风接口不可用</option>';
      return;
    }

    const previous = micSelect.value;
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === "audioinput");
    micSelect.innerHTML = "";
    devices.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = device.deviceId;
      option.textContent = device.label || ("Microphone " + (index + 1));
      micSelect.appendChild(option);
    });

    const previousStillExists = devices.some(device => device.deviceId === previous);
    const preferred = devices.find(device =>
      device.deviceId !== "default" &&
      device.deviceId !== "communications" &&
      !isVirtualMicrophone(device.label)
    );
    if (previousStillExists && !isVirtualMicrophone(devices.find(device => device.deviceId === previous)?.label)){
      micSelect.value = previous;
    }else if (preferred){
      micSelect.value = preferred.deviceId;
    }
  }

  function formatDuration(seconds){
    const total = Math.floor(seconds);
    return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0");
  }

  function updateRecordingInfo(message){
    recordingStateEl.textContent = message;
    recordingTimeEl.textContent = formatDuration(recordedSamples / TARGET_SR);
  }

  function updateLevel(samples){
    let sum = 0;
    for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
    const rms = Math.sqrt(sum / Math.max(samples.length, 1));
    levelFillEl.style.transform = "scaleX(" + Math.min(1, Math.max(0, rms * 8)) + ")";
  }

  function setStatus(text, cls){
    statusEl.textContent = text;
    statusEl.className = "pill " + (cls || "");
  }

  function lockUI(on){
    btnStart.disabled = on;
    btnStop.disabled = !on;
    micSelect.disabled = on;
  }

  function concatFloat32(a, b){
    const out = new Float32Array(a.length + b.length);
    out.set(a, 0);
    out.set(b, a.length);
    return out;
  }

  function resampleLinear(input, srcSr, dstSr){
    if (srcSr === dstSr) return input;
    const ratio = dstSr / srcSr;
    const outLen = Math.max(0, Math.round(input.length * ratio));
    const out = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++){
      const x = i / ratio;
      const x0 = Math.floor(x);
      const x1 = Math.min(x0 + 1, input.length - 1);
      const t = x - x0;
      out[i] = input[x0] * (1 - t) + input[x1] * t;
    }
    return out;
  }

  async function apiStart(){
    const r = await fetch("/api/start", {method:"POST"});
    if(!r.ok) throw new Error(await r.text());
    const j = await r.json();
    sessionId = j.session_id;
  }

  async function apiPushChunk(float32_16k){
    const r = await fetch("/api/chunk?session_id=" + encodeURIComponent(sessionId), {
      method: "POST",
      headers: {"Content-Type":"application/octet-stream"},
      body: float32_16k.buffer
    });
    if(!r.ok) throw new Error(await r.text());
    return await r.json();
  }

  async function apiFinish(){
    const r = await fetch("/api/finish?session_id=" + encodeURIComponent(sessionId), {method:"POST"});
    if(!r.ok) throw new Error(await r.text());
    return await r.json();
  }

  async function playSpeech(text){
    voiceStatusEl.textContent = "Synthesizing / 正在合成";
    voiceStatusEl.className = "pill warn";
    const r = await fetch("/api/tts", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text, language:ttsLanguage.value, speaker:ttsSpeaker.value})
    });
    if(!r.ok) throw new Error(await r.text());
    const audio = await r.blob();
    if (player.src) URL.revokeObjectURL(player.src);
    player.src = URL.createObjectURL(audio);
    try{
      await player.play();
      voiceStatusEl.textContent = "Speaking / 播放中";
      voiceStatusEl.className = "pill ok";
    }catch(err){
      if (err?.name !== "NotAllowedError") throw err;
      voiceStatusEl.textContent = "Audio ready · Tap play / 音频已就绪，请点击播放";
      voiceStatusEl.className = "pill warn";
    }
  }

  async function runAgentTurn(text){
    agentTextEl.textContent = "Thinking / 思考中";
    const r = await fetch("/api/agent/chat", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text, conversation_id:conversationId})
    });
    if(!r.ok) throw new Error(await r.text());
    const j = await r.json();
    conversationId = j.conversation_id;
    agentTextEl.textContent = j.reply;
    await playSpeech(j.reply);
  }

  async function refreshVoiceHealth(){
    try{
      const r = await fetch("/api/voice/health", {cache:"no-store"});
      const j = await r.json();
      const agentMode = j.agent?.mode === "langchain" ? "LangChain" : "Echo";
      voiceStatusEl.textContent = j.tts?.ready ? "TTS ready · " + agentMode : "TTS loading/offline · " + agentMode;
      voiceStatusEl.className = "pill " + (j.tts?.ready ? "ok" : "warn");
    }catch(err){
      voiceStatusEl.textContent = "Voice service unavailable / 语音服务不可用";
      voiceStatusEl.className = "pill err";
    }
  }

  btnClear.onclick = () => {
    textEl.textContent = "";
    agentTextEl.textContent = "";
    conversationId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
  };
  btnSpeak.onclick = async () => {
    try{
      await playSpeech(ttsInput.value.trim());
    }catch(err){
      console.error(err);
      voiceStatusEl.textContent = "TTS failed / 合成失败";
      voiceStatusEl.className = "pill err";
      setStatus("TTS failed / 合成失败: " + err.message, "err");
    }
  };

  async function stopAudioPipeline(){
    try{
      if (processor){ processor.disconnect(); processor.onaudioprocess = null; }
      if (source) source.disconnect();
      if (audioCtx) await audioCtx.close();
      if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
    }catch(e){}
    processor = null; source = null; audioCtx = null; mediaStream = null;
    levelFillEl.style.transform = "scaleX(0)";
  }

  btnStart.onclick = async () => {
    if (running) return;

    textEl.textContent = "";
    langEl.textContent = "—";
    buf = new Float32Array(0);
    recordedSamples = 0;
    serverStateEl.textContent = "Server input: waiting";
    updateRecordingInfo("Requesting microphone / 正在请求麦克风权限");

    try{
      setStatus("Starting… / 启动中…", "warn");
      lockUI(true);

      const labelsAreHidden = Array.from(micSelect.options).every(option =>
        !option.textContent || /^Microphone \d+$/.test(option.textContent)
      );
      if (labelsAreHidden){
        const permissionStream = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
        permissionStream.getTracks().forEach(track => track.stop());
        await refreshMicrophones();
      }

      const selectedDeviceId = micSelect.value;
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          ...(selectedDeviceId ? {deviceId: {exact: selectedDeviceId}} : {}),
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        },
        video: false
      });

      const audioTrack = mediaStream.getAudioTracks()[0];
      activeMicLabel = audioTrack?.label || "Selected microphone / 已选麦克风";
      await refreshMicrophones();
      await apiStart();

      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      await audioCtx.resume();
      source = audioCtx.createMediaStreamSource(mediaStream);

      processor = audioCtx.createScriptProcessor(4096, 1, 1);
      const chunkSamples = Math.round(TARGET_SR * (CHUNK_MS / 1000));

      processor.onaudioprocess = (e) => {
        if (!running) return;
        const input = e.inputBuffer.getChannelData(0);
        updateLevel(input);
        const resampled = resampleLinear(input, audioCtx.sampleRate, TARGET_SR);
        buf = concatFloat32(buf, resampled);
        recordedSamples += resampled.length;
        updateRecordingInfo("Recording / 录音中: " + activeMicLabel);
        if (!pushing) pump();
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      running = true;
      setStatus("Listening… / 识别中…", "ok");
      updateRecordingInfo("Recording / 录音中: " + activeMicLabel);

    }catch(err){
      console.error(err);
      setStatus("Start failed / 启动失败: " + err.message, "err");
      lockUI(false);
      running = false;
      sessionId = null;
      await stopAudioPipeline();
      updateRecordingInfo("Microphone unavailable / 麦克风不可用");
    }
  };

  async function pump(){
    if (pushing) return;
    pushing = true;

    const chunkSamples = Math.round(TARGET_SR * (CHUNK_MS / 1000));

    try{
      while (running && buf.length >= chunkSamples){
        const chunk = buf.slice(0, chunkSamples);
        buf = buf.slice(chunkSamples);

        const j = await apiPushChunk(chunk);
        langEl.textContent = j.language || "—";
        textEl.textContent = j.text || "";
        const serverLevel = (j.input_rms || 0).toFixed(3);
        const serverPeak = (j.input_peak || 0).toFixed(3);
        if ((j.input_peak || 0) < 0.0001){
          serverStateEl.textContent = "No microphone signal / 未收到麦克风声音，请选择其他麦克风";
        }else{
          serverStateEl.textContent = "Server input: RMS " + serverLevel + " / peak " + serverPeak;
        }
        if (j.text) updateRecordingInfo("Speech recognized / 已识别到语音");
        if (running) setStatus("Listening… / 识别中…", "ok");
      }
    }catch(err){
      console.error(err);
      if (running) setStatus("Backend error / 后端错误: " + err.message, "err");
    }finally{
      pushing = false;
    }
  }

  btnStop.onclick = async () => {
    if (!running) return;

    running = false;
    setStatus("Finishing… / 收尾中…", "warn");
    updateRecordingInfo("Finalizing recording / 正在完成录音");
    lockUI(false);

    await stopAudioPipeline();

    try{
      let finalText = textEl.textContent.trim();
      if (sessionId){
        const j = await apiFinish();
        langEl.textContent = j.language || "—";
        textEl.textContent = j.text || "";
        finalText = (j.text || "").trim();
      }
      setStatus("Stopped / 已停止", "");
      updateRecordingInfo("Recording stopped / 录音已停止");
      if (autoAgent.checked && finalText){
        setStatus("Agent responding / 智能体回复中", "warn");
        await runAgentTurn(finalText);
        setStatus("Turn complete / 本轮完成", "ok");
      }
    }catch(err){
      console.error(err);
      setStatus("Finish failed / 收尾失败: " + err.message, "err");
    }finally{
      sessionId = null;
      buf = new Float32Array(0);
      pushing = false;
    }
  };

  refreshMicrophones().catch(err => {
    console.error(err);
    micSelect.innerHTML = '<option value="">Unable to list microphones / 无法读取麦克风</option>';
  });
  refreshVoiceHealth();
  setInterval(refreshVoiceHealth, 15000);
  navigator.mediaDevices?.addEventListener?.("devicechange", () => refreshMicrophones());
})();
</script>
</body>
</html>
"""


@app.get("/")
def index():
    response = Response(INDEX_HTML, mimetype="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/settings")
@local_settings_only
def settings_page():
    response = Response(SETTINGS_HTML, mimetype="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.post("/api/start")
def api_start():
    session_id = uuid.uuid4().hex
    state = asr.init_streaming_state(
        unfixed_chunk_num=UNFIXED_CHUNK_NUM,
        unfixed_token_num=UNFIXED_TOKEN_NUM,
        chunk_size_sec=CHUNK_SIZE_SEC,
    )
    now = time.time()
    SESSIONS[session_id] = Session(state=state, created_at=now, last_seen=now)
    return jsonify({"session_id": session_id})


@app.post("/api/chunk")
def api_chunk():
    session_id = request.args.get("session_id", "")
    s = _get_session(session_id)
    if not s:
        return jsonify({"error": "invalid session_id"}), 400

    if request.mimetype != "application/octet-stream":
        return jsonify({"error": "expect application/octet-stream"}), 400

    raw = request.get_data(cache=False)
    if len(raw) % 4 != 0:
        return jsonify({"error": "float32 bytes length not multiple of 4"}), 400

    wav = np.frombuffer(raw, dtype=np.float32).reshape(-1)
    input_rms = float(np.sqrt(np.mean(np.square(wav)))) if wav.size else 0.0
    input_peak = float(np.max(np.abs(wav))) if wav.size else 0.0

    asr.streaming_transcribe(wav, s.state)

    return jsonify(
        {
            "language": getattr(s.state, "language", "") or "",
            "text": getattr(s.state, "text", "") or "",
            "input_rms": input_rms,
            "input_peak": input_peak,
        }
    )


@app.post("/api/finish")
def api_finish():
    session_id = request.args.get("session_id", "")
    s = _get_session(session_id)
    if not s:
        return jsonify({"error": "invalid session_id"}), 400

    asr.finish_streaming_transcribe(s.state)
    out = {
        "language": getattr(s.state, "language", "") or "",
        "text": getattr(s.state, "text", "") or "",
    }
    SESSIONS.pop(session_id, None)
    return jsonify(out)


@app.get("/api/voice/health")
def api_voice_health():
    return jsonify({"tts": TTS_CLIENT.health(), "agent": VOICE_AGENT.status()})


@app.get("/api/settings")
@local_settings_only
def api_settings():
    return jsonify(VOICE_AGENT.settings_store.public_settings())


@app.put("/api/settings/provider")
@local_settings_only
def api_save_provider():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(VOICE_AGENT.settings_store.save_provider(payload))
    except (ModelSettingsError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/settings/active")
@local_settings_only
def api_set_active_provider():
    payload = request.get_json(silent=True) or {}
    try:
        settings = VOICE_AGENT.settings_store.set_active(str(payload.get("provider_id") or ""))
        return jsonify(settings)
    except ModelSettingsError as exc:
        return jsonify({"error": str(exc)}), 400


@app.delete("/api/settings/provider/<provider_id>")
@local_settings_only
def api_delete_provider(provider_id: str):
    try:
        return jsonify(VOICE_AGENT.settings_store.delete_provider(provider_id))
    except ModelSettingsError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/settings/test")
@local_settings_only
def api_test_provider():
    payload = request.get_json(silent=True) or {}
    started = time.perf_counter()
    try:
        reply = VOICE_AGENT.test_connection(payload)
    except (ModelSettingsError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Model provider connection test failed")
        return jsonify({"error": str(exc)}), 502
    return jsonify(
        {
            "ok": True,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "reply": reply,
        }
    )


@app.post("/api/tts")
def api_tts():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    language = str(payload.get("language") or "Auto")
    speaker = str(payload.get("speaker") or "Vivian")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 800:
        return jsonify({"error": "text exceeds 800 characters"}), 400
    if language not in TTS_LANGUAGES:
        return jsonify({"error": "language must be Auto, Chinese, or English"}), 400
    if speaker not in TTS_SPEAKERS:
        return jsonify({"error": "unsupported speaker"}), 400
    try:
        audio = TTS_CLIENT.synthesize(
            text=text,
            language=language,
            speaker=speaker,
        )
    except VoiceServiceError as exc:
        return jsonify({"error": str(exc)}), 503
    return Response(audio, mimetype="audio/wav", headers={"Cache-Control": "no-store"})


@app.post("/api/tts/stream")
def api_tts_stream():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    language = str(payload.get("language") or "Auto")
    speaker = str(payload.get("speaker") or "Vivian")
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 800:
        return jsonify({"error": "text exceeds 800 characters"}), 400
    if language not in TTS_LANGUAGES:
        return jsonify({"error": "language must be Auto, Chinese, or English"}), 400
    if speaker not in TTS_SPEAKERS:
        return jsonify({"error": "unsupported speaker"}), 400

    def generate():
        try:
            for audio, sample_rate in TTS_CLIENT.synthesize_stream(text, language, speaker):
                yield audio
        except VoiceServiceError as exc:
            app.logger.error("Streaming TTS failed: %s", exc)

    return Response(generate(), mimetype="audio/pcm", headers={"Cache-Control": "no-store", "X-Audio-Format": "f32le", "X-Sample-Rate": "24000"})


@app.post("/api/agent/chat")
def api_agent_chat():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    conversation_id = str(payload.get("conversation_id") or uuid.uuid4().hex)
    raw_history = payload.get("history")
    history = None
    if not text:
        return jsonify({"error": "text is required"}), 400
    if len(text) > 4000:
        return jsonify({"error": "text exceeds 4000 characters"}), 400
    if raw_history is not None:
        if not isinstance(raw_history, list):
            return jsonify({"error": "history must be a list"}), 400
        history = []
        for item in raw_history[-24:]:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                return jsonify({"error": "history contains an invalid message"}), 400
            content = str(item.get("content") or "").strip()
            if not content or len(content) > 4000:
                return jsonify({"error": "history contains invalid content"}), 400
            history.append({"role": item["role"], "content": content})
    try:
        reply = VOICE_AGENT.chat(text, conversation_id, history=history)
    except Exception as exc:
        app.logger.exception("LangChain voice agent failed")
        return jsonify({"error": str(exc)}), 502
    return jsonify(
        {
            "conversation_id": conversation_id,
            "reply": reply,
            "agent": VOICE_AGENT.status(),
        }
    )


@app.post("/api/agent/stream")
def api_agent_stream():
    """Server-sent text chunks used by the Vue phone-call experience."""
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    conversation_id = str(payload.get("conversation_id") or uuid.uuid4().hex)
    history = payload.get("history") or []
    agent = payload.get("agent") if isinstance(payload.get("agent"), dict) else None
    if not text:
        return jsonify({"error": "text is required"}), 400
    if not isinstance(history, list):
        return jsonify({"error": "history must be a list"}), 400

    def events():
        try:
            yield f"event: meta\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"
            for kind, chunk in VOICE_AGENT.stream_chat(text, conversation_id, history=history[-24:], agent=agent, with_kinds=True):
                yield f"event: {kind}\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as exc:
            app.logger.exception("Streaming LangChain voice agent failed")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return Response(events(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def parse_args():
    p = argparse.ArgumentParser(description="Qwen3-ASR Streaming Web Demo (vLLM backend)")
    p.add_argument("--asr-model-path", default="Qwen/Qwen3-ASR-1.7B", help="Model name or local path")
    p.add_argument("--host", default="0.0.0.0", help="Bind host")
    p.add_argument("--port", type=int, default=8000, help="Bind port")
    p.add_argument("--gpu-memory-utilization", type=float, default=0.8, help="vLLM GPU memory utilization")
    p.add_argument(
        "--max-model-len",
        type=int,
        default=24576,
        help="Maximum vLLM context length; reduce this when GPU KV-cache memory is limited",
    )

    p.add_argument("--unfixed-chunk-num", type=int, default=2)
    p.add_argument("--unfixed-token-num", type=int, default=5)
    p.add_argument("--chunk-size-sec", type=float, default=1.0)
    return p.parse_args()


def main():
    args = parse_args()

    global asr
    global UNFIXED_CHUNK_NUM
    global UNFIXED_TOKEN_NUM
    global CHUNK_SIZE_SEC

    UNFIXED_CHUNK_NUM = args.unfixed_chunk_num
    UNFIXED_TOKEN_NUM = args.unfixed_token_num
    CHUNK_SIZE_SEC = args.chunk_size_sec

    asr = Qwen3ASRModel.LLM(
        model=args.asr_model_path,
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        max_new_tokens=32,
    )
    print("Model loaded.")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
