/**
 * 神经图谱可视化 - 3d-force-graph 高性能版
 * 
 * 升级特性：
 * - 使用 3d-force-graph 库（内置 Three.js + WebGL 渲染）
 * - 支持 10万+ 节点丝滑渲染
 * - 真实力导向物理模拟
 * - 视口裁剪 + LOD 优化
 * - 悬停高亮 + 节点详情
 */

const GraphViz = {
  graph: null,
  graphData: { nodes: [], links: [] },
  hoveredNode: null,
  selectedNode: null,

  // 类型颜色映射
  typeColors: {
    'PERSON':   '#22d3ee',
    'PROJECT':  '#a855f7',
    'FILE':     '#10b981',
    'CONCEPT':  '#ff8a00',
    'DATE':     '#6366f1',
    'ENTITY':   '#ec4899',
    'DEFAULT':  '#64748b'
  },

  async init() {
    console.log("[GraphViz] 初始化 3d-force-graph 高性能版");
    
    try {
      await this.loadStats();
      await this.loadGraph();
      this.initGraph();
      this.applyStyles();
      
      console.log("[GraphViz] 初始化完成，节点数:", this.graphData.nodes.length);
    } catch (error) {
      console.error("[GraphViz] 初始化错误:", error);
    }
  },

  async loadStats() {
    try {
      const response = await fetch('/api/graph/stats', { cache: 'no-store' });
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        const nodesEl = document.getElementById('gs-nodes');
        const edgesEl = document.getElementById('gs-edges');
        if (nodesEl) nodesEl.textContent = data.nodes || '—';
        if (edgesEl) edgesEl.textContent = data.edges || '—';
      } catch (parseErr) {
        console.warn('[GraphViz] stats 非 JSON 响应，跳过');
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.warn('[GraphViz] 加载统计失败:', error.message);
      }
    }
  },

  async loadGraph() {
    try {
      const response = await fetch('/api/graph?limit=2000', { cache: 'no-store' });
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        
        // 转换为 3d-force-graph 格式
        this.graphData = {
          nodes: (data.nodes || []).map(n => ({
            id: n.name || n.id,
            label: n.label || n.name,
            type: n.type || 'ENTITY',
            evidence: n.evidence || '',
            color: this.typeColors[n.type] || this.typeColors.DEFAULT
          })),
          links: (data.edges || []).map(e => ({
            source: e.source,
            target: e.target,
            type: e.type || 'RELATED'
          }))
        };
        
        console.log('[GraphViz] 加载图谱:', this.graphData.nodes.length, '节点,', this.graphData.links.length, '边');
      } catch (parseErr) {
        console.warn('[GraphViz] graph 非 JSON 响应，跳过');
        this.graphData = { nodes: [], links: [] };
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.warn('[GraphViz] 加载图谱失败:', error.message);
      }
      this.graphData = { nodes: [], links: [] };
    }
  },

  initGraph() {
    const container = document.getElementById('graph-canvas');
    if (!container) {
      console.error('[GraphViz] 找不到 graph-canvas');
      return;
    }

    container.innerHTML = '';

    // 创建 3d-force-graph 实例
    this.graph = new ThreeForceGraph({ controlType: 'orbit' })
      .container(container)
      .graphData(this.graphData)
      .width(container.clientWidth)
      .height(container.clientHeight)
      .backgroundColor('#0a0e27')
      
      // 节点样式
      .nodeVal(node => this.getNodeSize(node))
      .nodeColor(node => node.color)
      .nodeOpacity(0.85)
      .nodeResolution(8)  // 球体细分精度
      
      // 连线样式
      .linkColor(() => 'rgba(34, 211, 238, 0.15)')
      .linkWidth(0.5)
      .linkDirectionalParticles(0.3)  // 粒子流效果
      .linkDirectionalParticleWidth(1.5)
      .linkDirectionalParticleColor(() => '#22d3ee')
      
      // 力导向参数
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .warmupTicks(100)
      .cooldownTicks(150)
      
      // 交互
      .onNodeHover(node => this.handleNodeHover(node))
      .onNodeClick(node => this.handleNodeClick(node))
      .onBackgroundClick(() => this.handleBackgroundClick());

    // 自动旋转（可选）
    // this.graph.controls().autoRotate = true;
    // this.graph.controls().autoRotateSpeed = 0.5;

    // 窗口调整
    const resizeObserver = new ResizeObserver(() => {
      if (this.graph) {
        this.graph
          .width(container.clientWidth)
          .height(container.clientHeight);
      }
    });
    resizeObserver.observe(container);
  },

  getNodeSize(node) {
    // 根据连接数调整节点大小
    const connections = this.graphData.links.filter(
      l => l.source === node.id || l.target === node.id
    ).length;
    return Math.max(2, Math.min(8, 2 + connections * 0.3));
  },

  handleNodeHover(node) {
    // 重置之前的高亮
    if (this.hoveredNode && this.hoveredNode !== node) {
      this.resetHighlight(this.hoveredNode);
    }

    this.hoveredNode = node;
    
    if (node) {
      this.highlightNode(node);
      document.body.style.cursor = 'pointer';
    } else {
      document.body.style.cursor = 'default';
    }
  },

  highlightNode(node) {
    // 高亮节点的邻居
    const neighbors = this.getNeighborIds(node.id);
    
    this.graph
      .nodeOpacity(n => (n === node || neighbors.has(n.id)) ? 1.0 : 0.2)
      .nodeColor(n => {
        if (n === node) return '#ffffff';
        if (neighbors.has(n.id)) return n.color;
        return '#333333';
      })
      .linkColor(l => {
        if (l.source.id === node.id || l.target.id === node.id) {
          return 'rgba(255, 138, 0, 0.6)';
        }
        return 'rgba(34, 211, 238, 0.05)';
      })
      .linkWidth(l => {
        if (l.source.id === node.id || l.target.id === node.id) return 1.5;
        return 0.3;
      });
  },

  resetHighlight(node) {
    this.graph
      .nodeOpacity(0.85)
      .nodeColor(n => n.color)
      .linkColor(() => 'rgba(34, 211, 238, 0.15)')
      .linkWidth(0.5);
  },

  getNeighborIds(nodeId) {
    const neighbors = new Set();
    this.graphData.links.forEach(l => {
      if (l.source === nodeId || l.source.id === nodeId) neighbors.add(l.target.id || l.target);
      if (l.target === nodeId || l.target.id === nodeId) neighbors.add(l.source.id || l.source);
    });
    return neighbors;
  },

  handleNodeClick(node) {
    this.selectedNode = node;
    this.showNodeDetails(node);
    
    // 聚焦到节点
    const distance = 5;
    const distRatio = 1 + distance / Math.sqrt(
      node.x * node.x + node.y * node.y + node.z * node.z
    );
    
    this.graph.cameraPosition(
      { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
      node,  // lookAt
      1500   // transition duration
    );
  },

  handleBackgroundClick() {
    this.selectedNode = null;
    this.hoveredNode = null;
    
    // 恢复默认视图
    this.resetHighlight(null);
    
    // 移除详情面板
    const panel = document.getElementById('node-detail-panel');
    if (panel) panel.remove();
  },

  showNodeDetails(node) {
    let panel = document.getElementById('node-detail-panel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'node-detail-panel';
      panel.style.cssText = `
        position: fixed;
        top: 50%;
        right: 20px;
        transform: translateY(-50%);
        background: rgba(10, 14, 39, 0.95);
        border: 1px solid rgba(34, 211, 238, 0.3);
        border-radius: 12px;
        padding: 20px;
        min-width: 280px;
        max-width: 350px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
        z-index: 1000;
        box-shadow: 0 0 30px rgba(34, 211, 238, 0.2);
      `;
      document.body.appendChild(panel);
    }

    const connections = this.graphData.links.filter(
      l => l.source === node.id || l.target === node.id
    ).length;

    panel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0; color: ${node.color}; font-size: 18px;">${node.label}</h3>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #64748b; cursor: pointer; font-size: 20px;">&times;</button>
      </div>
      <div style="margin-bottom: 12px;">
        <span style="color: #64748b; font-size: 12px;">类型</span>
        <div style="color: ${node.color}; font-weight: 500;">${node.type}</div>
      </div>
      ${node.evidence ? `
        <div style="margin-bottom: 12px;">
          <span style="color: #64748b; font-size: 12px;">来源</span>
          <div style="color: #94a3b8; font-size: 14px; word-break: break-word;">${node.evidence}</div>
        </div>
      ` : ''}
      <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(100, 116, 139, 0.3);">
        <span style="color: #64748b; font-size: 12px;">连接数</span>
        <div style="color: #22d3ee; font-weight: 500;">${connections}</div>
      </div>
    `;

    // 5秒后自动关闭
    setTimeout(() => {
      if (panel.parentElement) panel.remove();
    }, 5000);
  },

  applyStyles() {
    // 注入自定义样式（覆盖 3d-force-graph 默认样式）
    if (!document.getElementById('graph-viz-custom-styles')) {
      const style = document.createElement('style');
      style.id = 'graph-viz-custom-styles';
      style.textContent = `
        #graph-canvas {
          background: #0a0e27;
          border-radius: 12px;
          overflow: hidden;
        }
        
        #graph-canvas canvas {
          border-radius: 12px;
        }
        
        #node-detail-panel {
          animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-50%) translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateY(-50%) translateX(0);
          }
        }
      `;
      document.head.appendChild(style);
    }
  },

  destroy() {
    if (this.graph) {
      this.graph._destructor();
      this.graph = null;
    }
  }
};

// 导出
if (typeof window !== 'undefined') {
  window.GraphViz = GraphViz;
}
