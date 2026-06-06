/**
 * 神经图谱可视化 - Canvas 2D Obsidian 风格
 * 
 * 设计参考：Obsidian Graph View
 * - 零外部依赖
 * - Canvas 2D 批量渲染
 * - 力导向物理模拟（D3-force 风格）
 * - 无限画布 + 缩放导航
 * - 悬停高亮 + 拖拽交互
 */

const GraphViz = {
  canvas: null,
  ctx: null,
  nodes: [],
  links: [],
  nodeMap: {},
  
  // 视图状态
  transform: { x: 0, y: 0, scale: 1 },
  hoveredNode: null,
  selectedNode: null,
  draggedNode: null,
  
  // 交互状态
  isDragging: false,
  isDraggedNode: false,  // 是否真的拖拽了节点（移动超过5px）
  dragStartPos: { x: 0, y: 0 },
  lastMouse: { x: 0, y: 0 },
  
  // 力导向参数（参考 D3-force）
  physics: {
    repulsion: -500,           // 斥力强度（负值，越大斥力越强）
    springStrength: 0.005,     // 弹簧强度（连接节点间的力）
    idealLinkLength: 120,      // 理想链接长度
    damping: 0.85,             // 阻尼（速度衰减）
    centerForce: 0,            // 向心力（设为0，不拉向中心）
    maxVelocity: 20,           // 最大速度
    coolingFactor: 0.995,      // 冷却因子（慢慢降温）
    minAlpha: 0.001,           // 最小活跃度
    
    // 收敛检测参数
    convergenceThreshold: 0.05, // 速度阈值
    convergenceFrames: 60,     // 连续帧数
  },
  
  // 当前活跃度（用于控制模拟）
  alpha: 1.0,
  
  // 收敛检测状态
  convergence: {
    frameCount: 0,
    isConverged: false,
    history: []
  },
  
  // 空间分区网格（用于优化斥力计算）
  grid: {
    cellSize: 150,
    cells: {}
  },
  
  // 颜色方案
  colors: {
    bg: '#0f1117',
    grid: 'rgba(100, 116, 139, 0.08)',
    nodeDefault: '#64748b',
    nodeHighlight: '#ff8a00',
    linkDefault: 'rgba(100, 116, 139, 0.15)',
    linkHighlight: 'rgba(255, 138, 0, 0.6)',
    particle: '#22d3ee',
    text: '#e2e8f0'
  },
  
  // 类型颜色（HSL 色轮均匀分布）
  typeColors: {
    'PERSON':   { h: 190, s: 70, l: 60 },
    'PROJECT':  { h: 270, s: 70, l: 60 },
    'FILE':     { h: 150, s: 70, l: 60 },
    'CONCEPT':  { h: 30, s: 70, l: 60 },
    'DATE':     { h: 240, s: 70, l: 60 },
    'LOCATION': { h: 330, s: 70, l: 60 },
    'ENTITY':   { h: 210, s: 70, l: 60 },
    'DEFAULT':  { h: 210, s: 10, l: 50 }
  },
  
  // 粒子系统
  particles: [],
  particleTimer: 0,
  
  // 动画循环 ID
  animationFrameId: null,
  
  // 初始化状态
  isInitialized: false,
  
  // 性能监控
  performance: {
    lastFrameTime: 0,
    frameCount: 0,
    fps: 0
  },
  
  async init() {
    if (this.isInitialized) {
      console.log("[GraphViz] 已经初始化，跳过重复初始化");
      await this.loadStats();
      await this.loadGraph();
      this.resetConvergence();
      return;
    }
    
    console.log("[GraphViz] 初始化 Canvas 2D Obsidian 风格");
    
    const container = document.getElementById('graph-canvas');
    if (!container) {
      console.error('[GraphViz] 找不到 graph-canvas');
      return;
    }
    
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'width: 100%; height: 100%;';
    container.innerHTML = '';
    container.appendChild(this.canvas);
    
    this.ctx = this.canvas.getContext('2d');
    this.resizeCanvas();
    
    this.bindEvents();
    
    try {
      await this.loadStats();
      await this.loadGraph();
      this.initPhysics();
      this.startAnimation();
      this.isInitialized = true;
      
      console.log("[GraphViz] 初始化完成，节点数:", this.nodes.length);
    } catch (error) {
      console.error("[GraphViz] 初始化错误:", error);
    }
  },
  
  resizeCanvas() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.canvas.style.width = rect.width + 'px';
    this.canvas.style.height = rect.height + 'px';
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  },
  
  bindEvents() {
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
    this.canvas.addEventListener('wheel', this.onWheel.bind(this));
    this.canvas.addEventListener('dblclick', this.onDblClick.bind(this));
    
    this.canvas.addEventListener('touchstart', this.onTouchStart.bind(this));
    this.canvas.addEventListener('touchmove', this.onTouchMove.bind(this));
    this.canvas.addEventListener('touchend', this.onTouchEnd.bind(this));
    
    window.addEventListener('resize', () => this.resizeCanvas());
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
      const response = await fetch('/api/graph', { cache: 'no-store' });
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        
        this.nodes = (data.nodes || []).map((n, i) => ({
          id: n.name || n.id,
          label: n.label || n.name,
          type: n.type || 'ENTITY',
          evidence: n.evidence || '',
          x: 0, y: 0,
          vx: 0, vy: 0,
          size: 3,
          color: this.getNodeColor(n.type)
        }));
        
        this.links = (data.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          type: e.type || 'RELATED'
        }));
        
        this.nodeMap = {};
        this.nodes.forEach(n => this.nodeMap[n.id] = n);
        
        this.calculateNodeSizes();
        
        console.log('[GraphViz] 加载图谱:', this.nodes.length, '节点,', this.links.length, '边');
      } catch (parseErr) {
        console.warn('[GraphViz] graph 非 JSON 响应，跳过');
        this.nodes = [];
        this.links = [];
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.warn('[GraphViz] 加载图谱失败:', error.message);
      }
      this.nodes = [];
      this.links = [];
    }
  },
  
  getNodeColor(type) {
    const hsl = this.typeColors[type] || this.typeColors.DEFAULT;
    return `hsl(${hsl.h}, ${hsl.s}%, ${hsl.l}%)`;
  },
  
  calculateNodeSizes() {
    const degree = {};
    this.links.forEach(l => {
      degree[l.source] = (degree[l.source] || 0) + 1;
      degree[l.target] = (degree[l.target] || 0) + 1;
    });
    
    this.nodes.forEach(n => {
      n.size = Math.max(3, Math.min(12, 3 + (degree[n.id] || 0) * 0.8));
    });
  },
  
  initPhysics() {
    // 关键：初始位置使用大面积随机分布
    // 根据节点数量动态计算散布范围
    const nodeCount = this.nodes.length;
    const spreadRadius = Math.sqrt(nodeCount) * 30; // 每个节点约 30px 间距
    
    console.log('[GraphViz] 初始散布半径:', spreadRadius, 'px');
    
    this.nodes.forEach((node, i) => {
      // 使用螺旋布局 + 随机偏移（避免所有节点从同一点出发）
      const angle = i * 2.399963; // 黄金角（弧度）
      const r = Math.sqrt(i / nodeCount) * spreadRadius;
      const offsetX = (Math.random() - 0.5) * 40;
      const offsetY = (Math.random() - 0.5) * 40;
      
      node.x = r * Math.cos(angle) + offsetX;
      node.y = r * Math.sin(angle) + offsetY;
      node.vx = 0;
      node.vy = 0;
    });
    
    // 居中视图：将 transform 设为画布中心
    const width = this.canvas.width / window.devicePixelRatio;
    const height = this.canvas.height / window.devicePixelRatio;
    this.transform.x = width / 2;
    this.transform.y = height / 2;
    this.transform.scale = 0.5; // 缩小一点，让节点都在视野内
    
    // 根据节点数量调整初始 alpha（活跃度）
    this.alpha = 1.0;
    
    // 根据节点数量调整物理参数
    if (nodeCount > 1000) {
      // 大图：需要更强的斥力，更大的间距
      this.physics.repulsion = -800;
      this.physics.idealLinkLength = 200;
      this.physics.damping = 0.88;
      this.physics.coolingFactor = 0.998;
      this.grid.cellSize = 200;
    } else if (nodeCount > 300) {
      // 中图
      this.physics.repulsion = -600;
      this.physics.idealLinkLength = 150;
      this.physics.damping = 0.86;
      this.physics.coolingFactor = 0.997;
      this.grid.cellSize = 180;
    } else {
      // 小图
      this.physics.repulsion = -400;
      this.physics.idealLinkLength = 120;
      this.physics.damping = 0.85;
      this.physics.coolingFactor = 0.995;
      this.grid.cellSize = 150;
    }
  },
  
  startAnimation() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    const animate = (timestamp) => {
      if (timestamp - this.performance.lastFrameTime >= 1000) {
        this.performance.fps = this.performance.frameCount;
        this.performance.frameCount = 0;
        this.performance.lastFrameTime = timestamp;
      }
      this.performance.frameCount++;
      
      // 检查收敛
      const isConverged = this.checkConvergence();
      
      if (!isConverged) {
        this.update();
      }
      
      // 总是渲染
      this.render();
      
      this.animationFrameId = requestAnimationFrame(animate);
    };
    animate(0);
  },
  
  checkConvergence() {
    if (this.nodes.length === 0) return true;
    
    let totalSpeed = 0;
    for (const node of this.nodes) {
      totalSpeed += Math.sqrt(node.vx * node.vx + node.vy * node.vy);
    }
    const avgVelocity = totalSpeed / this.nodes.length;
    
    this.convergence.history.push(avgVelocity);
    if (this.convergence.history.length > this.physics.convergenceFrames) {
      this.convergence.history.shift();
    }
    
    if (avgVelocity < this.physics.convergenceThreshold) {
      this.convergence.frameCount++;
      if (this.convergence.frameCount >= this.physics.convergenceFrames) {
        if (!this.convergence.isConverged) {
          this.convergence.isConverged = true;
          // 强制停止所有节点
          this.nodes.forEach(n => { n.vx = 0; n.vy = 0; });
          console.log('[GraphViz] 物理模拟已收敛，平均速度:', avgVelocity.toFixed(4));
        }
        return true;
      }
    } else {
      this.convergence.frameCount = 0;
      this.convergence.isConverged = false;
    }
    
    return false;
  },
  
  buildGrid() {
    const cellSize = this.grid.cellSize;
    this.grid.cells = {};
    
    this.nodes.forEach(node => {
      const cellX = Math.floor(node.x / cellSize);
      const cellY = Math.floor(node.y / cellSize);
      const key = `${cellX},${cellY}`;
      
      if (!this.grid.cells[key]) {
        this.grid.cells[key] = [];
      }
      this.grid.cells[key].push(node);
    });
  },
  
  getNeighborNodes(node) {
    const cellSize = this.grid.cellSize;
    const cellX = Math.floor(node.x / cellSize);
    const cellY = Math.floor(node.y / cellSize);
    const neighbors = [];
    
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const key = `${cellX + dx},${cellY + dy}`;
        if (this.grid.cells[key]) {
          neighbors.push(...this.grid.cells[key]);
        }
      }
    }
    
    return neighbors;
  },
  
  update() {
    if (this.nodes.length === 0) return;
    
    // 检查是否在拖拽节点（拖拽时不更新物理）
    if (this.draggedNode && this.isDraggedNode) {
      return;
    }
    
    // 构建空间分区网格
    this.buildGrid();
    
    // 1. 斥力（使用空间分区优化）
    this.nodes.forEach(nodeA => {
      const neighbors = this.getNeighborNodes(nodeA);
      
      neighbors.forEach(nodeB => {
        if (nodeA === nodeB) return;
        
        const dx = nodeA.x - nodeB.x;
        const dy = nodeA.y - nodeB.y;
        const distSq = dx * dx + dy * dy;
        
        // 防止距离太小导致力爆炸
        const minDist = 10;
        if (distSq < minDist * minDist) {
          // 碰撞：强制推开
          const angle = Math.atan2(dy, dx) || (Math.random() * Math.PI * 2);
          nodeA.vx += Math.cos(angle) * 2;
          nodeA.vy += Math.sin(angle) * 2;
          return;
        }
        
        // 斥力 = repulsion / distSq
        // 方向：从 nodeB 指向 nodeA（推开）
        const force = this.physics.repulsion / distSq;
        const fx = (dx / Math.sqrt(distSq)) * force;
        const fy = (dy / Math.sqrt(distSq)) * force;
        
        nodeA.vx += fx;
        nodeA.vy += fy;
      });
    });
    
    // 2. 弹簧力（连接的节点）
    this.links.forEach(link => {
      const source = this.nodeMap[link.source];
      const target = this.nodeMap[link.target];
      if (!source || !target) return;
      
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      if (dist < 1) return; // 防止除以0
      
      // 弹簧力：当距离大于理想长度时吸引，小于时排斥
      const displacement = dist - this.physics.idealLinkLength;
      const force = displacement * this.physics.springStrength;
      
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    });
    
    // 3. 向心力（如果设置了的话）
    if (this.physics.centerForce > 0) {
      this.nodes.forEach(node => {
        node.vx -= node.x * this.physics.centerForce;
        node.vy -= node.y * this.physics.centerForce;
      });
    }
    
    // 4. 更新位置（无限画布，不加边界约束）
    this.nodes.forEach(node => {
      // 限制速度
      const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      if (speed > this.physics.maxVelocity) {
        node.vx = (node.vx / speed) * this.physics.maxVelocity;
        node.vy = (node.vy / speed) * this.physics.maxVelocity;
      }
      
      // 应用阻尼
      node.vx *= this.physics.damping;
      node.vy *= this.physics.damping;
      
      // 更新位置（无限画布，没有边界限制）
      node.x += node.vx * this.alpha;
      node.y += node.vy * this.alpha;
    });
    
    // 5. 冷却
    this.alpha *= this.physics.coolingFactor;
    if (this.alpha < this.physics.minAlpha) {
      this.alpha = this.physics.minAlpha;
    }
  },
  
  render() {
    const ctx = this.ctx;
    const width = this.canvas.width / window.devicePixelRatio;
    const height = this.canvas.height / window.devicePixelRatio;
    
    // 清空画布
    ctx.fillStyle = this.colors.bg;
    ctx.fillRect(0, 0, width, height);
    
    // 绘制网格背景
    this.drawGrid(ctx, width, height);
    
    // 应用变换
    ctx.save();
    ctx.translate(this.transform.x, this.transform.y);
    ctx.scale(this.transform.scale, this.transform.scale);
    
    // 绘制连线
    this.drawLinks(ctx);
    
    // 绘制粒子
    this.drawParticles(ctx);
    
    // 绘制节点
    this.drawNodes(ctx);
    
    ctx.restore();
    
    // 绘制性能信息
    this.drawPerformanceInfo(ctx, width, height);
  },
  
  drawGrid(ctx, width, height) {
    const gridSize = 40 * this.transform.scale;
    const offsetX = this.transform.x % gridSize;
    const offsetY = this.transform.y % gridSize;
    
    ctx.strokeStyle = this.colors.grid;
    ctx.lineWidth = 0.5;
    
    for (let x = offsetX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    
    for (let y = offsetY; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  },
  
  drawLinks(ctx) {
    ctx.lineWidth = 0.8;
    
    this.links.forEach(link => {
      const source = this.nodeMap[link.source];
      const target = this.nodeMap[link.target];
      if (!source || !target) return;
      
      const isHighlighted = this.hoveredNode && 
        (source.id === this.hoveredNode.id || target.id === this.hoveredNode.id);
      
      ctx.strokeStyle = isHighlighted ? this.colors.linkHighlight : this.colors.linkDefault;
      ctx.lineWidth = isHighlighted ? 1.5 : 0.5;
      
      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();
    });
  },
  
  drawNodes(ctx) {
    this.nodes.forEach(node => {
      const isHovered = this.hoveredNode && node.id === this.hoveredNode.id;
      const isSelected = this.selectedNode && node.id === this.selectedNode.id;
      
      const size = isHovered ? node.size * 1.3 : node.size;
      
      if (isHovered || isSelected) {
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, size * 3);
        gradient.addColorStop(0, node.color.replace(')', ', 0.3)').replace('hsl', 'hsla'));
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, size * 3, 0, Math.PI * 2);
        ctx.fill();
      }
      
      ctx.fillStyle = isHovered ? this.colors.nodeHighlight : node.color;
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
      ctx.fill();
      
      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      
      if (isHovered) {
        ctx.fillStyle = this.colors.text;
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - size - 8);
      }
    });
  },
  
  drawParticles(ctx) {
    this.particleTimer++;
    if (this.particleTimer % 30 === 0 && this.hoveredNode) {
      this.addParticlesForNode(this.hoveredNode);
    }
    
    this.particles = this.particles.filter(p => {
      p.progress += 0.02;
      if (p.progress >= 1) return false;
      
      const source = this.nodeMap[p.source];
      const target = this.nodeMap[p.target];
      if (!source || !target) return false;
      
      const x = source.x + (target.x - source.x) * p.progress;
      const y = source.y + (target.y - source.y) * p.progress;
      
      ctx.fillStyle = this.colors.particle;
      ctx.globalAlpha = 1 - p.progress;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      
      return true;
    });
  },
  
  addParticlesForNode(node) {
    this.links.forEach(link => {
      if (link.source === node.id || link.target === node.id) {
        this.particles.push({
          source: link.source,
          target: link.target,
          progress: 0
        });
      }
    });
  },
  
  drawPerformanceInfo(ctx, width, height) {
    const status = this.getConvergenceStatus();
    
    ctx.fillStyle = 'rgba(100, 116, 139, 0.7)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    
    const lines = [
      `FPS: ${status.fps}`,
      `Nodes: ${this.nodes.length}`,
      `Links: ${this.links.length}`,
      `Alpha: ${this.alpha.toFixed(3)}`,
      `Velocity: ${status.currentVelocity.toFixed(3)} px/f`,
      `Converged: ${status.isConverged ? '✓' : '✗'} (${status.frameCount}/${status.requiredFrames})`,
      `Scale: ${this.transform.scale.toFixed(2)}`
    ];
    
    lines.forEach((line, i) => {
      ctx.fillText(line, width - 10, height - 10 - (lines.length - 1 - i) * 14);
    });
  },
  
  getConvergenceStatus() {
    const avgVelocity = this.convergence.history.length > 0 
      ? this.convergence.history[this.convergence.history.length - 1] 
      : 0;
    
    return {
      isConverged: this.convergence.isConverged,
      frameCount: this.convergence.frameCount,
      requiredFrames: this.physics.convergenceFrames,
      currentVelocity: avgVelocity,
      threshold: this.physics.convergenceThreshold,
      fps: this.performance.fps
    };
  },
  
  // 鼠标事件
  onMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - this.transform.x) / this.transform.scale;
    const y = (e.clientY - rect.top - this.transform.y) / this.transform.scale;
    
    const clickedNode = this.findNodeAt(x, y);
    
    if (clickedNode) {
      this.draggedNode = clickedNode;
      this.isDraggedNode = false;
      this.isDragging = true;
      this.selectNode(clickedNode);
    } else {
      this.draggedNode = null;
      this.isDraggedNode = false;
      this.isDragging = true;
      this.selectedNode = null;
    }
    
    this.lastMouse.x = e.clientX;
    this.lastMouse.y = e.clientY;
    this.dragStartPos = { x: e.clientX, y: e.clientY };
  },
  
  onMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - this.transform.x) / this.transform.scale;
    const y = (e.clientY - rect.top - this.transform.y) / this.transform.scale;
    
    // 悬停检测
    const hoveredNode = this.findNodeAt(x, y);
    if (hoveredNode !== this.hoveredNode) {
      this.hoveredNode = hoveredNode;
      this.canvas.style.cursor = hoveredNode ? 'pointer' : 'default';
    }
    
    // 拖拽
    if (this.isDragging) {
      const dx = e.clientX - this.dragStartPos.x;
      const dy = e.clientY - this.dragStartPos.y;
      const dragDist = Math.sqrt(dx * dx + dy * dy);
      
      if (this.draggedNode && dragDist > 5) {
        // 拖拽节点
        this.isDraggedNode = true;
        this.draggedNode.x = x;
        this.draggedNode.y = y;
        this.draggedNode.vx = 0;
        this.draggedNode.vy = 0;
        this.resetConvergence();
      } else if (!this.draggedNode) {
        // 拖拽视图（平移）
        this.transform.x += e.clientX - this.lastMouse.x;
        this.transform.y += e.clientY - this.lastMouse.y;
      }
    }
    
    this.lastMouse.x = e.clientX;
    this.lastMouse.y = e.clientY;
  },
  
  onMouseUp(e) {
    this.isDragging = false;
    this.draggedNode = null;
    this.isDraggedNode = false;
  },
  
  onWheel(e) {
    e.preventDefault();
    
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.05, Math.min(5, this.transform.scale * delta));
    
    // 以鼠标位置为中心缩放
    const scaleRatio = newScale / this.transform.scale;
    this.transform.x = mouseX - (mouseX - this.transform.x) * scaleRatio;
    this.transform.y = mouseY - (mouseY - this.transform.y) * scaleRatio;
    this.transform.scale = newScale;
  },
  
  onDblClick(e) {
    // 双击重置视图到所有节点的中心
    this.fitView();
  },
  
  fitView() {
    if (this.nodes.length === 0) return;
    
    // 计算所有节点的包围盒
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    this.nodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    });
    
    const width = this.canvas.width / window.devicePixelRatio;
    const height = this.canvas.height / window.devicePixelRatio;
    const padding = 50;
    
    const graphWidth = maxX - minX || 1;
    const graphHeight = maxY - minY || 1;
    
    const scaleX = (width - padding * 2) / graphWidth;
    const scaleY = (height - padding * 2) / graphHeight;
    const scale = Math.min(scaleX, scaleY, 2); // 最大缩放 2
    
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    
    this.transform.scale = scale;
    this.transform.x = width / 2 - centerX * scale;
    this.transform.y = height / 2 - centerY * scale;
  },
  
  onTouchStart(e) {
    if (e.touches.length === 1) {
      e.preventDefault();
      const touch = e.touches[0];
      this.onMouseDown({ clientX: touch.clientX, clientY: touch.clientY });
    }
  },
  
  onTouchMove(e) {
    if (e.touches.length === 1) {
      e.preventDefault();
      const touch = e.touches[0];
      this.onMouseMove({ clientX: touch.clientX, clientY: touch.clientY });
    }
  },
  
  onTouchEnd(e) {
    this.onMouseUp(e);
  },
  
  findNodeAt(x, y) {
    for (let i = this.nodes.length - 1; i >= 0; i--) {
      const node = this.nodes[i];
      const dx = node.x - x;
      const dy = node.y - y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      if (dist < node.size * 2 / this.transform.scale) {
        return node;
      }
    }
    return null;
  },
  
  selectNode(node) {
    this.selectedNode = node;
    this.showNodeDetails(node);
    this.addParticlesForNode(node);
  },
  
  resetConvergence() {
    this.convergence.frameCount = 0;
    this.convergence.isConverged = false;
    this.convergence.history = [];
    this.alpha = Math.max(this.alpha, 0.3);
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
        background: rgba(15, 17, 23, 0.95);
        border: 1px solid rgba(100, 116, 139, 0.3);
        border-radius: 12px;
        padding: 20px;
        min-width: 280px;
        max-width: 350px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
        z-index: 1000;
        box-shadow: 0 0 30px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
      `;
      document.body.appendChild(panel);
    }
    
    const connections = this.links.filter(
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
    
    setTimeout(() => {
      if (panel.parentElement) panel.remove();
    }, 5000);
  },
  
  destroy() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    this.isInitialized = false;
    this.nodes = [];
    this.links = [];
    this.particles = [];
    
    console.log('[GraphViz] 资源已清理');
  }
};

if (typeof window !== 'undefined') {
  window.GraphViz = GraphViz;
}
