const PROVIDER_ALIASES = {
  dashscope: 'alibaba-cn',
  moonshot: 'moonshotai',
  zhipu: 'zai',
}

function normalizeName(value = '') {
  return value.toLocaleLowerCase().replace(/\b(ai|api|nim|gemini)\b/g, '').replace(/[^a-z0-9]+/g, '')
}

function normalizeEndpoint(value = '') {
  try {
    const url = new URL(value)
    const path = url.pathname.replace(/\/(compatible-mode\/)?v\d+(beta)?\/?$/i, '').replace(/\/$/, '')
    return `${url.hostname.toLocaleLowerCase()}${path}`
  } catch {
    return value.toLocaleLowerCase().replace(/\/$/, '')
  }
}

function resolveCatalogProvider(provider, catalog) {
  const directIds = [PROVIDER_ALIASES[provider.id], provider.id].filter(Boolean)
  for (const id of directIds) if (catalog[id]) return catalog[id]

  const endpoint = normalizeEndpoint(provider.baseUrl)
  const name = normalizeName(provider.name)
  return Object.values(catalog).find((item) => (
    (endpoint && normalizeEndpoint(item.api) === endpoint)
    || (name && normalizeName(item.name) === name)
  ))
}

function timestamp(value) {
  const parsed = Date.parse(value || '')
  return Number.isFinite(parsed) ? parsed : 0
}

function preferredProvider(providers, catalogId) {
  return [...providers].sort((a, b) => (
    Number(Boolean(b.apiKey)) - Number(Boolean(a.apiKey))
    || Number(b.id === catalogId) - Number(a.id === catalogId)
    || (b.updatedAt || 0) - (a.updatedAt || 0)
  ))[0]
}

function localModelMap(models, providerIds, preferredId, activeModelId) {
  const matches = models.filter((model) => providerIds.has(model.providerId))
  const result = new Map()
  for (const model of matches) {
    const current = result.get(model.model)
    const score = Number(model.id === activeModelId) * 4 + Number(model.providerId === preferredId) * 2 + Number(Boolean(model.apiKey))
    const currentScore = current
      ? Number(current.id === activeModelId) * 4 + Number(current.providerId === preferredId) * 2 + Number(Boolean(current.apiKey))
      : -1
    if (!current || score > currentScore) result.set(model.model, model)
  }
  return result
}

function catalogChild(providerId, catalogId, modelId, model, persisted) {
  return {
    value: persisted?.id || `catalog:${catalogId}:${encodeURIComponent(modelId)}`,
    label: model.name || modelId,
    description: model.description || modelId,
    modelId,
    providerId,
    catalogId,
    persisted: Boolean(persisted),
    releasedAt: model.release_date,
    updatedAt: model.last_updated,
    badge: model.reasoning ? 'Reasoning' : undefined,
  }
}

export function buildModelOptions({ providers = [], models = [], catalog = {}, activeModelId = '' }) {
  const groups = new Map()
  const customProviders = []

  for (const provider of providers) {
    const catalogProvider = resolveCatalogProvider(provider, catalog)
    if (!catalogProvider) {
      customProviders.push(provider)
      continue
    }
    const group = groups.get(catalogProvider.id) || { catalog: catalogProvider, providers: [] }
    group.providers.push(provider)
    groups.set(catalogProvider.id, group)
  }

  const options = [...groups.values()].map((group) => {
    const provider = preferredProvider(group.providers, group.catalog.id)
    const providerIds = new Set(group.providers.map((item) => item.id))
    const localModels = localModelMap(models, providerIds, provider.id, activeModelId)
    const children = Object.entries(group.catalog.models || {}).map(([modelId, model]) => (
      catalogChild(provider.id, group.catalog.id, modelId, model, localModels.get(modelId))
    ))

    for (const [modelId, model] of localModels) {
      if (group.catalog.models?.[modelId]) continue
      children.push({
        value: model.id,
        label: model.name || modelId,
        description: modelId,
        modelId,
        providerId: model.providerId,
        catalogId: group.catalog.id,
        persisted: true,
        updatedAt: model.updatedAt,
        badge: 'Custom',
      })
    }

    children.sort((a, b) => timestamp(b.releasedAt || b.updatedAt) - timestamp(a.releasedAt || a.updatedAt) || a.label.localeCompare(b.label))
    return {
      value: group.catalog.id,
      label: group.catalog.name,
      description: group.catalog.api,
      providerId: provider.id,
      children,
    }
  })

  for (const provider of customProviders) {
    const children = models
      .filter((model) => model.providerId === provider.id)
      .map((model) => ({
        value: model.id,
        label: model.name,
        description: model.model,
        modelId: model.model,
        providerId: provider.id,
        persisted: true,
        updatedAt: model.updatedAt,
        badge: 'Custom',
      }))
    if (children.length) options.push({ value: provider.id, label: provider.name, description: provider.baseUrl, providerId: provider.id, children })
  }

  return options.sort((a, b) => a.label.localeCompare(b.label))
}

export function findModelOption(options, value) {
  for (const provider of options) {
    const model = provider.children.find((item) => item.value === value)
    if (model) return model
  }
  return undefined
}
