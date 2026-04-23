import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:5001'

export const useOmniaStore = defineStore('omnia', () => {
  // State
  const daemonStatus = ref('stopped')
  const daemonPid = ref(null)
  const apiOnline = ref(false)
  const memoryStats = ref({ facts: 0, relations: 0, habits: 0, timeline: 0 })
  const skills = ref([])
  const logs = ref([])
  const isLoading = ref(false)

  // Actions
  async function checkDaemonStatus() {
    try {
      const res = await axios.get(`${API_BASE}/api/status`, { timeout: 2000 })
      apiOnline.value = true
      daemonStatus.value = 'running'
    } catch {
      apiOnline.value = false
      daemonStatus.value = 'stopped'
    }
  }

  async function getDaemonPid() {
    try {
      const res = await axios.get(`${API_BASE}/api/status`)
      daemonPid.value = res.data.pid
      daemonStatus.value = 'running'
    } catch {
      daemonPid.value = null
      daemonStatus.value = 'stopped'
    }
  }

  async function startDaemon() {
    isLoading.value = true
    try {
      await axios.post(`${API_BASE}/api/daemon/start`)
      await getDaemonPid()
    } finally {
      isLoading.value = false
    }
  }

  async function stopDaemon() {
    isLoading.value = true
    try {
      await axios.post(`${API_BASE}/api/daemon/stop`)
      daemonPid.value = null
      daemonStatus.value = 'stopped'
    } finally {
      isLoading.value = false
    }
  }

  async function restartDaemon() {
    isLoading.value = true
    try {
      await axios.post(`${API_BASE}/api/daemon/restart`)
      await getDaemonPid()
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMemoryStats() {
    try {
      const res = await axios.get(`${API_BASE}/api/memory/stats`)
      memoryStats.value = res.data
    } catch (e) {
      console.error('Failed to fetch memory stats:', e)
    }
  }

  async function searchMemory(query, layer = 'all') {
    try {
      const res = await axios.get(`${API_BASE}/api/memory/search`, { params: { q: query, layer } })
      return res.data
    } catch (e) {
      console.error('Failed to search memory:', e)
      return []
    }
  }

  async function fetchSkills() {
    try {
      const res = await axios.get(`${API_BASE}/api/skills`)
      skills.value = res.data
    } catch (e) {
      console.error('Failed to fetch skills:', e)
    }
  }

  async function toggleSkill(skillId, enabled) {
    try {
      await axios.post(`${API_BASE}/api/skills/toggle`, { skill_id: skillId, enabled })
      await fetchSkills()
    } catch (e) {
      console.error('Failed to toggle skill:', e)
    }
  }

  async function fetchLogs(lines = 100) {
    try {
      const res = await axios.get(`${API_BASE}/api/logs`, { params: { lines } })
      logs.value = res.data
    } catch (e) {
      console.error('Failed to fetch logs:', e)
    }
  }

  return {
    daemonStatus,
    daemonPid,
    apiOnline,
    memoryStats,
    skills,
    logs,
    isLoading,
    checkDaemonStatus,
    getDaemonPid,
    startDaemon,
    stopDaemon,
    restartDaemon,
    fetchMemoryStats,
    searchMemory,
    fetchSkills,
    toggleSkill,
    fetchLogs,
  }
})