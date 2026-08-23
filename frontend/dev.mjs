import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(frontendDir, '..')
const isWindows = process.platform === 'win32'
const pythonCommand = process.env.PYTHON || (isWindows ? 'wsl.exe' : 'python')
const pythonArgs = isWindows
  ? ['.venv-wsl/bin/uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8002']
  : ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8002']

const backend = spawn(pythonCommand, pythonArgs, { cwd: rootDir, stdio: 'inherit' })
const vite = spawn(process.execPath, [path.join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js')], { cwd: frontendDir, stdio: 'inherit' })

function stop(code = 0) {
  backend.kill()
  vite.kill()
  process.exit(code)
}

backend.on('exit', (code) => { if (code && vite.exitCode === null) stop(code) })
vite.on('exit', (code) => stop(code || 0))
process.on('SIGINT', () => stop())
process.on('SIGTERM', () => stop())
