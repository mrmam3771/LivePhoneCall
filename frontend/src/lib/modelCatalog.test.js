import { describe, expect, test } from 'vitest'
import { buildModelOptions } from './modelCatalog'

describe('buildModelOptions', () => {
  test('uses the models.dev catalog instead of the locally materialized model count', () => {
    const providers = [
      { id: 'deepseek', name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', apiKey: '', updatedAt: 1 },
      { id: 'legacy-deepseek', name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', apiKey: 'configured', updatedAt: 2 },
    ]
    const models = [
      { id: 'deepseek-chat', providerId: 'deepseek', name: 'Old local name', model: 'deepseek-chat' },
    ]
    const catalog = {
      deepseek: {
        id: 'deepseek',
        name: 'DeepSeek',
        api: 'https://api.deepseek.com',
        models: {
          'deepseek-chat': { id: 'deepseek-chat', name: 'DeepSeek Chat', release_date: '2024-01-01' },
          'deepseek-reasoner': { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', release_date: '2025-01-20' },
          'deepseek-v3.2-speciale': { id: 'deepseek-v3.2-speciale', name: 'DeepSeek V3.2 Speciale', release_date: '2025-12-01' },
        },
      },
    }

    const options = buildModelOptions({ providers, models, catalog })

    expect(options).toHaveLength(1)
    expect(options[0].label).toBe('DeepSeek')
    expect(options[0].providerId).toBe('legacy-deepseek')
    expect(options[0].children.map((model) => model.label)).toEqual([
      'DeepSeek V3.2 Speciale',
      'DeepSeek Reasoner',
      'DeepSeek Chat',
    ])
  })
})
