<template>
  <div class="memory-view">
    <h2>记忆系统</h2>
    <div class="stats">
      <div class="stat">Facts: {{ store.memoryStats.facts }}</div>
      <div class="stat">Relations: {{ store.memoryStats.relations }}</div>
      <div class="stat">Habits: {{ store.memoryStats.habits }}</div>
      <div class="stat">Timeline: {{ store.memoryStats.timeline }}</div>
    </div>
    <div class="search-box">
      <input v-model="query" placeholder="搜索记忆..." @keyup.enter="doSearch" />
      <button @click="doSearch">搜索</button>
    </div>
    <div class="results">
      <div v-for="item in results" :key="item.id" class="result-item">
        {{ item.content }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useOmniaStore } from '../stores/omnia'

const store = useOmniaStore()
const query = ref('')
const results = ref([])

onMounted(() => {
  store.fetchMemoryStats()
})

async function doSearch() {
  if (query.value) {
    results.value = await store.searchMemory(query.value)
  }
}
</script>

<style scoped>
.memory-view { padding: 20px; }
.stats { display: flex; gap: 20px; margin: 20px 0; }
.stat { background: #1a1a2e; padding: 15px; border-radius: 8px; }
.search-box { display: flex; gap: 10px; margin: 20px 0; }
.search-box input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #333; }
.search-box button { padding: 10px 20px; border-radius: 8px; border: none; background: #00d9ff; }
.results { margin-top: 20px; }
.result-item { background: #1a1a2e; padding: 10px; margin: 5px 0; border-radius: 8px; }
</style>