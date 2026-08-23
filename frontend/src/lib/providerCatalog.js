export const PROVIDER_CATALOG = {
  openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', api: 'openai-completions', models: [['GPT-5.2', 'gpt-5.2'], ['GPT-5 mini', 'gpt-5-mini'], ['GPT-4.1', 'gpt-4.1']] },
  anthropic: { name: 'Anthropic', baseUrl: 'https://api.anthropic.com', api: 'anthropic', models: [['Claude Opus 5', 'claude-opus-5'], ['Claude Sonnet 4.5', 'claude-sonnet-4-5-20250929'], ['Claude Haiku 4.5', 'claude-haiku-4-5-20251001']] },
  google: { name: 'Google Gemini', baseUrl: 'https://generativelanguage.googleapis.com', api: 'google_genai', models: [['Gemini 3 Pro', 'gemini-3-pro'], ['Gemini 3 Flash', 'gemini-3-flash'], ['Gemini Flash Latest', 'gemini-flash-latest']] },
  deepseek: { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', api: 'openai-completions', models: [['DeepSeek Chat', 'deepseek-chat'], ['DeepSeek Reasoner', 'deepseek-reasoner']] },
  dashscope: { name: 'Alibaba DashScope', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', api: 'openai-completions', models: [['Qwen Plus', 'qwen-plus'], ['Qwen Max', 'qwen-max'], ['Qwen Turbo', 'qwen-turbo']] },
  moonshot: { name: 'Moonshot AI', baseUrl: 'https://api.moonshot.cn/v1', api: 'openai-completions', models: [['Kimi K2.5', 'kimi-k2.5'], ['Moonshot v1 128K', 'moonshot-v1-128k']] },
  minimax: { name: 'MiniMax', baseUrl: 'https://api.minimax.io/v1', api: 'openai-completions', models: [['MiniMax M2.1', 'MiniMax-M2.1'], ['MiniMax M2', 'MiniMax-M2']] },
  nvidia: { name: 'NVIDIA NIM', baseUrl: 'https://integrate.api.nvidia.com/v1', api: 'openai-completions', models: [['Nemotron 3 Super 120B', 'nvidia/llama-3.3-nemotron-super-49b-v1.5'], ['Llama 3.3 70B Instruct', 'meta/llama-3.3-70b-instruct'], ['Qwen3 235B', 'qwen/qwen3-235b-a22b']] },
  zhipu: { name: 'Zhipu AI', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', api: 'openai-completions', models: [['GLM-5.3', 'glm-5.3'], ['GLM-4.7', 'glm-4.7']] },
  siliconflow: { name: 'SiliconFlow', baseUrl: 'https://api.siliconflow.cn/v1', api: 'openai-completions', models: [['Qwen3 235B', 'Qwen/Qwen3-235B-A22B'], ['DeepSeek V3.2', 'deepseek-ai/DeepSeek-V3.2']] },
  openrouter: { name: 'OpenRouter', baseUrl: 'https://openrouter.ai/api/v1', api: 'openai-completions', models: [['GPT-5 mini', 'openai/gpt-5-mini'], ['Claude Sonnet 4.5', 'anthropic/claude-sonnet-4.5'], ['Gemini 3 Pro', 'google/gemini-3-pro']] },
  groq: { name: 'Groq', baseUrl: 'https://api.groq.com/openai/v1', api: 'openai-completions', models: [['Llama 3.3 70B', 'llama-3.3-70b-versatile'], ['Qwen3 32B', 'qwen/qwen3-32b']] },
  together: { name: 'Together AI', baseUrl: 'https://api.together.xyz/v1', api: 'openai-completions', models: [['Llama 3.3 70B Turbo', 'meta-llama/Llama-3.3-70B-Instruct-Turbo']] },
  fireworks: { name: 'Fireworks AI', baseUrl: 'https://api.fireworks.ai/inference/v1', api: 'openai-completions', models: [['Llama 3.3 70B', 'accounts/fireworks/models/llama-v3p3-70b-instruct']] },
  xai: { name: 'xAI', baseUrl: 'https://api.x.ai/v1', api: 'openai-completions', models: [['Grok 4.6', 'grok-4.6'], ['Grok 3', 'grok-3']] },
  mistral: { name: 'Mistral AI', baseUrl: 'https://api.mistral.ai/v1', api: 'openai-completions', models: [['Mistral Large', 'mistral-large-latest'], ['Codestral', 'codestral-latest']] },
  cohere: { name: 'Cohere', baseUrl: 'https://api.cohere.com/compatibility/v1', api: 'openai-completions', models: [['Command A', 'command-a-03-2025']] },
  perplexity: { name: 'Perplexity', baseUrl: 'https://api.perplexity.ai', api: 'openai-completions', models: [['Sonar Pro', 'sonar-pro'], ['Sonar', 'sonar']] },
  ollama: { name: 'Ollama', baseUrl: 'http://127.0.0.1:11434/v1', api: 'openai-completions', models: [['Qwen3 8B', 'qwen3:8b'], ['Llama 3.3', 'llama3.3']] },
  lmstudio: { name: 'LM Studio', baseUrl: 'http://127.0.0.1:1234/v1', api: 'openai-completions', models: [['Loaded local model', 'local-model']] },
  vllm: { name: 'vLLM', baseUrl: 'http://127.0.0.1:8000/v1', api: 'openai-completions', models: [['Serving model', 'model']] },
  custom: { name: 'Custom OpenAI-compatible', baseUrl: '', api: 'openai-completions', models: [] },
}

export function presetForProvider(provider) {
  const name = (provider?.name || '').toLowerCase()
  const baseUrl = provider?.baseUrl || ''
  return Object.values(PROVIDER_CATALOG).find((preset) => preset.name.toLowerCase() === name || (preset.baseUrl && preset.baseUrl === baseUrl)) || PROVIDER_CATALOG.custom
}
