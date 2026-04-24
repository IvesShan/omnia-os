<template>
  <div class="memory">
    <div class="header">
      <h1>🧠 Memory Palace</h1>
      <div class="stats">
        <span class="stat-item">
          <span class="stat-label">节点:</span>
          <span class="stat-value">{{ nodeCount }}</span>
        </span>
        <span class="stat-item">
          <span class="stat-label">连接:</span>
          <span class="stat-value">{{ edgeCount }}</span>
        </span>
      </div>
    </div>
    
    <div class="controls">
      <button @click="resetView" class="control-btn">重置视图</button>
      <button @click="togglePhysics" class="control-btn">
        {{ physicsEnabled ? '暂停物理' : '启用物理' }}
      </button>
      <select v-model="selectedLayer" class="layer-select">
        <option value="">全部层级</option>
        <option value="facts">事实</option>
        <option value="relations">关系</option>
        <option value="habits">习惯</option>
        <option value="timeline">时间线</option>
      </select>
    </div>
    
    <div ref="graphContainer" class="graph-container"></div>
    
    <div v-if="selectedNode" class="node-detail">
      <h3>{{ selectedNode.label }}</h3>
      <p><strong>类型:</strong> {{ selectedNode.type }}</p>
      <p><strong>ID:</strong> {{ selectedNode.id }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import ForceGraph from 'force-graph'

const graphContainer = ref(null)
const selectedNode = ref(null)
const nodeCount = ref(0)
const edgeCount = ref(0)
const physicsEnabled = ref(true)
const selectedLayer = ref('')

let graph = null
let graphData = { nodes: [], links: [] }

// 颜色映射
const typeColors = {
  PERSON: '#4CAF50',
  PROJECT: '#2196F3',
  CONCEPT: '#FF9800',
  EVENT: '#E91E63',
  SKILL: '#9C27B0',
  TOOL: '#00BCD4',
  MEMORY: '#607D8B',
  DEFAULT: '#90A4AE'
}

// 层级颜色
const layerColors = {
  facts: '#4CAF50',
  relations: '#2196F3',
  habits: '#FF9800',
  timeline: '#E91E63'
}

onMounted(async () => {
  await loadGraphData()
  initGraph()
})

onUnmounted(() => {
  if (graph) {
    graph._destructor()
  }
})

watch(selectedLayer, () => {
  updateGraphFilter()
})

async function loadGraphData() {
  try {
    // 从数据库加载节点和边
    const response = await fetch('http://localhost:8765/api/memory/neural-graph')
    if (response.ok) {
      const data = await response.json()
      graphData = data
      nodeCount.value = data.nodes.length
      edgeCount.value = data.links.length
    } else {
      // 使用模拟数据
      generateMockData()
    }
  } catch (error) {
    console.log('Using mock data:', error.message)
    generateMockData()
  }
}

function generateMockData() {
  // 生成模拟数据用于演示
  const nodes = [
    { id: 'omnia', label: 'Omnia', type: 'PROJECT' },
    { id: 'infinite', label: '无限', type: 'PERSON' },
    { id: 'user', label: '原点', type: 'PERSON' },
    { id: 'memory', label: '记忆系统', type: 'CONCEPT' },
    { id: 'neural', label: '神经图谱', type: 'CONCEPT' },
    { id: 'dji', label: 'DJI', type: 'PROJECT' },
    { id: 'repair', label: '无人机维修', type: 'SKILL' },
    { id: 'miaoxiujiang', label: '喵修匠', type: 'TOOL' },
    { id: 'dongjidi', label: '懂机帝', type: 'PROJECT' },
    { id: 'tauri', label: 'Tauri', type: 'TOOL' },
    { id: 'vue', label: 'Vue.js', type: 'TOOL' },
    { id: 'python', label: 'Python', type: 'SKILL' },
    { id: 'sqlite', label: 'SQLite', type: 'TOOL' },
    { id: 'force-graph', label: 'Force Graph', type: 'TOOL' },
  ]
  
  const links = [
    { source: 'omnia', target: 'infinite', type: 'has_persona' },
    { source: 'omnia', target: 'user', type: 'owned_by' },
    { source: 'omnia', target: 'memory', type: 'contains' },
    { source: 'memory', target: 'neural', type: 'visualizes' },
    { source: 'neural', target: 'force-graph', type: 'uses' },
    { source: 'infinite', target: 'user', type: 'assists' },
    { source: 'user', target: 'dji', type: 'runs' },
    { source: 'dji', target: 'repair', type: 'focuses_on' },
    { source: 'dji', target: 'miaoxiujiang', type: 'uses' },
    { source: 'dji', target: 'dongjidi', type: 'developing' },
    { source: 'omnia', target: 'tauri', type: 'built_with' },
    { source: 'omnia', target: 'vue', type: 'built_with' },
    { source: 'omnia', target: 'python', type: 'uses' },
    { source: 'memory', target: 'sqlite', type: 'stores_in' },
  ]
  
  graphData = { nodes, links }
  nodeCount.value = nodes.length
  edgeCount.value = links.length
}

function initGraph() {
  if (!graphContainer.value) return
  
  graph = ForceGraph()(graphContainer.value)
    .graphData(graphData)
    .nodeId('id')
    .nodeLabel(node => `${node.label} (${node.type})`)
    .nodeColor(node => typeColors[node.type] || typeColors.DEFAULT)
    .nodeVal(node => {
      // 根据连接数调整节点大小
      const connections = graphData.links.filter(
        l => l.source === node.id || l.target === node.id
      ).length
      return Math.max(1, connections * 0.5)
    })
    .nodeCanvasObject((node, ctx, globalScale) => {
      const label = node.label
      const fontSize = 12 / globalScale
      ctx.font = `${fontSize}px Sans-Serif`
      
      // 节点圆圈
      ctx.beginPath()
      ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI)
      ctx.fillStyle = typeColors[node.type] || typeColors.DEFAULT
      ctx.fill()
      
      // 节点标签
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, node.x, node.y - 8)
    })
    .linkSource('source')
    .linkTarget('target')
    .linkLabel(link => link.type)
    .linkColor(() => 'rgba(255, 255, 255, 0.2)')
    .linkWidth(1)
    .linkDirectionalParticles(2)
    .linkDirectionalParticleSpeed(0.005)
    .linkDirectionalParticleColor(() => '#00BCD4')
    .onNodeClick(node => {
      selectedNode.value = node
    })
    .onNodeDragEnd(node => {
      node.fx = node.x
      node.fy = node.y
    })
    .cooldownTicks(100)
    .onEngineStop(() => {
      console.log('Graph stabilized')
    })
  
  // 设置容器尺寸
  const resizeObserver = new ResizeObserver(entries => {
    for (let entry of entries) {
      const { width, height } = entry.contentRect
      graph.width(width).height(height)
    }
  })
  resizeObserver.observe(graphContainer.value)
}

function resetView() {
  if (!graph) return
  
  // 重置缩放和平移
  graph.zoomToFit(400)
  
  // 清除固定位置
  graphData.nodes.forEach(node => {
    node.fx = undefined
    node.fy = undefined
  })
  
  // 重新加热
  graph.reheat()
  graph.cooldownTicks(100)
}

function togglePhysics() {
  if (!graph) return
  
  physicsEnabled.value = !physicsEnabled.value
  if (physicsEnabled.value) {
    graph.reheat()
    graph.cooldownTicks(100)
  } else {
    graph.cooldownTicks(0)
  }
}

function updateGraphFilter() {
  if (!graph) return
  
  // 根据选择的层级过滤节点
  // 这里需要根据实际数据结构调整
  graph.graphData(graphData)
}
</script>

<style scoped>
.memory {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #e0e0e0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header h1 {
  margin: 0;
  font-size: 24px;
  background: linear-gradient(90deg, #4CAF50, #00BCD4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.stat-label {
  color: #90A4AE;
}

.stat-value {
  color: #00BCD4;
  font-weight: bold;
}

.controls {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.control-btn {
  padding: 8px 16px;
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid #4CAF50;
  color: #4CAF50;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.control-btn:hover {
  background: rgba(76, 175, 80, 0.3);
  transform: translateY(-2px);
}

.layer-select {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
}

.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.node-detail {
  position: absolute;
  bottom: 20px;
  right: 20px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  max-width: 300px;
}

.node-detail h3 {
  margin: 0 0 8px 0;
  color: #00BCD4;
}

.node-detail p {
  margin: 4px 0;
  font-size: 14px;
}
</style>
