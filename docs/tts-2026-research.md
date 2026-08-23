# 2026 中英双语实时 TTS 调研

更新日期：2026-08-22

## 结论先行

针对“Qwen3-ASR + Codex/Agent + TTS + 移动端”的目标，建议按下面顺序验证：

1. **本机部署首选：Qwen3-TTS 0.6B CustomVoice。** 它支持中英、文本流和音频流，Apache-2.0，官方给出的最佳端到端合成延迟为 97 ms。0.6B 是当前机器上最现实的高质量起点，也与现有 Qwen 技术栈一致。[官方仓库](https://github.com/QwenLM/Qwen3-TTS) / [0.6B 模型卡](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)
2. **专为语音 Agent 的本地备选：MOSS-TTS-Realtime 1.7B。** 支持中英和增量文本输入，官方在单张 L20、预热、SDPA + `torch.compile` 下报告 TTFB 180 ms、RTF 0.51；它还能复用多轮 KV cache。[官方模型卡](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_tts_realtime_model_card.md)
3. **国内云端首选：Alibaba Qwen3-TTS Realtime。** 北京区有实时 WebSocket 模型，和当前 Qwen ASR 的组合成本最低；官方没有发布可直接横向比较的 TTFA，必须从你的网络实测。[实时 TTS 指南](https://www.alibabacloud.com/help/en/model-studio/realtime-tts-user-guide)
4. **全球托管低延迟对照：Cartesia Sonic 3.5、ElevenLabs Flash v2.5。** 两者均支持中英双语和双向流式输入；ElevenLabs 的约 75 ms 是模型推理时间，不含网络和播放缓冲。[Cartesia](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) / [ElevenLabs](https://elevenlabs.io/docs/overview/models)
5. **完全离线手机端首选：Kokoro v1.1-zh + sherpa-onnx。** Android/iOS 均有官方运行路径，支持中英、103 个音色和 INT8；但它是端侧离线 TTS，不应期待与服务器大模型同级的表现力或严格的 token-in/audio-out 流式体验。[Kokoro 文档](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html)

如果手机可以联网，最佳架构不是把 0.6B/1.7B 大模型塞进手机，而是手机只负责 WebSocket 播放，TTS 跑在当前 RTX 显卡或国内云端。完全离线模式再用 Kokoro 作为降级路径。

## 指标口径

- **模型推理延迟**：模型内部开始计算到产生输出，不含网络、排队、客户端解码和播放缓冲。
- **TTFB/TTFA/首包**：定义因厂商而异。有些指首字节，有些指首个可解码音频块，不能直接当作同一指标。
- **RTF**：生成耗时 / 音频时长。`RTF < 1` 表示整体生成快于播放速度，但不代表首包一定快。
- 下表只记录来源明确给出的数字；没有数字时写“未公布”，不做推算。

## 本地与开源方案

| 方案 | 中英支持 | 真流式能力 | 官方公开延迟 | 许可 | 部署约束与判断 |
|---|---|---|---|---|---|
| **Qwen3-TTS 12Hz 0.6B/1.7B** | 中文、英文及另外 8 种语言 | 单字符输入后即可输出首个音频包；文本输入和音频输出均可流式 | 最低 97 ms，来源未给出适用于所有硬件的保证 | Apache-2.0 | 官方提供 PyTorch 包、FlashAttention 2 建议和 vLLM-Omni 示例。对当前消费级 NVIDIA GPU，0.6B 是优先实测项；97 ms 不能直接视为 RTX 4070 上的结果。[仓库](https://github.com/QwenLM/Qwen3-TTS) |
| **Fun-CosyVoice3 0.5B-2512** | 中、英及另外 7 种语言，支持多种中文方言 | 明确支持 text-in 与 audio-out 双流式 | 最低 150 ms | 代码和 HF 模型页标为 Apache-2.0；仓库免责声明涉及演示素材，商业上线仍应做法务复核 | 模型约 0.5B，支持 FastAPI、TRT-LLM/vLLM 路径和语音克隆，适合做 Qwen3-TTS 的本地 A/B 对照。[仓库](https://github.com/QwenAudio/CosyVoice) / [模型卡](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512) |
| **MOSS-TTS-Realtime 1.7B** | 20 种语言，明确包含中、英 | 增量文本输入、增量音频、单轮及多轮 KV cache 复用 | 单张 L20 预热后 TTFB 180 ms，RTF 0.51；测试启用了 SDPA + `torch.compile` | Apache-2.0 | 面向语音 Agent，最大 32K 上下文；当前 FastAPI 说明只支持 batch size 1。显存和冷启动成本高于 0.6B 模型。[模型卡](https://github.com/OpenMOSS/MOSS-TTS/blob/main/docs/moss_tts_realtime_model_card.md) |
| **MOSS-TTS Local Transformer v1.5 4B** | 31 种语言，明确包含中、英 | SGLang-Omni 提供 OpenAI 兼容流式服务；官方也有实时解码示例 | 未公布统一 TTFA | Apache-2.0 | 48 kHz 立体声、克隆和 31 语种很强，但 4B 对消费级显卡的延迟/显存压力更大，优先级低于 MOSS-Realtime。[模型卡](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Local-Transformer-v1.5) |
| **Fish Audio S2 Pro** | 80+ 语言；中、英属于 Tier 1 | SGLang-Omni 流式服务 | 单张 H200：TTFA 约 100 ms、RTF 0.195 | Fish Audio Research License；个人、研究和非商业免费，商业用途需另签许可 | 约 4B 主模型 + 400M 快速分支，官方延迟来自 H200，不能外推到当前消费级 GPU。音质和情感控制很强，但许可、显存和部署复杂度明显更高。[仓库](https://github.com/fishaudio/fish-speech) / [许可](https://github.com/fishaudio/fish-speech/blob/main/LICENSE) |
| **Luna-TTS Realtime 0.6B** | 中文、英文、日文、韩文 | 1.28 秒块级增量输出 | 双 H20、预热、8 步并行 CFG：首块 41.6 ms、RTF 0.0240；单 H20 串行 CFG 为 59.6 ms、RTF 0.0432 | 截至本调研日期未找到官方公开权重、代码或许可 | 论文指标最领先，但当前不是可落地候选，只能列为研究前沿；不得把双 H20 结果当作手机或 RTX 4070 延迟。[论文](https://arxiv.org/abs/2608.11593) |

### 次级候选

- **Spark-TTS 0.5B** 支持中文和英文、Apache-2.0。官方 Triton/TRT-LLM 表格在 L20、并发 1 下给出平均延迟 876.24 ms、RTF 0.1362，但该数字不是明确的 TTFA，而且官方资料没有像 Qwen、CosyVoice 那样清楚证明增量文本输入，因此不列为首选实时 Agent 模型。[官方仓库](https://github.com/SparkAudio/Spark-TTS)
- **VibeVoice-Realtime 0.5B** 虽然约 300 ms 首次可听输出且 MIT，但官方明确表示当前实时模型面向英语，其他语言结果不可预测，且没有中文支持，因此不符合本次硬条件。[官方模型卡](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B)
- **Supertonic 3** 不列为合格候选：本次要求是中文和英文均有明确、可验证的模型支持，不能只因为端侧框架里出现语言代码或第三方转换就视为已满足。

## 托管 API

| 服务 | 中英与流式能力 | 官方延迟信息 | 当前可用性与注意事项 |
|---|---|---|---|
| **Alibaba Qwen3-TTS Realtime** | 北京/新加坡区提供 WebSocket 实时模型；客户端可提交文本 buffer，服务返回 `response.audio.delta`；中英明确支持 | 未公布统一 TTFA；`commit` 模式被描述为最低延迟，`server_commit` 平衡延迟和质量 | 与现有 Qwen 技术栈最匹配，中国大陆优先实测 `qwen3-tts-instruct-flash-realtime`。[模型列表](https://www.alibabacloud.com/help/en/model-studio/realtime-tts-user-guide) / [交互流程](https://www.alibabacloud.com/help/en/model-studio/interactive-process-of-qwen-tts-realtime-synthesis) |
| **MiniMax Speech 2.8 Turbo/HD** | WebSocket/HTTP 流式，40 种语言，包括中英、粤语和代码切换 | 厂商合作资料称 `<250 ms latency`，但未定义是 TTFA 还是端到端，不能与 75 ms 模型推理直接比较 | 国内连接和中英表现是优势；实时 Agent 优先测 Turbo，音质优先测 HD。[WebSocket 文档](https://platform.minimax.io/docs/guides/speech-t2a-websocket) / [模型列表](https://platform.minimax.io/docs/guides/models-intro) |
| **Cartesia Sonic 3.5** | 稳定快照 `sonic-3.5-2026-05-04`，42 种语言含 `en`/`zh`，WebSocket 可逐块输入文本和输出 PCM | 开放文档没有 Sonic 3.5 的独立统一 TTFA；旧 Sonic Turbo 官方最低首字节为 40 ms，不能替代 3.5 的实测 | 全球低延迟强候选。增量文本的默认 buffer 最长可达 3000 ms，需要按 Agent 的分句策略调整，避免模型快但输入缓冲慢。[模型文档](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) / [低延迟 WebSocket](https://docs.cartesia.ai/examples/tts-websocket-low-latency) |
| **ElevenLabs Flash v2.5** | 32 种语言含中英；HTTP streaming 和双向 WebSocket 均受支持 | 约 75 ms 是短文本模型推理，不含网络、排队、应用及播放缓冲 | 音色库和 SDK 成熟。官方明确提醒真实 TTFA 会显著高于 75 ms；中国大陆使用前必须测可达性和抖动。[模型文档](https://elevenlabs.io/docs/overview/models) / [延迟说明](https://elevenlabs.io/docs/developer-guides/reducing-latency) |
| **Volcengine Doubao Seed TTS 2.0** | 支持中文、英文跨语言音色迁移；有单向音频流和双向 text-in/audio-out WebSocket | 单向大模型流式首包官方约 600 ms；双向模式未给精确数值 | 国内生产部署和音色能力较强，但公开单向首包指标慢于最激进的海外模型；应测试双向接口。[产品文档](https://www.volcengine.com/docs/6561/1257543?lang=zh) / [双向 WebSocket](https://www.volcengine.com/docs/6561/2532486?lang=zh) |
| **Google Cloud Chirp 3 HD** | 英文和普通话 `cmn-CN` 明确支持；双向流式同时接收文本和返回音频 | 未公布统一 TTFA | 流式能力目前为 Preview，区域不在中国大陆，适合作为企业云质量基线而非国内首选。[流式文档](https://docs.cloud.google.com/text-to-speech/docs/create-audio-text-streaming) / [语言列表](https://docs.cloud.google.com/text-to-speech/docs/chirp3-hd) |
| **Azure Speech** | 大量 `zh-CN` 和英文/多语种音色；SDK 支持流式输出和输入文本流 | 官方解释 first-byte/client/service latency 和预连接优化，但无统一毫秒承诺 | 成熟的企业级备选，适合已有 Azure/世纪互联体系的项目，不因缺少统一 TTFA 而宣称“最快”。[语言支持](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support) / [降低延迟](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-lower-speech-synthesis-latency) |

## 移动端支持

### A. 手机作为本地或云端流式客户端

这是推荐架构。Android/iOS 只维持 WebSocket、接收 PCM/Opus 音频并用小缓冲连续播放；模型运行在本机 RTX GPU、局域网服务器或云端。

```text
手机麦克风 -> Qwen3-ASR 服务 -> Agent -> 流式文本
                                      -> TTS WebSocket -> 手机扬声器
```

实施注意点：

- 本地服务当前若只绑定 `127.0.0.1`，手机无法访问；需要绑定局域网地址（通常为 `0.0.0.0`），仅开放局域网防火墙规则，并增加会话鉴权。
- TTS 应接收 LLM 的稳定短语或标点片段，而不是等待整段答案；同时不能每个 token 单独合成，否则韵律会破碎。
- 手机播放器使用 raw PCM 时通常可把首播缓冲控制在约 40–120 ms；这是客户端策略，不是模型性能承诺。
- 外网移动端优先选择国内区域的 Alibaba、MiniMax 或 Volcengine；海外服务需要在真实 4G/5G/Wi-Fi 下测 P50/P95 TTFA、断流和重连。

### B. Android/iOS 完全离线端侧

| 方案 | Android / iOS | 中英支持 | 包体与限制 | 适用判断 |
|---|---|---|---|---|
| **Kokoro v1.1-zh + sherpa-onnx** | 官方提供 Android TTS APK/源码；Swift Package 含 iOS XCFramework 和 `tts-kokoro-zh-en.swift` 示例 | 中英，103 个音色，24 kHz；同时有 INT8 和非量化包 | 原始 Kokoro 权重与 sherpa-onnx 均标为 Apache-2.0。v1.0 ONNX 文件为 310 MB，另有 26 MB voices；v1.1/INT8 应以下载包实测。官方接口名为 `OfflineTts`，不能把回调生成等同于服务器式双向流式 | 完全离线首选，音色明显多于 MeloTTS；短句分块生成后立即播放可获得可接受交互感。[模型与下载](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html) / [Android APK](https://k2-fsa.github.io/sherpa/onnx/tts/apk.html) / [Swift Package](https://github.com/k2-fsa/sherpa-onnx/blob/master/Package.swift) |
| **MeloTTS zh_en + sherpa-onnx** | sherpa-onnx 的 Android/iOS 通用 VITS 路径可加载；Android 已提供对应 APK | 中英、单音色、44.1 kHz | ONNX 模型 163 MB。官方明确说明英文只能朗读 `lexicon.txt` 中已有词，遇到产品名和新词需要维护词典 | 包较小、结构简单的离线保底方案；语言鲁棒性和音色选择不如 Kokoro。[官方转换文档](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html) |

sherpa-onnx 本身是 Apache-2.0，官方明确支持 Android、iOS、HarmonyOS 和嵌入式设备。[项目仓库](https://github.com/k2-fsa/sherpa-onnx) 但框架许可和每个模型权重许可是两件事，发布应用前仍应把具体模型包里的 `LICENSE` 纳入合规清单。

## 面向当前项目的选择

建议用同一套测试文本和播放器做四路 A/B：

1. 本机 `Qwen3-TTS-12Hz-0.6B-CustomVoice`。
2. 国内云 `qwen3-tts-instruct-flash-realtime`。
3. MiniMax `speech-2.8-turbo`。
4. 手机离线 `kokoro-int8-multi-lang-v1_1`。

记录冷启动、预热后 P50/P95 首次可播放音频、整句 RTF、峰值显存/内存、中英混说错误、数字和英文产品名读法。只有这组同网络、同文本、同播放器的实测，才适合决定最终方案。

基于当前已知条件，产品默认路径应是：**手机/网页 -> 当前 PC 上的 Qwen3-ASR -> Codex/Agent -> 本机 Qwen3-TTS 0.6B**；手机离开局域网时切换 Alibaba 或 MiniMax；无网时降级到 Kokoro。这样同时保留音质、实时性、移动端可用性和离线能力。
