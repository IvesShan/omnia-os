import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Daemon from '../views/Daemon.vue'
import Memory from '../views/Memory.vue'
import Skills from '../views/Skills.vue'
import Logs from '../views/Logs.vue'
import Settings from '../views/Settings.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/daemon', name: 'Daemon', component: Daemon },
  { path: '/memory', name: 'Memory', component: Memory },
  { path: '/skills', name: 'Skills', component: Skills },
  { path: '/logs', name: 'Logs', component: Logs },
  { path: '/settings', name: 'Settings', component: Settings },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router