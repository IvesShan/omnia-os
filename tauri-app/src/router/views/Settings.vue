<template>
  <div class="settings-view">
    <h2>设置</h2>
    <div class="settings-group">
      <div class="setting-item">
        <label>API 地址</label>
        <input v-model="apiUrl" placeholder="http://localhost:5001" />
      </div>
      <div class="setting-item">
        <label>刷新间隔</label>
        <input v-model="refreshInterval" type="number" />
      </div>
    </div>
    <button class="save-btn" @click="saveSettings">保存设置</button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const apiUrl = ref('http://localhost:5001')
const refreshInterval = ref(5000)

function saveSettings() {
  localStorage.setItem('omnia_api_url', apiUrl.value)
  localStorage.setItem('omnia_refresh_interval', refreshInterval.value)
  alert('设置已保存')
}
</script>

<style scoped>
.settings-view { padding: 20px; }
.settings-group { margin: 20px 0; }
.setting-item { display: flex; align-items: center; margin: 15px 0; }
.setting-item label { width: 100px; }
.setting-item input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid #333; background: #1a1a2e; }
.save-btn { padding: 10px 30px; border: none; border-radius: 8px; background: #00d9ff; cursor: pointer; }
</style>