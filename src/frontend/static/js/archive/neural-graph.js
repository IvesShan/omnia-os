/**
 * Omnia 神经图谱 - 3D Force Graph
 * 使用 3d-force-graph 库实现真正的力导向图
 */

class NeuralGraphForce {
  constructor(container) {
    this.container = container;
    this.graph = null;
    this.data = {
      nodes: [],
      links: []
    };
    
    this.init();
  }
  
  async init() {
    // 检查库是否已加载
    if (typeof ForceGraph3D === 'undefined') {
      this.container.innerHTML = '<p class="text-red-400 text-center p-8">❌ 3D Force Graph 库未加载，请刷新页面</p>';
      return;
    }
    
    // 加载记忆数据
    await this.loadMemoryData();
    
    // 创建图谱
    this.createGraph();
  }
  
  async loadMemoryData() {
    try {
      // 加载记忆统计
      const statsResponse = await fetch('/api/memory/stats');
      const stats = await statsResponse.json();
      
      // 加载技能列表
      const skillsResponse = await fetch('/api/skills');
      const skills = await skillsResponse.json();
      
      // 创建中心节点 - Omnia
      this.data.nodes.push({
        id: 'omnia',
        name: 'Omnia',
        group: 'system',
        val: 25,
        color: '#6366f1'
      });
      
      // 创建记忆节点
      const memoryTypes = [
        { key: 'facts', label: '事实记忆', count: stats.facts || 0, color: '#8b5cf6' },
        { key: 'relations', label: '关系记忆', count: stats.relations || 0, color: '#ec4899' },
        { key: 'habits', label: '习惯记忆', count: stats.habits || 0, color: '#f59e0b' },
        { key: 'timeline', label: '时间线', count: stats.timeline || 0, color: '#10b981' }
      ];
      
      memoryTypes.forEach(type => {
        this.data.nodes.push({
          id: type.key,
          name: type.label,
          group: 'memory',
          val: Math.max(8, type.count / 50),
          color: type.color,
          count: type.count
        });
        
        this.data.links.push({
          source: 'omnia',
          target: type.key,
          color: type.color
        });
      });
      
      // 创建技能节点
      if (skills && Array.isArray(skills)) {
        skills.forEach((skill, index) => {
          const skillId = `skill_${index}`;
          this.data.nodes.push({
            id: skillId,
            name: skill.name || `技能 ${index + 1}`,
            group: 'skill',
            val: 10,
            color: '#06b6d4'
          });
          
          this.data.links.push({
            source: 'omnia',
            target: skillId,
            color: '#06b6d4'
          });
        });
      }
      
      // 创建用户节点
      this.data.nodes.push({
        id: 'user',
        name: '原点',
        group: 'user',
        val: 20,
        color: '#f43f5e'
      });
      
      this.data.links.push({
        source: 'omnia',
        target: 'user',
        color: '#f43f5e'
      });
      
      // 创建助手节点
      this.data.nodes.push({
        id: 'assistant',
        name: '无限',
        group: 'assistant',
        val: 18,
        color: '#8b5cf6'
      });
      
      this.data.links.push({
        source: 'omnia',
        target: 'assistant',
        color: '#8b5cf6'
      });
      
      console.log('✅ 记忆数据加载完成:', this.data);
      
    } catch (error) {
      console.error('❌ 加载数据失败:', error);
      
      // 使用默认数据
      this.data = {
        nodes: [
          { id: 'omnia', name: 'Omnia', group: 'system', val: 25, color: '#6366f1' },
          { id: 'user', name: '原点', group: 'user', val: 20, color: '#f43f5e' },
          { id: 'assistant', name: '无限', group: 'assistant', val: 18, color: '#8b5cf6' },
          { id: 'facts', name: '事实记忆', group: 'memory', val: 10, color: '#8b5cf6' },
          { id: 'relations', name: '关系记忆', group: 'memory', val: 10, color: '#ec4899' }
        ],
        links: [
          { source: 'omnia', target: 'user', color: '#f43f5e' },
          { source: 'omnia', target: 'assistant', color: '#8b5cf6' },
          { source: 'omnia', target: 'facts', color: '#8b5cf6' },
          { source: 'omnia', target: 'relations', color: '#ec4899' }
        ]
      };
    }
  }
  
  createGraph() {
    // 清空容器
    this.container.innerHTML = '';
    
    // 创建图谱
    this.graph = ForceGraph3D()(this.container)
      .graphData(this.data)
      .nodeLabel(node => `${node.name}${node.count ? ` (${node.count})` : ''}`)
      .nodeColor(node => node.color)
      .nodeVal(node => node.val)
      .nodeOpacity(0.9)
      .linkColor(link => link.color)
      .linkOpacity(0.6)
      .linkWidth(2)
      .backgroundColor('#0a0e27')
      .width(this.container.clientWidth)
      .height(this.container.clientHeight)
      .enableNodeDrag(true)
      .enableNavigationControls(true)
      .enablePointerInteraction(true)
      .onNodeClick(node => {
        // 点击节点时聚焦
        const distance = 40;
        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
        
        this.graph.cameraPosition(
          { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
          node,
          2000
        );
      })
      .onNodeHover(node => {
        // 悬停时改变鼠标样式
        this.container.style.cursor = node ? 'pointer' : 'default';
      });
    
    // 设置力导向参数
    this.graph
      .d3AlphaDecay(0.02)
      .d3VelocityDecay(0.3)
      .cooldownTicks(100)
      .onEngineStop(() => {
        console.log('✅ 力导向布局完成');
      });
    
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
  
  autoRotate() {
    let angle = 0;
    let lastInteraction = Date.now();
    
    // 监听用户交互
    this.container.addEventListener('mousedown', () => {
      lastInteraction = Date.now();
    });
    
    this.container.addEventListener('wheel', () => {
      lastInteraction = Date.now();
    });
    
    const rotate = () => {
      if (!this.graph) return;
      
      // 2秒无操作后恢复旋转
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
export { NeuralGraphForce };
