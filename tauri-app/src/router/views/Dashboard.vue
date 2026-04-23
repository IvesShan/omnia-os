<template>
  <div class="dashboard-view">
    <h2>仪表盘</h2>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">💾</div>
        <div class="stat-value">{{ stats.facts }}</div>
        <div class="stat-label">Facts</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔗</div>
        <div class="stat-value">{{ stats.relations }}</div>
        <div class="stat-label">Relations</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔄</div>
        <div class="stat-value">{{ stats.habits }}</div>
        <div class="stat-label">Habits</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📅</div>
        <div class="stat-value">{{ stats.timeline }}</div>
        <div class="stat-label">Timeline</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useOmniaStore } from '../stores/omnia'

const store = useOmniaStore()
const stats = ref({ facts: 0, relations: 0, habits: 0, timeline: 0 })

onMounted(async () => {
  await store.fetchMemoryStats()
  stats.value = store.memoryStats
})
</script>

<style scoped>
.dashboard-view { padding: 20px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 20px; }
.stat-card { background: #1a1a2e; padding: 20px; border-radius: 12px; text-align: center; }
.stat-icon { font-size: 32px; }
.stat-value { font-size: 28px; font-weight: bold; color: #00d9ff; margin: 10px 0; }
.stat-label { color: #888; }
</style>