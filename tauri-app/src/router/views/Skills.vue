<template>
  <div class="skills-view">
    <h2>技能中心</h2>
    <div class="skills-list">
      <div v-for="skill in store.skills" :key="skill.id" class="skill-item">
        <span class="skill-name">{{ skill.name }}</span>
        <button @click="store.toggleSkill(skill.id, !skill.enabled)">
          {{ skill.enabled ? '禁用' : '启用' }}
        </button>
      </div>
      <div v-if="store.skills.length === 0" class="empty">暂无技能</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useOmniaStore } from '../stores/omnia'

const store = useOmniaStore()

onMounted(() => {
  store.fetchSkills()
})
</script>

<style scoped>
.skills-view { padding: 20px; }
.skills-list { margin-top: 20px; }
.skill-item { display: flex; justify-content: space-between; align-items: center; background: #1a1a2e; padding: 15px; margin: 10px 0; border-radius: 8px; }
.skill-name { font-size: 16px; }
.skill-item button { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; background: #00d9ff; }
.empty { color: #666; text-align: center; margin-top: 40px; }
</style>