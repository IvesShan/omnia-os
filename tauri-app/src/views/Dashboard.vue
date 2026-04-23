<template>
  <div class="dashboard">
    <h1>📊 Dashboard</h1>
    <div class="stats">
      <div class="stat-card">
        <span class="label">Facts</span>
        <span class="value">{{ stats.facts }}</span>
      </div>
      <div class="stat-card">
        <span class="label">Relations</span>
        <span class="value">{{ stats.relations }}</span>
      </div>
      <div class="stat-card">
        <span class="label">Habits</span>
        <span class="value">{{ stats.habits }}</span>
      </div>
      <div class="stat-card">
        <span class="label">Timeline</span>
        <span class="value">{{ stats.timeline }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'

const stats = ref({ facts: 0, relations: 0, habits: 0, timeline: 0 })

onMounted(async () => {
  try {
    const status = await invoke('get_status')
    stats.value = status.stats
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.dashboard { padding: 20px; }
.stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 20px; }
.stat-card { background: #1a1a2e; padding: 20px; border-radius: 12px; text-align: center; }
.stat-card .label { display: block; color: #888; font-size: 14px; }
.stat-card .value { display: block; font-size: 32px; font-weight: bold; color: #00d9ff; margin-top: 8px; }
</style>