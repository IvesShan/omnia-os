<template>
  <div class="logs">
    <h1>📝 Logs</h1>
    <pre class="log-content">{{ logs }}</pre>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'

const logs = ref('Loading...')

onMounted(async () => {
  try {
    logs.value = await invoke('get_logs')
  } catch (e) {
    logs.value = 'Error: ' + e
  }
})
</script>

<style scoped>
.logs { padding: 20px; }
.log-content { background: #1a1a2e; padding: 20px; border-radius: 12px; overflow: auto; max-height: 500px; font-family: monospace; font-size: 12px; }
</style>