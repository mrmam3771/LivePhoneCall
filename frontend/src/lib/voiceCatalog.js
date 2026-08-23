export const AUTO_VOICE_ID = 'Auto'

export const VOICE_OPTIONS = [
  { id: AUTO_VOICE_ID, name: 'Automatic', nativeLanguage: 'Matches the reply', description: 'Aiden for English, Vivian for Chinese, and native voices for Japanese and Korean.', recommended: true },
  { id: 'Aiden', name: 'Aiden', nativeLanguage: 'English', description: 'Sunny American male voice with a natural conversational pace.', sample: 'Good afternoon. It is lovely to meet you. How can I help you today?' },
  { id: 'Ryan', name: 'Ryan', nativeLanguage: 'English', description: 'Dynamic male voice with a strong sense of rhythm.', sample: 'Good afternoon. It is lovely to meet you. How can I help you today?' },
  { id: 'Vivian', name: 'Vivian', nativeLanguage: 'Chinese', description: 'Bright young female voice.', sample: '你好，很高兴见到你。今天有什么可以帮你的吗？' },
  { id: 'Serena', name: 'Serena', nativeLanguage: 'Chinese', description: 'Warm and gentle young female voice.', sample: '你好，很高兴见到你。今天有什么可以帮你的吗？' },
  { id: 'Uncle_Fu', name: 'Uncle Fu', nativeLanguage: 'Chinese', description: 'Seasoned male voice with a mellow timbre.', sample: '你好，很高兴见到你。今天有什么可以帮你的吗？' },
  { id: 'Dylan', name: 'Dylan', nativeLanguage: 'Chinese · Beijing', description: 'Youthful Beijing male voice.', sample: '你好，很高兴见到你。今天有什么可以帮你的吗？' },
  { id: 'Eric', name: 'Eric', nativeLanguage: 'Chinese · Sichuan', description: 'Lively Chengdu male voice.', sample: '你好，很高兴见到你。今天有什么可以帮你的吗？' },
  { id: 'Ono_Anna', name: 'Ono Anna', nativeLanguage: 'Japanese', description: 'Playful Japanese female voice.', sample: 'こんにちは。今日はどのようにお手伝いできますか？' },
  { id: 'Sohee', name: 'Sohee', nativeLanguage: 'Korean', description: 'Warm Korean female voice.', sample: '안녕하세요. 오늘 무엇을 도와드릴까요?' },
]

export function resolveVoiceForText(text, configuredVoice = AUTO_VOICE_ID) {
  if (configuredVoice && configuredVoice !== AUTO_VOICE_ID) return configuredVoice
  const value = String(text || '')
  if (/[぀-ヿ]/u.test(value)) return 'Ono_Anna'
  if (/[가-힯]/u.test(value)) return 'Sohee'
  const latinCount = (value.match(/[A-Za-z]/g) || []).length
  const chineseCount = (value.match(/[㐀-鿿]/gu) || []).length
  return latinCount > chineseCount ? 'Aiden' : 'Vivian'
}

export function voiceById(id) {
  return VOICE_OPTIONS.find((voice) => voice.id === id) || VOICE_OPTIONS[0]
}
