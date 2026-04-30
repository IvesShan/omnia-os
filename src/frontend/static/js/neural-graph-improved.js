/**
 * Omnia 神经图谱 - 改进版
 * 添加搜索、筛选、节点详情功能
 * Obsidian 风格：悬停高亮、节点发光、力导向动画
 */

class NeuralGraphImproved {
  constructor(container) {
    this.container = container;
    this.graph = null;
    this.data = { nodes: [], links: [] };
    this.originalData = { nodes: [], links: [] };
    this.selectedNode = null;
    this.hoveredNode = null;
    this.searchTerm = '';
    this.filterType = 'all';
    
    // 类型颜色映射
    this.typeColors = {
      'PERSON': '#f43f5e',
      'PROJECT': '#6366f1',
      'FILE': '#10b981',
      'CONCEPT': '#f59e0b',
      'DATE': '#8b5cf6',
      'LOCATION': '#06b6d4',
      'ENTITY': '#ec4899'
    };
    
    this.init();
  }
  
  async init() {
    // 检查库是否已加载
    if (typeof ForceGraph3D === 'undefined') {
      this.container.innerHTML = '<p class="text-red-400 text-center p-8">❌ 3D Force Graph 库未加载，请刷新页面</p>';
      return;
    }
    
    // 创建控制面板
    this.createControlPanel();
    
    // 加载数据
    await this.loadData();
    
    // 创建图谱
    this.createGraph();
  }
  
  createControlPanel() {
    const panel = document.createElement('div');
    panel.className = 'graph-control-panel';
    panel.innerHTML = `
      <div class="graph-search-box">
        <input type="text" id="graph-search-input" placeholder="搜索节点..." class="graph-search-input">
      </div>
      <div class="graph-filter-buttons">
        <button data-type="all" class="filter-btn active">全部</button>
        <button data-type="PERSON" class="filter-btn">人物</button>
        <button data-type="PROJECT" class="filter-btn">项目</button>
        <button data-type="FILE" class="filter-btn">文件</button>
        <button data-type="CONCEPT" class="filter-btn">概念</button>
      </div>
      <div id="node-detail-panel" class="node-detail-panel hidden">
        <div class="node-detail-header">
          <span id="node-name"></span>
          <button id="close-detail" class="close-btn">×</button>
        </div>
        <div class="node-detail-body">
          <div class="detail-row">
            <span class="detail-label">类型:</span>
            <span id="node-type"></span>
          </div>
          <div class="detail-row">
            <span class="detail-label">连接数:</span>
            <span id="node-connections"></span>
          </div>
        </div>
      </div>
      <div class="graph-hint" style="margin-top: 8px; font-size: 11px; color: #6b7280; text-align: center;">
        悬停高亮 | 拖拽移动 | 点击详情
      </div>
    `;
    
    this.container.appendChild(panel);
    
    // 绑定事件
    const searchInput = panel.querySelector('#graph-search-input');
    searchInput.addEventListener('input', (e) => {
      this.searchTerm = e.target.value.toLowerCase();
      this.filterData();
    });
    
    const filterButtons = panel.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.filterType = btn.dataset.type;
        this.filterData();
      });
    });
    
    const closeBtn = panel.querySelector('#close-detail');
    closeBtn.addEventListener('click', () => {
      panel.querySelector('#node-detail-panel').classList.add('hidden');
    });
  }
  
  async loadData() {
    try {
      // 加载神经图谱数据
      const graphResponse = await fetch('/api/graph');
      const graphData = await graphResponse.json();
      
      if (graphData && graphData.nodes) {
        // 计算每个节点的连接数
        const connectionCount = {};
        graphData.links.forEach(link => {
          connectionCount[link.source] = (connectionCount[link.source] || 0) + 1;
          connectionCount[link.target] = (connectionCount[link.target] || 0) + 1;
        });
        
        // 转换节点格式
        this.data.nodes = graphData.nodes.map(node => ({
          id: node.id,
          name: node.label || node.id,
          type: node.type || 'ENTITY',
          val: Math.max(5, Math.min(30, (connectionCount[node.id] || 1) * 2)),
          color: this.typeColors[node.type] || '#6b7280',
          connections: connectionCount[node.id] || 0
        }));
        
        // 转换边格式
        this.data.links = graphData.links.map(link => ({
          source: link.source,
          target: link.target,
          relation: link.relation,
          color: 'rgba(99, 102, 241, 0.3)'
        }));
        
        // 保存原始数据
        this.originalData = JSON.parse(JSON.stringify(this.data));
        
        console.log('✅ 神经图谱数据加载完成:', this.data.nodes.length, '节点,', this.data.links.length, '边');
      }
    } catch (error) {
      console.error('❌ 加载数据失败:', error);
      this.createDefaultData();
    }
  }
  
  createDefaultData() {
    this.data = {
      nodes: [
        { id: 'omnia', name: 'Omnia', type: 'SYSTEM', val: 25, color: '#6366f1', connections: 4 },
        { id: 'user', name: '原点', type: 'PERSON', val: 20, color: '#f43f5e', connections: 1 },
        { id: 'assistant', name: '无限', type: 'PERSON', val: 18, color: '#8b5cf6', connections: 1 }
      ],
      links: [
        { source: 'omnia', target: 'user', color: 'rgba(244, 63, 94, 0.5)' },
        { source: 'omnia', target: 'assistant', color: 'rgba(139, 92, 246, 0.5)' }
      ]
    };
    this.originalData = JSON.parse(JSON.stringify(this.data));
  }
  
  filterData() {
    if (this.searchTerm === '' && this.filterType === 'all') {
      this.data = JSON.parse(JSON.stringify(this.originalData));
    } else {
      // 筛选节点
      const filteredNodes = this.originalData.nodes.filter(node => {
        const matchSearch = this.searchTerm === '' || 
          node.name.toLowerCase().includes(this.searchTerm) ||
          node.id.toLowerCase().includes(this.searchTerm);
        const matchType = this.filterType === 'all' || node.type === this.filterType;
        return matchSearch && matchType;
      });
      
      // 筛选边（只保留两端节点都在筛选结果中的边）
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      const filteredLinks = this.originalData.links.filter(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
      
      this.data = { nodes: filteredNodes, links: filteredLinks };
    }
    
    // 更新图谱
    if (this.graph) {
      this.graph.graphData(this.data);
    }
  }
  
  /**
   * Obsidian 风格：高亮节点及其连接
   */
  highlightNodeAndConnections(node) {
    if (!this.graph) return;
    
    // 获取连接的节点ID
    const connectedNodeIds = new Set();
    const connectedLinks = [];
    
    if (node) {
      this.data.links.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        
        if (sourceId === node.id) {
          connectedNodeIds.add(targetId);
          connectedLinks.push({ source: sourceId, target: targetId });
        } else if (targetId === node.id) {
          connectedNodeIds.add(sourceId);
          connectedLinks.push({ source: sourceId, target: targetId });
        }
      });
      connectedNodeIds.add(node.id); // 包含自己
    }
    
    // 更新节点颜色和大小
    this.graph
      .nodeColor(n => {
        if (!node) return n.color; // 没有悬停时恢复原色
        if (n.id === node.id) return n.color; // 悬停节点保持原色
        if (connectedNodeIds.has(n.id)) return n.color; // 连接节点保持原色
        return 'rgba(107, 114, 128, 0.2)'; // 其他节点变暗
      })
      .nodeVal(n => {
        if (!node) return n.val; // 没有悬停时恢复原大小
        if (n.id === node.id) return n.val * 1.5; // 悬停节点放大
        if (connectedNodeIds.has(n.id)) return n.val * 1.2; // 连接节点稍大
        return n.val * 0.8; // 其他节点缩小
      })
      .linkColor(l => {
        if (!node) return 'rgba(99, 102, 241, 0.3)'; // 没有悬停时恢复原色
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        
        // 检查是否是悬停节点的连接
        const isHoveredLink = connectedLinks.some(
          cl => (cl.source === sourceId && cl.target === targetId) ||
                (cl.source === targetId && cl.target === sourceId)
        );
        
        if (isHoveredLink) return 'rgba(99, 102, 241, 0.8)'; // 高亮连接
        return 'rgba(107, 114, 128, 0.1)'; // 其他连接变暗
      })
      .linkWidth(l => {
        if (!node) return 1;
        const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
        const targetId = typeof l.target === 'object' ? l.target.id : l.target;
        
        const isHoveredLink = connectedLinks.some(
          cl => (cl.source === sourceId && cl.target === targetId) ||
                (cl.source === targetId && cl.target === sourceId)
        );
        
        return isHoveredLink ? 3 : 0.5;
      });
  }
  
  createGraph() {
    // 清空容器（保留控制面板）
    const panel = this.container.querySelector('.graph-control-panel');
    this.container.innerHTML = '';
    if (panel) this.container.appendChild(panel);
    
    // 创建图谱
    this.graph = ForceGraph3D()(this.container)
      .graphData(this.data)
      .nodeLabel(node => `${node.name} (${node.type})`)
      .nodeColor(node => node.color)
      .nodeVal(node => node.val)
      .nodeOpacity(0.9)
      .linkColor(link => link.color)
      .linkOpacity(0.4)
      .linkWidth(1)
      .backgroundColor('#0a0e27')
      .width(this.container.clientWidth)
      .height(this.container.clientHeight)
      .enableNodeDrag(true)
      .enableNavigationControls(true)
      .enablePointerInteraction(true)
      .onNodeClick(node => this.onNodeClick(node))
      .onNodeHover(node => {
        this.container.style.cursor = node ? 'pointer' : 'default';
        this.highlightNodeAndConnections(node);
        this.hoveredNode = node;
      });
    
    // 设置力导向参数
    this.graph
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .cooldownTicks(100);
    
    // 自动旋转
    this.autoRotate();
    
    // 响应窗口大小变化
    window.addEventListener('resize', () => {
      if (this.graph) {
        this.graph
          .width(this.container.clientWidth)
          .height(this.container.clientHeight);
      }
    });
  }
  
  onNodeClick(node) {
    // 显示节点详情
    const detailPanel = this.container.querySelector('#node-detail-panel');
    if (detailPanel) {
      this.container.querySelector('#node-name').textContent = node.name;
      this.container.querySelector('#node-type').textContent = node.type;
      this.container.querySelector('#node-connections').textContent = node.connections;
      detailPanel.classList.remove('hidden');
    }
    
    // 聚焦到节点
    const distance = 40;
    const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
    
    this.graph.cameraPosition(
      { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
      node,
      2000
    );
  }
  
  autoRotate() {
    let angle = 0;
    let lastInteraction = Date.now();
    
    this.container.addEventListener('mousedown', () => {
      lastInteraction = Date.now();
    });
    
    this.container.addEventListener('wheel', () => {
      lastInteraction = Date.now();
    });
    
    const rotate = () => {
      if (!this.graph) return;
      
      if (Date.now() - lastInteraction > 2000) {
        const camera = this.graph.camera();
        if (camera) {
          angle += 0.002;
          camera.position.x = 300 * Math.sin(angle);
          camera.position.z = 300 * Math.cos(angle);
          camera.lookAt(0, 0, 0);
        }
      }
      
      requestAnimationFrame(rotate);
    };
    
    rotate();
  }
  
  destroy() {
    if (this.graph) {
      this.graph._destructor();
      this.graph = null;
    }
  }
}

// 导出
export { NeuralGraphImproved };
