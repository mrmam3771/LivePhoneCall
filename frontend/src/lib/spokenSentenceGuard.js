function sentenceKey(sentence) {
  return sentence.toLocaleLowerCase().replace(/\s+/g, ' ').trim()
}

export function createSpokenSentenceGuard() {
  const sentences = new Set()

  return {
    accept(sentence) {
      const key = sentenceKey(sentence)
      if (key.length < 8) return true
      if (sentences.has(key)) return false
      sentences.add(key)
      return true
    },
  }
}
