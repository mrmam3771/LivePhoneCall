# Qwen Voice Frontend

Vue 3 and Vite frontend for the local Qwen voice workspace.

```powershell
yarn
yarn dev
```

The development server runs at `http://127.0.0.1:8000/`. It is currently a
frontend-only preview: conversations, text messages, recorded audio, and the
selected theme are stored locally in the browser. ASR, LLM, and TTS calls are
not enabled in this phase.

Run `yarn test` for IndexedDB behavior tests and `yarn build` for a production
bundle.
