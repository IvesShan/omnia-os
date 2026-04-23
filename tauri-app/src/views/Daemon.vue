<template>
  <div class="daemon">
    <h1>🎛️ Daemon Control</h1>
    <div class="status">
      <span class="label">Status:</span>
      <span :class="['value', running ? 'online' : 'offline']">
        {{ running ? 'Running (PID: ' + pid + ')' : 'Stopped' }}
      </span>
    </div>
    <div class="controls">
      <button @click="startDaemon" :disabled="running">Start</button>
      <button @click="stopDaemon" :disabled="!running">Stop</button>
      <button @click="restartDaemon">Restart</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'

const running = ref(false)
const pid = ref(0)

const checkStatus = async () => {
  try {
    const status = await invoke('get_status')
    running.value = !!status.daemon_pid
    pid.value = status.daemon_pid || 0
  } catch (e) {
    console.error(e)
  }
}

const startDaemon = async () => {
  await invoke('start_daemon')
  setTimeout(checkStatus, 1000)
}

const stopDaemon = async () => {
  await invoke('stop_daemon')
  setTimeout(checkStatus, 1000)
}

const restartDaemon = async () => {
  await stopDaemon()
  setTimeout(startDaemon, 1000)
}

onMounted(checkStatus)
</script>

<style scoped>
.daemon { padding: 20px; }
.status { margin: 20px 0; padding: 20px; background: #1a1a2e; border-radius: 12px; }
.status .label { color: #888; margin-right: 10px; }
.status .value.online { color: #00ff88; }
.status .value.offline { color: #ff4444; }
.controls { display: flex; gap: 12px; }
.controls button { padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; background: #00d9ff; color: #000; font-weight: bold; }
.controls button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>