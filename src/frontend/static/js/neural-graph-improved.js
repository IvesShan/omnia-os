/**
 * Omnia 神经图谱 - Obsidian 风格升级版
 * 添加力导向布局、悬停高亮、节点拖拽、发光效果
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
      'ENTITY': '#ec4899',
      'SYSTEM': '#3b82f6'
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
          <div class="detail-row">
            <span class="detail-label">来源:</span>
            <span id="node-source"></span>
          </div>
        </div>
      </div>
      <div class="graph-hint" style="margin-top: 8px; font-size: 11px; color: #6b7280;">
        💡 悬停高亮 | 拖拽移动 | 点击详情
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
      const graphResponse = await fetch('/api/graph');
      const graphData = await graphResponse.json();
      
      if (graphData && graphData.nodes) {
        const connectionCount = {};
        graphData.links.forEach(link => {
          connectionCount[link.source] = (connectionCount[link.source] || 0) + 1;
          connectionCount[link.target] = (connectionCount[link.target] || 0) + 1;
        });
        
        this.data.nodes = graphData.nodes.map(node => ({
          id: node.id,
          name: node.label || node.id,
          type: node.type || 'ENTITY',
          val: Math.max(5, Math.min(30, (connectionCount[node.id] || 1) * 2 + 5)),
          color: this.typeColors[node.type] || '#6b7280',
          connections: connectionCount[node.id] || 0,
          source: node.source || 'unknown'
        }));
        
        this.data.links = graphData.links.map(link => ({
          source: link.source,
          target: link.target,
          relation: link.relation,
          color: 'rgba(99, 102, 241, 0.25)'
        }));
        
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
        { id: 'omnia', name: 'Omnia', type: 'SYSTEM', val: 25, color: '#6366f1', connections: 4, source: 'system' },
        { id: 'user', name: '原点', type: 'PERSON', val: 20, color: '#f43f5e', connections: 2, source: 'system' },
        { id: 'assistant', name: '无限', type: 'PERSON', val: 18, color: '#8b5cf6', connections: 2, source: 'system' },
        { id: 'memory', name: 'Memory Palace', type: 'CONCEPT', val: 15, color: '#f59e0b', connections: 1, source: 'system' }
      ],
      links: [
        { source: 'omnia', target: 'user', color: 'rgba(244, 63, 94, 0.4)' },
        { source: 'omnia', target: 'assistant', color: 'rgba(139, 92, 246, 0.4)' },
        { source: 'omnia', target: 'memory', color: 'rgba(245, 158, 11, 0.4)' },
        { source: 'user', target: 'assistant', color: 'rgba(99, 102, 241, 0.3)' }
      ]
    };
    this.originalData = JSON.parse(JSON.stringify(this.data));
  }
  
  filterData() {
    if (this.searchTerm === '' && this.filterType === 'all') {
      this.data = JSON.parse(JSON.stringify(this.originalData));
    } else {
      const filteredNodes = this.originalData.nodes.filter(node => {
        const matchSearch = this.searchTerm === '' || 
          node.name.toLowerCase().includes(this.searchTerm) ||
          node.id.toLowerCase().includes(this.searchTerm);
        const matchType = this.filterType === 'all' || node.type === this.filterType;
        return matchSearch && matchType;
      });
      
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      const filteredLinks = this.originalData.links.filter(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
      
      this.data = { nodes: filteredNodes, links: filteredLinks };
    }
    
    if (this.graph) {
      this.graph.graphData(this.data);
    }
  }
  
  // 获取节点的所有连接节点
  getConnectedNodes(node) {
    const connected = new Set();
    this.data.links.forEach(link => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      
      if (sourceId === node.id) connected.add(targetId);
      if (targetId === node.id) connected.add(sourceId);
    });
    return connected;
  }
  
  createGraph() {
    const panel = this.container.querySelector('.graph-control-panel');
    this.container.innerHTML = '';
    if (panel) this.container.appendChild(panel);
    
    // 创建图谱 - Obsidian 风格
    this.graph = ForceGraph3D()(this.container)
      .graphData(this.data)
      // 节点配置 - 发光效果
      .nodeThreeObject(node => {
        const isConnected = this.hoveredNode && (
          this.hoveredNode.id === node.id || 
          this.getConnectedNodes(this.hoveredNode).has(node.id)
        );
        const isHovered = this.hoveredNode && this.hoveredNode.id === node.id;
        
        // 创建节点组
        const nodeGroup = new THREE.Group();
        
        // 核心球体
        const coreGeometry = new THREE.SphereGeometry(node.val * 0.15, 16, 16);
        const coreMaterial = new THREE.MeshBasicMaterial({
          color: node.color,
          transparent: true,
          opacity: isConnected ? 1 : (this.hoveredNode ? 0.2 : 0.85)
        });
        const core = new THREE.Mesh(coreGeometry, coreMaterial);
        nodeGroup.add(core);
        
        // 光晕效果
        const glowSize = isHovered ? node.val * 0.4 : node.val * 0.25;
        const glowGeometry = new THREE.SphereGeometry(glowSize, 16, 16);
        const glowMaterial = new THREE.MeshBasicMaterial({
          color: node.color,
          transparent: true,
          opacity: isHovered ? 0.6 : 0.2,
          side: THREE.BackSide
        });
        const glow = new THREE.Mesh(glowGeometry, glowMaterial);
        nodeGroup.add(glow);
        
        // 悬停时添加外圈
        if (isHovered) {
          const ringGeometry = new THREE.RingGeometry(node.val * 0.35, node.val * 0.4, 32);
          const ringMaterial = new THREE.MeshBasicMaterial({
            color: node.color,
            transparent: true,
            opacity: 0.8,
            side: THREE.DoubleSide
          });
          const ring = new THREE.Mesh(ringGeometry, ringMaterial);
          ring.rotation.x = Math.PI / 2;
          nodeGroup.add(ring);
        }
        
        return nodeGroup;
      })
      .nodeLabel(node => `<div style="padding: 8px; background: rgba(0,0,0,0.8); border-radius: 8px;">
        <strong>${node.name}</strong><br>
        <span style="color: #9ca3af;">${node.type}</span>
      </div>`)
      // 连接线配置 - 悬停高亮
      .linkColor(link => {
        if (!this.hoveredNode) return 'rgba(99, 102, 241, 0.25)';
        
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        
        if (sourceId === this.hoveredNode.id || targetId === this.hoveredNode.id) {
          return 'rgba(99, 102, 241, 0.9)';
        }
        return 'rgba(99, 102, 241, 0.08)';
      })
      .linkWidth(link => {
        if (!this.hoveredNode) return 1;
        
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        
        if (sourceId === this.hoveredNode.id || targetId === this.hoveredNode.id) {
          return 3;
        }
        return 0.5;
      })
      .linkOpacity(0.8)
      .backgroundColor('#0a0e27')
      .width(this.container.clientWidth)
      .height(this.container.clientHeight)
      .enableNodeDrag(true)
      .enableNavigationControls(true)
      .enablePointerInteraction(true)
      // 悬停事件 - Obsidian 风格高亮
      .onNodeHover(node => {
        this.hoveredNode = node;
        this.container.style.cursor = node ? 'pointer' : 'default';
        
        // 刷新图谱以更新视觉效果
        if (this.graph) {
          this.graph
            .nodeColor(this.data.nodes.map(n => n.color))
            .linkColor(this.data.links.map(l => l.color));
        }
      })
      // 点击事件 - 显示详情
      .onNodeClick(node => this.onNodeClick(node));
    
    // 设置力导向参数 - Obsidian 风格自然分布
    this.graph
      .d3AlphaDecay(0.005)      // 更慢的冷却，更自然的动画
      .d3VelocityDecay(0.2)      // 更低的阻尼，更流畅的运动
      .cooldownTicks(300)        // 更长的动画时间
      .linkDistance(80)          // 连接距离
      .nodeResolution(16);       // 更平滑的节点
    
    // 自动旋转（空闲时）
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
    const detailPanel = this.container.querySelector('#node-detail-panel');
    if (detailPanel) {
      this.container.querySelector('#node-name').textContent = node.name;
      this.container.querySelector('#node-type').textContent = node.type;
      this.container.querySelector('#node-connections').textContent = node.connections;
      this.container.querySelector('#node-source').textContent = node.source || 'unknown';
      detailPanel.classList.remove('hidden');
    }
    
    // 聚焦到节点
    const distance = 60;
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
    
    this.graph.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node,
      1500
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
      
      if (Date.now() - lastInteraction > 3000) {
        const camera = this.graph.camera();
        if (camera) {
          angle += 0.001;
          camera.position.x = 400 * Math.sin(angle);
          camera.position.z = 400 * Math.cos(angle);
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
