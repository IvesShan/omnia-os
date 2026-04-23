<template>
  <div class="app">
    <!-- Header -->
    <header class="header">
      <div class="logo">
        <span class="logo-icon">♾️</span>
        <h1>Omnia Manager</h1>
      </div>
      <div class="status-indicator" :class="{ online: apiOnline, offline: !apiOnline }">
        {{ apiOnline ? '🟢 在线' : '🔴 离线' }}
      </div>
    </header>

    <!-- Navigation -->
    <nav class="nav">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        :class="['nav-btn', { active: currentTab === tab.id }]"
        @click="currentTab = tab.id"
      >
        <span class="nav-icon">{{ tab.icon }}</span>
        {{ tab.name }}
      </button>
    </nav>

    <!-- Content -->
    <main class="content">
      <!-- Dashboard -->
      <div v-if="currentTab === 'dashboard'" class="dashboard">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-icon">💾</div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.facts }}</div>
              <div class="stat-label">Facts</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🔗</div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.relations }}</div>
              <div class="stat-label">Relations</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🔄</div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.habits }}</div>
              <div class="stat-label">Habits</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📅</div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.timeline }}</div>
              <div class="stat-label">Timeline</div>
            </div>
          </div>
        </div>

        <div class="daemon-status">
          <h3>守护进程状态</h3>
          <div class="status-row">
            <span class="status-label">PID:</span>
            <span class="status-value">{{ daemonPid || '未运行' }}</span>
          </div>
          <div class="status-row">
            <span class="status-label">API:</span>
            <span class="status-value">{{ apiOnline ? 'http://localhost:6789' : '未响应' }}</span>
          </div>
        </div>
      </div>

      <!-- Control -->
      <div v-if="currentTab === 'control'" class="control-panel">
        <h2>服务控制</h2>
        <div class="control-buttons">
          <button class="control-btn start" @click="startDaemon" :disabled="daemonPid">
            <span class="btn-icon">▶️</span>
            启动守护进程
          </button>
          <button class="control-btn stop" @click="stopDaemon" :disabled="!daemonPid">
            <span class="btn-icon">⏹️</span>
            停止守护进程
          </button>
          <button class="control-btn restart" @click="restartDaemon" :disabled="!daemonPid">
            <span class="btn-icon">🔄</span>
            重启守护进程
          </button>
        </div>
      </div>

      <!-- Logs -->
      <div v-if="currentTab === 'logs'" class="logs-panel">
        <div class="logs-header">
          <h2>日志查看</h2>
          <button class="refresh-btn" @click="loadLogs">🔄 刷新</button>
        </div>
        <div class="logs-container">
          <div v-for="(log, index) in logs" :key="index" class="log-line">
            {{ log }}
          </div>
          <div v-if="logs.length === 0" class="logs-empty">
            暂无日志
          </div>
        </div>
      </div>

      <!-- Backup -->
      <div v-if="currentTab === 'backup'" class="backup-panel">
        <h2>备份管理</h2>
        <div class="backup-actions">
          <button class="backup-btn" @click="createBackup">
            <span class="btn-icon">💾</span>
            创建备份
          </button>
          <button class="backup-btn" @click="listBackups">
            <span class="btn-icon">📂</span>
            查看备份列表
          </button>
        </div>
        <div v-if="backups.length > 0" class="backups-list">
          <h3>可用备份</h3>
          <div v-for="backup in backups" :key="backup.name" class="backup-item">
            <span class="backup-name">{{ backup.name }}</span>
            <span class="backup-size">{{ backup.size }}</span>
            <button class="restore-btn" @click="restoreBackup(backup.name)">恢复</button>
          </div>
        </div>
      </div>

      <!-- Search -->
      <div v-if="currentTab === 'search'" class="search-panel">
        <h2>记忆搜索</h2>
        <div class="search-box">
          <input 
            v-model="searchQuery" 
            placeholder="输入关键词搜索..."
            @keyup.enter="searchMemory"
          />
          <button class="search-btn" @click="searchMemory">🔍 搜索</button>
        </div>
        <div v-if="searchResults.length > 0" class="search-results">
          <div v-for="result in searchResults" :key="result.id" class="result-item">
            <div class="result-category">[{{ result.category }}]</div>
            <div class="result-key">{{ result.key }}:</div>
            <div class="result-value">{{ result.value }}</div>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <span>Omnia v1.0 | 记忆宫殿系统</span>
    </footer>
  </div>
</template>

<script>
import { invoke } from '@tauri-apps/api/core'

export default {
  name: 'App',
  data() {
    return {
      currentTab: 'dashboard',
      tabs: [
        { id: 'dashboard', name: '仪表盘', icon: '📊' },
        { id: 'control', name: '控制', icon: '⚙️' },
        { id: 'logs', name: '日志', icon: '📝' },
        { id: 'backup', name: '备份', icon: '💾' },
        { id: 'search', name: '搜索', icon: '🔍' },
      ],
      stats: { facts: 0, relations: 0, habits: 0, timeline: 0 },
      daemonPid: null,
      apiOnline: false,
      logs: [],
      backups: [],
      searchQuery: '',
      searchResults: [],
    }
  },
  async mounted() {
    await this.loadStatus()
    setInterval(this.loadStatus, 5000) // 每5秒刷新状态
  },
  methods: {
    async loadStatus() {
      try {
        const status = await invoke('get_status')
        this.stats = status.stats
        this.daemonPid = status.daemon_pid
        this.apiOnline = status.api_online
      } catch (error) {
        console.error('Failed to load status:', error)
      }
    },
    async startDaemon() {
      try {
        await invoke('start_daemon')
        await this.loadStatus()
      } catch (error) {
        console.error('Failed to start daemon:', error)
      }
    },
    async stopDaemon() {
      try {
        await invoke('stop_daemon')
        await this.loadStatus()
      } catch (error) {
        console.error('Failed to stop daemon:', error)
      }
    },
    async restartDaemon() {
      try {
        await invoke('restart_daemon')
        await this.loadStatus()
      } catch (error) {
        console.error('Failed to restart daemon:', error)
      }
    },
    async loadLogs() {
      try {
        this.logs = await invoke('get_logs')
      } catch (error) {
        console.error('Failed to load logs:', error)
      }
    },
    async createBackup() {
      try {
        const result = await invoke('create_backup')
        console.log('Backup created:', result)
        await this.listBackups()
      } catch (error) {
        console.error('Failed to create backup:', error)
      }
    },
    async listBackups() {
      try {
        this.backups = await invoke('list_backups')
      } catch (error) {
        console.error('Failed to list backups:', error)
      }
    },
    async restoreBackup(name) {
      try {
        await invoke('restore_backup', { name })
        await this.loadStatus()
      } catch (error) {
        console.error('Failed to restore backup:', error)
      }
    },
    async searchMemory() {
      if (!this.searchQuery) return
      try {
        this.searchResults = await invoke('search_memory', { query: this.searchQuery })
      } catch (error) {
        console.error('Failed to search memory:', error)
      }
    },
  },
}
</script>
