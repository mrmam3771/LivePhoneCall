# 2026 年中英文移动端本机 TTS 调研

更新日期：2026-08-23

## 结论

严格同时要求以下五项：**2026 年发布、开放权重、明确支持中文和英文、Android 与 iOS 有官方本机运行路径、足够快用于实时交互**，截至本次调研，**没有一个候选有完整的一手证据满足全部条件**。

对本项目最实际的选择是：

1. **首测 Kokoro v1.1-zh INT8 + sherpa-onnx。** 它不是 2026 新模型：原模型发布于 2025-02，sherpa-onnx 移动端模型包发布于 2025-06；但它明确支持中英混合、Apache-2.0、82M 参数，有官方 Android TTS Engine APK、Kotlin/Java/Dart/Swift API 和音频回调，是当前最接近“一个模型覆盖中英、手机本机运行”的方案。[Kokoro 模型卡](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) / [sherpa-onnx 中英模型页](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/kokoro-multi-lang-v1_1.html)
2. **若速度和包体优先于音质，测试双 Piper。** 中文和英文各加载一个 INT8 VITS/Piper 模型，由应用按文本语言路由；这不是单个双语模型，但压缩包通常约 14–21 MiB/声线，明显小于 Kokoro。sherpa-onnx 提供 Android/iOS 和回调式播放路径。[Piper 模型与 Android APK](https://k2-fsa.github.io/sherpa/onnx/tts/apk.html) / [官方 TTS Engine 源码](https://github.com/k2-fsa/sherpa-onnx/tree/master/android/SherpaOnnxTtsEngine)
3. **不要为了“2026 最新”选择 Supertonic 3 或 KittenTTS。** 两者很轻、很新，但官方语言表均不含中文；不满足本项目硬条件。[Supertonic 3](https://github.com/supertone-inc/supertonic) / [KittenTTS](https://github.com/KittenML/KittenTTS)
4. **Qwen3-TTS 0.6B 与 Fun-CosyVoice3 0.5B 不作为手机本机候选。** 它们适合服务器 GPU；官方仓库没有 Android/iOS 本机 SDK、手机基准或手机内存口径。Qwen 0.6B 模型仓库约 2.52 GB；两者公布的 97 ms/150 ms 是各自优化环境下的流式能力，不能外推到手机。[Qwen 模型卡与文件](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/tree/main) / [CosyVoice3 模型卡](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512)

## 口径说明

- **本机可运行**：官方项目直接提供 Android/iOS 示例、SDK 或可构建路径；只有第三方转换不算官方支持。
- **实时**：RTF `< 1` 只说明完整音频生成快于播放，不保证首声快。交互式 TTS 还需要低 TTFA、可边生成边播放、可取消。
- **回调式不等于真正 text-in streaming**：sherpa-onnx 的 `generateWithConfigAndCallback()` 会回调 PCM 并允许返回 `0` 取消，Android TTS Engine 也把回调块立即交给系统播放；但 Kokoro/VITS 的一次调用仍接收一段完整文本，不支持像 CosyVoice 那样在同一会话持续追加文本。[Kotlin API](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/kotlin-api/Tts.kt) / [Android 播放回调](https://github.com/k2-fsa/sherpa-onnx/blob/master/android/SherpaOnnxTtsEngine/app/src/main/java/com/k2fsa/sherpa/onnx/tts/engine/TtsService.kt)
- **官方移动端基准很缺**：以下候选均未公布可复核的 Android/iPhone TTFA、RTF、峰值内存组合。没有数字时不以桌面或 GPU 数据代替。

## 候选核查

| 候选 | 发布与许可 | 中英 | Android / iOS | 流式与体积 | 判断 |
|---|---|---|---|---|---|
| **Kokoro v1.1-zh INT8** | sherpa 包发布于 2025-06-18；原模型 Apache-2.0 | **明确支持中英及混说**；103 声线 | sherpa 官方提供 Android TTS Engine APK；Kotlin/Java/Dart/Swift API，iOS SwiftUI 示例 | 音频回调/可取消，不是可追加文本的真流；INT8 发布包约 **140.2 MiB**，FP32 约 **347.9 MiB** | **推荐级别 A，首测。** 单模型中英、许可宽松、移动链路最完整；但官方无手机性能数据，不能预先保证旗舰或中端机都实时。[模型清单](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/kokoro.html) / [发布资产](https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models) |
| **双 Piper / VITS** | 模型较旧；原 rhasspy Piper 代码 MIT，当前维护版 `piper1-gpl` 为 GPL-3.0；每个声线许可需单独核查 | 中文、英文声线都有，但通常是**两个单语模型** | sherpa 官方 Android APK/TTS Engine 与 iOS API 可运行 VITS/Piper | 回调/可取消；sherpa 的中文 `xiao_ya` INT8 包约 14 MiB，常见英文 INT8 包约 20–21 MiB | **推荐级别 A（极限速度/包体路线）。** 需要语言检测、分段和双模型管理；不能宣传为一个原生双语模型。[Piper 维护版](https://github.com/OHF-Voice/piper1-gpl) / [中文模型示例](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese/vits-piper-zh_CN-xiao_ya-medium.html) |
| **MeloTTS zh_en** | 2024；代码 MIT，官方模型卡标记 MIT | 明确中英，1 声线；英文词必须存在于 lexicon，OOV 有限制 | sherpa 官方通用 Android/iOS 路径 | 回调；ONNX **163 MB**。官方 Raspberry Pi 4 四线程 RTF **2.518**，慢于实时；没有手机基准 | **推荐级别 C。** 比 Kokoro 老，英文覆盖受限，官方弱设备数据也不理想。[sherpa MeloTTS 页](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html#vits-melo-tts-zh-en-chinese-english-1-speaker) / [MeloTTS](https://github.com/myshell-ai/MeloTTS) |
| **ZipVoice Distill INT8** | 2025-06 模型发布；Apache-2.0；123M 参数 | 明确中英、零样本克隆 | sherpa 有 Java/Kotlin/Dart/Swift 示例，因此有 Android/iOS 构建路径 | 非 text-in 真流；需参考音频+文字、Vocos、迭代步数。INT8 包约 **104.1 MiB**，Vocos 另约 **51.6 MiB** | **推荐级别 B/C。** 适合必须克隆音色的场景，不是最低延迟首选；无手机基准。[ZipVoice 官方仓库](https://github.com/k2-fsa/ZipVoice) / [sherpa 部署页](https://k2-fsa.github.io/sherpa/onnx/tts/zipvoice.html) |
| **Moonshine Voice TTS** | 2026 活跃工具链；代码主体 MIT；官方说明非英语模型采用 Moonshine Community **非商业**许可证，其他 TTS 资产还要遵循各自来源许可 | 列出 `en-us` 与 `zh-hans`，底层组合 Kokoro/Piper 和自研 G2P；不是一个新双语模型 | **官方 Android Maven、iOS Swift Package 和两端 TTS 示例** | `say()` 非阻塞排队，后台预合成下一句；不是增量文本/增量 PCM 的模型级真流；未公布手机基准 | **推荐级别 B（原型）/商用需法务核查。** 移动 SDK 最省集成，但中文权重许可与音质需要先验收。[官方仓库与 TTS 文档](https://github.com/moonshine-ai/moonshine) |
| **Supertonic 3** | 2026-05；代码 MIT，模型 OpenRAIL-M；官方已公告仓库将在 2026-07 后归档、停止支持 | **不支持中文**；31 种语言表有英语但无 `zh` | 官方 iOS、Flutter、Java/C++ 等 ONNX 示例；sherpa 也支持 | 约 99M 参数；sherpa INT8 包约 122.8 MiB；官方电子书设备演示平均 RTF 0.3 | **排除。** 很快且移动友好，但没有中文；`lang="na"` 也不等于支持中文。[官方语言表、许可与基准](https://github.com/supertone-inc/supertonic) |
| **KittenTTS v0.8** | 2026-02-24；Apache-2.0；15M/40M/80M | **仅英语**；“multilingual TTS”仍在路线图 | 官方项目的 mobile SDK 仍未完成；sherpa 可在移动端运行其 ONNX | 25–80 MB；有 Python streaming 示例，但无官方 Android/iOS SDK与手机基准 | **排除。** 体积优秀，但没有中文。[官方仓库](https://github.com/KittenML/KittenTTS) / [sherpa 模型支持](https://k2-fsa.github.io/sherpa/onnx/tts/kitten.html) |
| **Moonshine micro neural TTS** | 2026 工具链；面向极小 MCU | **只支持英语或 IPA** | 面向微控制器，不是中英手机方案 | 真正输出 streaming mono int16 PCM | **排除。** “Moonshine TTS”确实存在，但与 Moonshine STT 不同，且 micro 版本不支持中文。[官方说明](https://github.com/moonshine-ai/moonshine/tree/main/micro/neural-tts) |
| **Qwen3-TTS 0.6B** | 2026-01；Apache-2.0 | 明确中英等 10 种语言 | **无官方 Android/iOS 本机运行支持或手机基准**；官方示例使用 PyTorch/CUDA | 官方真 text/audio streaming，最低 97 ms；HF 仓库约 **2.52 GB** | **手机本机排除，服务器保留。** 不能用桌面第三方 GGUF/Metal 端口推导 iPhone/Android 可用。[官方模型卡](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base) |
| **Fun-CosyVoice3 0.5B-2512** | 2025-12；Apache-2.0 | 明确中英等 9 种语言 | **无官方 Android/iOS 本机 SDK或手机基准**；官方部署面向 PyTorch、vLLM/TRT-LLM/服务器 | 真 text-in/audio-out 双流，官方称最低 150 ms；0.5B | **手机本机排除，服务器可 A/B。** 0.5B 对手机仍过重，150 ms 不能外推。[官方仓库](https://github.com/FunAudioLLM/CosyVoice) / [模型卡](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512) |

## 推荐验证顺序

1. 在一台目标 Android 中端机、一台 Android 旗舰机和最低支持 iPhone 上，先测 **Kokoro v1.1-zh INT8 + sherpa-onnx**。
2. 固定 20 条文本：纯中文、纯英文、中英混说、数字、日期、缩写和产品名。记录冷/热启动、首个可播放 PCM 的 P50/P95、整句 RTF、峰值内存、包体、耗电和温升。
3. 若 Kokoro 首声或持续 RTF 不达标，改测 **中文 Piper INT8 + 英文 Piper INT8**；由上游 LLM 稳定短语按语言切段，避免在单词中间切换声线。
4. 交互实现采用 8–20 个中文字或 4–12 个英文词的稳定短语提交，并立即播放回调 PCM；用户插话时取消当前生成并清空播放器队列。
5. 只有需要本机克隆音色时再测 ZipVoice；Moonshine Voice 可用于快速验证 Android/iOS 产品形态，但商用前必须逐项确认中文模型和数据许可。

最终判断应由目标真机数据决定。现有一手资料能证明 Kokoro/Piper **可以在手机本机运行**，但不能证明它们在所有目标手机上都达到所需 TTFA 和 RTF。
