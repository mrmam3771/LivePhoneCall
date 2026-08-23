# Qwen Voice Frontend

Vue 3 and Vite frontend for the local Qwen voice workspace.

```powershell
yarn
yarn dev
```

The development server listens on all interfaces. Open
`http://127.0.0.1:8000/` on this PC or `http://<PC-LAN-IP>:8000/` from another
device on the same network. Only TCP 8000 needs a `LocalSubnet` Windows Firewall
rule; the API and model ports remain behind Vite's same-origin `/api` proxy.

Mobile browsers require a trusted HTTPS origin before granting microphone
access. Use `scripts/start_mobile_https.ps1` for microphone testing; LAN HTTP is
sufficient for the UI, text chat, and audio playback.

Run `yarn test` for IndexedDB behavior tests and `yarn build` for a production
bundle.
