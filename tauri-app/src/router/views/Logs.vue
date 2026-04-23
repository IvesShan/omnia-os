<template>
  <div class="logs-view">
    <div class="logs-header">
      <h2>日志</h2>
      <button @click="store.fetchLogs">🔄 刷新</button>
    </div>
    <div class="logs-container">
      <div v-for="(log, index) in store.logs" :key="index" class="log-line">
        {{ log }}
      </div>
      <div v-if="store.logs.length === 0" class="empty">暂无日志</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useOmniaStore } from '../stores/omnia'

const store = useOmniaStore()

onMounted(() => {
  store.fetchLogs()
})
</script>

<style scoped>
.logs-view { padding: 20px; }
.logs-header { display: flex; justify-content: space-between; align-items: center; }
.logs-container { background: #0d0d1a; padding: 15px; border-radius: 8px; margin-top: 15px; max-height: 500px; overflow-y: auto; }
.log-line { font-family: monospace; font-size: 12px; padding: 3px 0; color: #00ff88; }
.empty { color: #666; text-align: center; margin-top: 40px; }
button { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; background: #00d9ff; }
</style>