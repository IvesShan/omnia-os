<template>
  <div class="daemon-view">
    <h2>守护进程</h2>
    <div class="status-card">
      <div class="status-row">
        <span>状态:</span>
        <span :class="['status-badge', store.daemonStatus]">{{ store.daemonStatus }}</span>
      </div>
      <div class="status-row">
        <span>PID:</span>
        <span>{{ store.daemonPid || '未运行' }}</span>
      </div>
    </div>
    <div class="control-buttons">
      <button @click="store.startDaemon" :disabled="store.daemonPid">启动</button>
      <button @click="store.stopDaemon" :disabled="!store.daemonPid">停止</button>
      <button @click="store.restartDaemon" :disabled="!store.daemonPid">重启</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useOmniaStore } from '../stores/omnia'

const store = useOmniaStore()

onMounted(() => {
  store.getDaemonPid()
})
</script>

<style scoped>
.daemon-view { padding: 20px; }
.status-card { background: #1a1a2e; padding: 20px; border-radius: 12px; margin: 20px 0; }
.status-row { display: flex; justify-content: space-between; padding: 10px 0; }
.status-badge.running { color: #00ff88; }
.status-badge.stopped { color: #ff4444; }
.control-buttons { display: flex; gap: 10px; }
button { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; }
button:disabled { opacity: 0.5; }
</style>