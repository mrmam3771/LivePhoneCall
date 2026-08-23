export function consumeModelToken(piece, state) {
  state.raw += piece
  let visible = ''

  while (state.raw) {
    const tag = state.raw.match(/<\/?think(?:ing)?>/i)
    if (!tag) {
      const partial = state.raw.match(/<(?:\/?t(?:h(?:i(?:n(?:k(?:i(?:n?)?)?)?)?)?)?)?$/i)
      const length = partial?.[0].length || 0
      const complete = state.raw.slice(0, state.raw.length - length)
      if (state.inThinking) state.thought += complete
      else visible += complete
      state.raw = length ? state.raw.slice(-length) : ''
      break
    }

    const before = state.raw.slice(0, tag.index)
    if (state.inThinking) state.thought += before
    else visible += before
    state.inThinking = !tag[0].startsWith('</')
    state.raw = state.raw.slice((tag.index || 0) + tag[0].length)
  }

  return visible
}
