# 中英文实时对话 TTS 选择（2026-08）

更新日期：2026-08-22

## 结论

本项目当前的 Qwen3-TTS 0.6B 并不是“没有流式”：`qwen3-tts-service/app.py` 调用 `generate_custom_voice_streaming(..., chunk_size=4)`，并以 float32 PCM 分块返回。实际体感慢，至少还受两项应用结构影响：

1. `CallPanel.vue` 每遇到一个完整句子，就重新发起一次 `/api/tts/stream` HTTP 请求；一个回答有多句时，会重复支付请求、调度和模型生成启动成本。
2. `QwenTTSService` 用一个全局 `threading.Lock` 包住整次流式生成，所有合成请求严格串行；同时本机 GPU 还运行 ASR，TTS 的延迟会受到显存与算力争用影响。

因此，优先建议不是立即删除 Qwen3-TTS，而是做两条 A/B 路径：

1. **最快得到可用电话体验：接入国内云端的 Qwen3-TTS Realtime 或 MiniMax Speech 2.8 Turbo，并保持一条长连接 WebSocket。** 这能绕开本机 ASR/TTS 争抢 GPU，也能把 LLM 的稳定文本片段持续喂给同一 TTS 会话。
2. **坚持本地：先测试 Fun-CosyVoice3 0.5B；MOSS-TTS-Realtime 作为第二候选。** CosyVoice 与当前模型规模相近且官方明确支持 text-in/audio-out 双流式；MOSS 更贴合多轮语音 Agent，但模型更大，官方 180 ms 数据来自 L20，未必适合当前共享消费级 GPU。

海外云中，**Cartesia Sonic 3.5** 的协议最适合可中断电话 Agent；**ElevenLabs Flash v2.5** 有明确约 75 ms 模型推理口径。两者从中国大陆访问时，网络 RTT、抖动和服务路由可能抵消模型优势，必须在真实 4G/5G 与 Wi-Fi 下实测。

## 指标不能直接横比

- **模型推理延迟**只包含模型计算。ElevenLabs 明确说明约 75 ms 不包含网络与应用延迟。[官方模型文档](https://elevenlabs.io/docs/overview/models)
- **TTFB/TTFA**可能指首字节、首个音频块或首个可播放音频，厂商定义不完全一致。
- **RTF**是生成耗时除以音频时长；RTF 小于 1 只代表整体生成快于播放，不保证第一块音频来得快。
- **端到端首声**还包括 VAD 判停、ASR final、LLM 首个稳定短语、TTS 首包、网络和播放器缓冲。电话体验应以“用户停说到听见 AI 第一声”的 P50/P95 为主指标。
- 下表的数字只保留官方明确发布的口径。没有官方数字时写“未公布”，不做推算。

## 候选对比

| 方案 | 中英支持 | 真流式与电话能力 | 官方延迟口径 | 部署与许可 | 适合当前项目的判断 |
|---|---|---|---|---|---|
| **Alibaba Qwen3-TTS Realtime** | 明确支持中文、英文与混合语言自动判断 | WebSocket；`input_text_buffer.append` 增量文本，`response.audio.delta` 增量音频；`commit` 为最低延迟，`server_commit` 自动分段 | 未公布可横比的统一 TTFA | 托管 API；客户端事件和模型由 Model Studio 管理 | **国内云首选。** 与现有 Qwen 栈最接近，迁移工作量低；使用持久会话可消除当前逐句 HTTP 建连/调度开销。[交互流程](https://www.alibabacloud.com/help/en/model-studio/interactive-process-of-qwen-tts-realtime-synthesis) / [客户端事件](https://www.alibabacloud.com/help/en/model-studio/qwen-tts-realtime-client-events) |
| **MiniMax Speech 2.8 Turbo** | 官方列出 40 种语言，接口支持 `language_boost`，示例包含 Chinese；中英文均在支持范围 | WebSocket `task_start` / `task_continue` / 音频分块返回，面向实时播放 | 官方开放文档未给出可复核的统一 TTFA/RTF | 托管 API | **国内云第二候选。** `speech-2.8-turbo` 比 HD 更符合 Agent；不要引用第三方的“低于多少毫秒”作为保证，需自行测 P50/P95。[WebSocket 指南](https://platform.minimax.io/docs/guides/speech-t2a-websocket) / [模型列表](https://platform.minimax.io/docs/guides/models-intro) |
| **Cartesia Sonic 3.5** | 42 种语言，明确包含 `zh` 与 `en` | 双向 WebSocket、增量 transcript、上下文续写、同一 socket 多 context；可取消 context，官方直接定位 telephony/assistant | Sonic 3.5 官方页面只称低延迟，未公布独立统一 TTFA；旧模型数字不能替代 3.5 | 托管 API | **协议最适合电话 Agent。** 每轮一个 `context_id`，用户打断时取消旧 context 并创建新 context；需要把默认最高 3000 ms 的自动文本缓冲调低或由客户端分句，否则会人为增加等待。[模型](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) / [WebSocket](https://docs.cartesia.ai/api-reference/tts/websocket) / [输入缓冲](https://docs.cartesia.ai/build-with-cartesia/capability-guides/stream-inputs-using-continuations) |
| **ElevenLabs Flash v2.5** | 32 种语言，明确包含中文与英文 | 双向 TTS WebSocket 接收 partial text、返回音频分块；支持短期 client token | 约 75 ms，官方明确是短输入的模型推理，不含网络、排队和播放 | 托管 API | **海外低延迟对照。** 音色和 SDK 成熟；中国大陆真实端到端表现必须测。Flash 为降低延迟默认弱化数字规范化，电话号/日期应由 LLM 先转换成口语文本。[模型](https://elevenlabs.io/docs/overview/models) / [WebSocket](https://elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input) / [延迟说明](https://elevenlabs.io/docs/developer-guides/reducing-latency) |
| **Fun-CosyVoice3 0.5B-2512** | 中文、英文等 9 种语言，另支持 18+ 中文方言/口音 | 官方明确为 text-in 与 audio-out 双流式 | 最低 150 ms；官方模型卡未给出本机同硬件复现保证 | 开源模型约 0.5B；模型卡标记 Apache-2.0；提供 FastAPI、TRT-LLM/vLLM 相关路径 | **本地首选替代项。** 模型大小接近现有 Qwen 0.6B，最值得在同一 GPU、同一文本下 A/B；不能仅凭 150 ms 宣称一定快于当前模型。[官方模型卡](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512) / [官方仓库](https://github.com/FunAudioLLM/CosyVoice) |
| **MOSS-TTS-Realtime** | 官方模型页标记 20 种语言，包含中英文 | 原生增量文本输入和增量音频输出；支持多轮文本/声学历史和 KV cache 复用 | 单张 L20、预热、SDPA + `torch.compile`：TTFB 180 ms、RTF 0.51 | 1.7B backbone + 200M local transformer；Apache-2.0 | **本地第二候选。** 语音 Agent 设计比逐句 TTS 更完整，但显存与算力压力明显高于 0.5B/0.6B；官方未提供完整 benchmark fixture，数字不能直接外推。[模型卡](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_tts_realtime_model_card.md) / [架构](https://github.com/OpenMOSS/MOSS-TTS/blob/main/moss_tts_realtime/README.md) |
| **当前 Qwen3-TTS 0.6B** | 官方支持中英等 10 种语言 | 官方架构支持文本输入与音频输出流式；当前项目也使用生成器流式输出 | 官方宣称最低 97 ms，但没有给出当前机器/当前运行时的保证 | Apache-2.0；本项目已部署 | **保留作本地 fallback。** 当前慢不能直接归因于模型；官方 vLLM-Omni 文档路径截至当前仍提示在线 serving 后续支持，本项目用的运行时也不是官方低延迟基准环境。[官方仓库](https://github.com/QwenLM/Qwen3-TTS) |
| **Azure Speech** | 有大量 `zh-CN` 和英文/多语音色 | SDK 支持流式音频，官方提供预连接、复用 synthesizer 与 input text streaming 的降延迟方法 | 未给统一毫秒承诺；SDK 分别暴露 client first-byte、service first-byte、network、finish latency | 托管企业服务 | **企业稳定性备选，不是“最快”结论。** 已有 Azure 体系或合规要求时值得纳入；优点是延迟指标可观测、区域与企业支持成熟。[降低延迟](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-lower-speech-synthesis-latency) / [TTS 文档](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/index-text-to-speech) |
| **NVIDIA Riva TTS** | English 与 Mandarin 均有官方模型，但普通话走 FastPitch/HiFi-GAN，Magpie Multilingual 当前列出的语言不含中文 | gRPC 流式 TTS，支持流式和离线 SSML | 官方按 GPU、模型和并发发布 first-audio/chunk/RTFX 表，差异极大；不能脱离所选 tab 和硬件引用单个数字 | NVIDIA AI Enterprise/Riva 部署栈 | **不建议作为本项目第一选择。** 它可在专用 NVIDIA 推理服务器上非常快，但中英文不是同一多语模型路径，且对当前一张共享消费级 GPU 过重。[语言与模型](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/public/tts/tts-overview.html) / [性能表](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/tts/tts-performance-table.html) |

## 推荐排序

### 目标一：尽快获得自然、可打断的实时电话体验

1. **Qwen3-TTS Realtime（北京区）**：对当前项目迁移最平滑，优先验证。
2. **MiniMax Speech 2.8 Turbo**：国内网络和中英语音的第二路 A/B。
3. **Cartesia Sonic 3.5**：电话协议能力最完整，但先测中国大陆网络 P95。
4. **ElevenLabs Flash v2.5**：适合做海外低延迟基线，75 ms 不是端到端承诺。

### 目标二：数据不出本机

1. **先优化当前 Qwen3-TTS 0.6B 的会话结构**：保持模型常驻；避免每句新建 HTTP 请求；让 LLM 的稳定短语进入同一个 TTS 会话；保留打断和取消语义。
2. **Fun-CosyVoice3 0.5B-2512**：在完全相同的机器、文本、音色和播放器下测首声 P50/P95 与 RTF。
3. **MOSS-TTS-Realtime**：显存允许时再测，重点验证多轮 KV cache 是否能抵消模型更大的成本。

## 移动端接入判断

移动端无需运行 0.5B/1.7B 模型。推荐让 Android/iOS/移动网页只负责麦克风、VAD 和低缓冲播放，FastAPI 后端持有厂商 API Key 并维持 TTS WebSocket：

```text
手机麦克风 -> ASR -> LLM 流式稳定短语 -> 后端持久 TTS WebSocket -> PCM/Opus -> 手机扬声器
```

- Cartesia 官方支持浏览器短期 access token；ElevenLabs 支持 single-use token，但在本项目中仍建议由后端代理，避免长期 API Key 落到客户端。
- 远端通话优先 Opus；局域网/网页播放器可使用 raw PCM。播放器只保留很小的 jitter buffer，收到第一块可播放音频立即排程。
- 每个 AI 回合必须有独立 generation/context ID。用户插话时，同时取消 LLM、TTS context 和尚未播放的 AudioBuffer；否则即使模型很快，仍会出现“上一轮继续说”的假卡顿。
- 不应等待完整回答或完整句号才送 TTS。建议按稳定短语提交，例如中文约 8–20 字、英文约 4–12 个词，并在逗号/句号处优先 flush；具体阈值需要用音质和延迟 A/B 调整。

## 应采用的本项目基准

用固定的 20 条文本（中文、英文、中英混说、数字、日期、产品名）分别测试上述四路：当前本地 Qwen、云端 Qwen Realtime、MiniMax Turbo、CosyVoice 本地。每路记录：

- 冷启动和预热后 P50/P95 首个可播放音频；
- 用户停说到 AI 首声的端到端 P50/P95；
- RTF、峰值 GPU 显存和 ASR 同时运行时的退化；
- 中英混说、数字/电话号码、标点韵律；
- 打断到真正静音的时间；
- 移动 4G/5G、Wi-Fi 和局域网三种网络下的断流、重连与 P95 抖动。

只有这组同文本、同播放器、同网络条件的实测，才足以决定最终供应商。按当前架构判断，**先把 TTS 改为持久会话，再比较模型**，收益大概率高于只替换权重。
