/**
 * 神经图谱高级可视化 - 增强版
 * 集成路径查找、中心度分析、社区发现
 * 配合 5001 端口 WebUI HUD 面板
 */

const NeuralGraphAdvanced = {
  // 状态
  initialized: false,
  currentView: 'brain', // brain, centrality, communities, paths
  
  // 数据缓存
  stats: null,
  nodes: [],
  edges: [],
  centrality: {},
  communities: [],
  
  // 类型颜色
  typeColors: {
    'PERSON': '#22d3ee',
    'PROJECT': '#a855f7',
    'FILE': '#10b981',
    'CONCEPT': '#ff8a00',
    'DATE': '#6366f1',
    'LOCATION': '#ec4899',
    'ENTITY': '#94a3b8',
    'DEFAULT': '#64748b'
  },
  
  // 初始化
  async init() {
    if (this.initialized) return;
    
    console.log('[NeuralGraph] 初始化高级图谱...');
    
    // 加载数据
    await Promise.all([
      this.loadStats(),
      this.loadCentrality(),
      this.loadCommunities()
    ]);
    
    this.initialized = true;
    this.render();
    
    console.log('[NeuralGraph] 初始化完成:', {
      nodes: this.stats?.nodes,
      edges: this.stats?.edges,
      communities: this.communities.length
    });
  },
  
  // 加载统计
  async loadStats() {
    try {
      const res = await fetch('/api/graph/stats');
      this.stats = await res.json();
      
      // 更新 HUD 显示
      const nodesEl = document.getElementById('gs-nodes');
      const edgesEl = document.getElementById('gs-edges');
      if (nodesEl) nodesEl.textContent = this.stats.nodes || '—';
      if (edgesEl) edgesEl.textContent = this.stats.edges || '—';
      
      console.log('[NeuralGraph] 统计:', this.stats);
    } catch (e) {
      console.error('[NeuralGraph] 加载统计失败:', e);
    }
  },
  
  // 加载中心度
  async loadCentrality() {
    try {
      const [degree, pagerank, betweenness] = await Promise.all([
        fetch('/api/graph/centrality/degree?top_k=10').then(r => r.json()),
        fetch('/api/graph/centrality/pagerank?top_k=10').then(r => r.json()),
        fetch('/api/graph/centrality/betweenness?top_k=10').then(r => r.json())
      ]);
      
      this.centrality = { degree, pagerank, betweenness };
      console.log('[NeuralGraph] 中心度:', this.centrality);
    } catch (e) {
      console.error('[NeuralGraph] 加载中心度失败:', e);
    }
  },
  
  // 加载社区
  async loadCommunities() {
    try {
      const res = await fetch('/api/graph/communities');
      const data = await res.json();
      this.communities = data.communities || [];
      console.log('[NeuralGraph] 社区:', this.communities.length, '个');
    } catch (e) {
      console.error('[NeuralGraph] 加载社区失败:', e);
    }
  },
  
  // 搜索节点
  async searchNodes(query) {
    if (!query) return [];
    
    try {
      const res = await fetch(`/api/graph/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      return data.results || [];
    } catch (e) {
      console.error('[NeuralGraph] 搜索失败:', e);
      return [];
    }
  },
  
  // 查找路径
  async findPath(startId, endId) {
    try {
      const res = await fetch(`/api/graph/path?start_id=${startId}&end_id=${endId}`);
      return await res.json();
    } catch (e) {
      console.error('[NeuralGraph] 路径查找失败:', e);
      return { found: false };
    }
  },
  
  // 获取邻居
  async getNeighbors(nodeId) {
    try {
      const res = await fetch(`/api/graph/neighbors/${nodeId}`);
      return await res.json();
    } catch (e) {
      console.error('[NeuralGraph] 获取邻居失败:', e);
      return {};
    }
  },
  
  // 渲染
  render() {
    this.renderCentralityPanel();
    this.renderCommunitiesPanel();
    this.updateStatus();
  },
  
  // 渲染中心度面板
  renderCentralityPanel() {
    const container = document.getElementById('neural-centrality');
    if (!container || !this.centrality.degree) return;
    
    const topNodes = this.centrality.degree.centrality?.slice(0, 5) || [];
    
    container.innerHTML = `
      <div class="centrality-header">
        <span class="ch-title">影响力排名</span>
        <span class="ch-subtitle">TOP 5</span>
      </div>
      <div class="centrality-list">
        ${topNodes.map((n, i) => `
          <div class="centrality-item" data-node="${n.node}">
            <span class="ci-rank">${i + 1}</span>
            <span class="ci-dot" style="background: ${this.typeColors[n.type] || this.typeColors.DEFAULT}"></span>
            <span class="ci-name">${n.name}</span>
            <span class="ci-score">${n.total}</span>
          </div>
        `).join('')}
      </div>
    `;
    
    // 点击事件
    container.querySelectorAll('.centrality-item').forEach(item => {
      item.addEventListener('click', () => {
        const nodeId = item.dataset.node;
        this.showNodeDetails(nodeId);
      });
    });
  },
  
  // 渲染社区面板
  renderCommunitiesPanel() {
    const container = document.getElementById('neural-communities');
    if (!container || !this.communities.length) return;
    
    const topCommunities = this.communities.slice(0, 5);
    
    container.innerHTML = `
      <div class="communities-header">
        <span class="ch-title">知识社区</span>
        <span class="ch-count">${this.communities.length} 个</span>
      </div>
      <div class="communities-list">
        ${topCommunities.map((c, i) => `
          <div class="community-item" data-community="${c.community_id}">
            <span class="ci-badge" style="background: ${this.typeColors[c.dominant_type] || this.typeColors.DEFAULT}">${c.size}</span>
            <span class="ci-type">${c.dominant_type}</span>
            <span class="ci-members">${c.nodes?.slice(0, 3).map(n => n.name).join(', ')}...</span>
          </div>
        `).join('')}
      </div>
    `;
  },
  
  // 显示节点详情
  async showNodeDetails(nodeId) {
    const neighbors = await this.getNeighbors(nodeId);
    
    const modal = document.getElementById('neural-modal');
    if (!modal) return;
    
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>${neighbors.name || nodeId}</h3>
          <span class="modal-type">${neighbors.type}</span>
          <button class="modal-close" onclick="this.closest('#neural-modal').classList.remove('active')">×</button>
        </div>
        <div class="modal-body">
          <div class="node-section">
            <h4>出度关系 (${neighbors.outgoing?.length || 0})</h4>
            <div class="relation-list">
              ${(neighbors.outgoing || []).slice(0, 10).map(r => `
                <div class="relation-item">
                  <span class="rel-type">${r.relation}</span>
                  <span class="rel-target">${r.target_name}</span>
                </div>
              `).join('')}
            </div>
          </div>
          <div class="node-section">
            <h4>入度关系 (${neighbors.incoming?.length || 0})</h4>
            <div class="relation-list">
              ${(neighbors.incoming || []).slice(0, 10).map(r => `
                <div class="relation-item">
                  <span class="rel-type">${r.relation}</span>
                  <span class="rel-source">${r.source_name}</span>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
    
    modal.classList.add('active');
  },
  
  // 更新状态
  updateStatus() {
    const statusEl = document.getElementById('neural-status');
    if (!statusEl) return;
    
    const status = this.stats?.nodes > 0 ? 'COGNITION ACTIVE' : 'STANDBY';
    const color = this.stats?.nodes > 100 ? '#22c55e' : this.stats?.nodes > 0 ? '#f59e0b' : '#ef4444';
    
    statusEl.textContent = status;
    statusEl.style.color = color;
  },
  
  // 切换视图
  setView(view) {
    this.currentView = view;
    this.render();
  }
};

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
  // 延迟初始化，等待其他组件
  setTimeout(() => {
    NeuralGraphAdvanced.init();
  }, 1000);
});

// 导出
window.NeuralGraphAdvanced = NeuralGraphAdvanced;
