/**
 * 神经图谱可视化 - Canvas 2D Obsidian 风格
 * 
 * 设计参考：Obsidian Graph View
 * - 零外部依赖
 * - Canvas 2D 批量渲染
 * - 力导向物理模拟（优化版：使用网格空间分区）
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
  lastMouse: { x: 0, y: 0 },
  
  // 力导向参数（优化版）
  physics: {
    repulsion: -200,           // 斥力强度
    springStrength: 0.05,      // 弹簧强度
    idealLinkLength: 150,      // 理想链接长度
    damping: 0.85,             // 阻尼（降低，让节点更快稳定）
    centerForce: 0.02,         // 向心力
    maxVelocity: 15,           // 最大速度
    coolingFactor: 0.99,       // 冷却因子
    minAlpha: 0.01,            // 最小活跃度
    
    // 收敛检测参数
    convergenceThreshold: 1.0, // 速度阈值（像素/帧）
    convergenceFrames: 30      // 连续帧数（降低，更快收敛）
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
    cellSize: 100,    // 网格单元大小
    cells: {}         // 网格单元字典
  },
  
  // 颜色方案
  colors: {
    bg: '#0f1117',
    grid: 'rgba(100, 116, 139, 0.08)',
    nodeDefault: '#64748b',
    nodeHighlight: '#ff8a00',
    linkDefault: 'rgba(100, 116, 139, 0.2)',
    linkHighlight: 'rgba(255, 138, 0, 0.6)',
    particle: '#22d3ee',
    text: '#e2e8f0'
  },
  
  // 类型颜色（HSL 色轮均匀分布）
  typeColors: {
    'PERSON':   { h: 190, s: 70, l: 60 },  // 青色
    'PROJECT':  { h: 270, s: 70, l: 60 },  // 紫色
    'FILE':     { h: 150, s: 70, l: 60 },  // 绿色
    'CONCEPT':  { h: 30, s: 70, l: 60 },   // 橙色
    'DATE':     { h: 240, s: 70, l: 60 },  // 靛蓝
    'LOCATION': { h: 330, s: 70, l: 60 },  // 粉色
    'ENTITY':   { h: 210, s: 70, l: 60 },  // 蓝色
    'DEFAULT':  { h: 210, s: 10, l: 50 }   // 灰色
  },
  
  // 粒子系统
  particles: [],
  particleTimer: 0,
  
  // 动画循环 ID（用于停止动画）
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
    // 防止重复初始化
    if (this.isInitialized) {
      console.log("[GraphViz] 已经初始化，跳过重复初始化");
      // 只刷新数据，不重新初始化
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
    
    // 创建 canvas 元素
    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'width: 100%; height: 100%;';
    container.innerHTML = '';
    container.appendChild(this.canvas);
    
    this.ctx = this.canvas.getContext('2d');
    this.resizeCanvas();
    
    // 绑定事件
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
    // 鼠标事件
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
    this.canvas.addEventListener('wheel', this.onWheel.bind(this));
    this.canvas.addEventListener('dblclick', this.onDblClick.bind(this));
    
    // 触摸事件
    this.canvas.addEventListener('touchstart', this.onTouchStart.bind(this));
    this.canvas.addEventListener('touchmove', this.onTouchMove.bind(this));
    this.canvas.addEventListener('touchend', this.onTouchEnd.bind(this));
    
    // 窗口调整
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
      const response = await fetch('/api/graph?limit=500', { cache: 'no-store' });
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        
        // 构建节点和边
        this.nodes = (data.nodes || []).map((n, i) => ({
          id: n.name || n.id,
          label: n.label || n.name,
          type: n.type || 'ENTITY',
          evidence: n.evidence || '',
          x: 0,
          y: 0,
          vx: 0,
          vy: 0,
          size: 3,
          color: this.getNodeColor(n.type)
        }));
        
        this.links = (data.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          type: e.type || 'RELATED'
        }));
        
        // 构建节点映射
        this.nodeMap = {};
        this.nodes.forEach(n => this.nodeMap[n.id] = n);
        
        // 计算节点大小（基于连接度）
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
    // 初始位置：圆形分布
    const centerX = this.canvas.width / (2 * window.devicePixelRatio);
    const centerY = this.canvas.height / (2 * window.devicePixelRatio);
    const radius = Math.min(centerX, centerY) * 0.6;
    
    this.nodes.forEach((node, i) => {
      const angle = (i / this.nodes.length) * Math.PI * 2;
      node.x = centerX + Math.cos(angle) * radius * (0.5 + Math.random() * 0.5);
      node.y = centerY + Math.sin(angle) * radius * (0.5 + Math.random() * 0.5);
      node.vx = 0;
      node.vy = 0;
    });
    
    // 居中视图
    this.transform.x = 0;
    this.transform.y = 0;
    this.transform.scale = 1;
  },
  
  startAnimation() {
    // 先停止之前的动画循环
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    const animate = (timestamp) => {
      // 计算 FPS
      if (timestamp - this.performance.lastFrameTime >= 1000) {
        this.performance.fps = this.performance.frameCount;
        this.performance.frameCount = 0;
        this.performance.lastFrameTime = timestamp;
      }
      this.performance.frameCount++;
      
      // 检查是否真正收敛
      const isConverged = this.checkConvergence();
      
      if (!isConverged) {
        this.update();
        this.render();
      } else {
        // 只渲染，不更新物理
        this.render();
      }
      
      this.animationFrameId = requestAnimationFrame(animate);
    };
    animate(0);
  },
  
  /**
   * 检查是否真正收敛
   */
  checkConvergence() {
    if (this.nodes.length === 0) return true;
    
    // 计算平均速度
    let totalSpeed = 0;
    for (const node of this.nodes) {
      const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      totalSpeed += speed;
    }
    const avgVelocity = totalSpeed / this.nodes.length;
    
    // 记录历史
    this.convergence.history.push(avgVelocity);
    if (this.convergence.history.length > this.physics.convergenceFrames) {
      this.convergence.history.shift();
    }
    
    // 检查是否连续 N 帧低于阈值
    if (avgVelocity < this.physics.convergenceThreshold) {
      this.convergence.frameCount++;
      if (this.convergence.frameCount >= this.physics.convergenceFrames) {
        if (!this.convergence.isConverged) {
          this.convergence.isConverged = true;
          console.log('[GraphViz] 物理模拟已收敛，平均速度:', avgVelocity.toFixed(3), 'px/帧');
        }
        return true;
      }
    } else {
      this.convergence.frameCount = 0;
      this.convergence.isConverged = false;
    }
    
    return false;
  },
  
  /**
   * 获取收敛状态
   */
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
  
  /**
   * 构建空间分区网格（优化斥力计算）
   */
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
  
  /**
   * 获取相邻网格单元的节点
   */
  getNeighborNodes(node) {
    const cellSize = this.grid.cellSize;
    const cellX = Math.floor(node.x / cellSize);
    const cellY = Math.floor(node.y / cellSize);
    const neighbors = [];
    
    // 检查 3x3 的相邻网格
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
    
    const centerX = this.canvas.width / (2 * window.devicePixelRatio);
    const centerY = this.canvas.height / (2 * window.devicePixelRatio);
    
    // 构建空间分区网格
    this.buildGrid();
    
    // 1. 斥力（使用空间分区优化）
    this.nodes.forEach(nodeA => {
      const neighbors = this.getNeighborNodes(nodeA);
      
      neighbors.forEach(nodeB => {
        if (nodeA === nodeB) return;
        
        const dx = nodeB.x - nodeA.x;
        const dy = nodeB.y - nodeA.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        
        // 只计算近距离的斥力（优化性能）
        if (dist > this.grid.cellSize * 2) return;
        
        const force = this.physics.repulsion / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        
        nodeA.vx -= fx;
        nodeA.vy -= fy;
      });
    });
    
    // 2. 弹簧力（连接的节点）
    this.links.forEach(link => {
      const source = this.nodeMap[link.source];
      const target = this.nodeMap[link.target];
      if (!source || !target) return;
      
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      
      const displacement = dist - this.physics.idealLinkLength;
      const force = displacement * this.physics.springStrength;
      
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    });
    
    // 3. 向心力（防止节点飘散）
    this.nodes.forEach(node => {
      node.vx += (centerX - node.x) * this.physics.centerForce;
      node.vy += (centerY - node.y) * this.physics.centerForce;
    });
    
    // 4. 更新位置
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
      
      // 更新位置
      node.x += node.vx;
      node.y += node.vy;
    });
    
    // 5. 冷却
    this.alpha *= this.physics.coolingFactor;
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
    
    // 绘制性能信息（调试用）
    this.drawPerformanceInfo(ctx, width, height);
  },
  
  drawGrid(ctx, width, height) {
    const gridSize = 40 * this.transform.scale;
    const offsetX = this.transform.x % gridSize;
    const offsetY = this.transform.y % gridSize;
    
    ctx.strokeStyle = this.colors.grid;
    ctx.lineWidth = 0.5;
    
    // 垂直线
    for (let x = offsetX; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    
    // 水平线
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
      
      // 高亮判断
      const isHighlighted = this.hoveredNode && 
        (source.id === this.hoveredNode.id || target.id === this.hoveredNode.id);
      
      ctx.strokeStyle = isHighlighted ? this.colors.linkHighlight : this.colors.linkDefault;
      ctx.lineWidth = isHighlighted ? 1.5 : 0.8;
      
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
      
      // 外发光
      if (isHovered || isSelected) {
        const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, size * 3);
        gradient.addColorStop(0, node.color.replace(')', ', 0.3)').replace('hsl', 'hsla'));
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, size * 3, 0, Math.PI * 2);
        ctx.fill();
      }
      
      // 节点主体
      ctx.fillStyle = isHovered ? this.colors.nodeHighlight : node.color;
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
      ctx.fill();
      
      // 边框（选中状态）
      if (isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      
      // 标签（悬停时显示）
      if (isHovered) {
        ctx.fillStyle = this.colors.text;
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - size - 8);
      }
    });
  },
  
  drawParticles(ctx) {
    // 每 30 帧添加新粒子
    this.particleTimer++;
    if (this.particleTimer % 30 === 0 && this.hoveredNode) {
      this.addParticlesForNode(this.hoveredNode);
    }
    
    // 更新和绘制粒子
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
  
  /**
   * 绘制性能信息（调试用）
   */
  drawPerformanceInfo(ctx, width, height) {
    const status = this.getConvergenceStatus();
    
    ctx.fillStyle = 'rgba(100, 116, 139, 0.7)';
    ctx.font = '10px monospace';
    ctx.textAlign = 'right';
    
    const lines = [
      `FPS: ${status.fps}`,
      `Nodes: ${this.nodes.length}`,
      `Links: ${this.links.length}`,
      `Velocity: ${status.currentVelocity.toFixed(2)} px/f`,
      `Converged: ${status.isConverged ? '✓' : '✗'}`,
      `Frames: ${status.frameCount}/${status.requiredFrames}`
    ];
    
    lines.forEach((line, i) => {
      ctx.fillText(line, width - 10, height - 10 - (lines.length - 1 - i) * 14);
    });
  },
  
  // 鼠标事件处理
  onMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - this.transform.x) / this.transform.scale;
    const y = (e.clientY - rect.top - this.transform.y) / this.transform.scale;
    
    // 检查是否点击了节点
    const clickedNode = this.findNodeAt(x, y);
    
    if (clickedNode) {
      this.draggedNode = clickedNode;
      this.isDragging = true;
      this.selectNode(clickedNode);
    } else {
      this.draggedNode = null;
      this.isDragging = true;
      this.selectedNode = null;
    }
    
    this.lastMouse.x = e.clientX;
    this.lastMouse.y = e.clientY;
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
      if (this.draggedNode) {
        // 拖拽节点
        this.draggedNode.x = x;
        this.draggedNode.y = y;
        this.draggedNode.vx = 0;
        this.draggedNode.vy = 0;
        this.resetConvergence();
      } else {
        // 拖拽视图
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
  },
  
  onWheel(e) {
    e.preventDefault();
    
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.3, Math.min(3, this.transform.scale * delta));
    
    // 以鼠标位置为中心缩放
    const scaleRatio = newScale / this.transform.scale;
    this.transform.x = mouseX - (mouseX - this.transform.x) * scaleRatio;
    this.transform.y = mouseY - (mouseY - this.transform.y) * scaleRatio;
    this.transform.scale = newScale;
  },
  
  onDblClick(e) {
    // 双击重置视图
    this.transform.x = 0;
    this.transform.y = 0;
    this.transform.scale = 1;
    this.resetConvergence();
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
      
      if (dist < node.size * 2) {
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
  
  /**
   * 重置收敛状态
   */
  resetConvergence() {
    this.convergence.frameCount = 0;
    this.convergence.isConverged = false;
    this.convergence.history = [];
    this.alpha = Math.max(this.alpha, 0.1);
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
    
    // 5秒后自动关闭
    setTimeout(() => {
      if (panel.parentElement) panel.remove();
    }, 5000);
  },
  
  destroy() {
    // 停止动画循环
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    // 重置初始化状态
    this.isInitialized = false;
    
    // 清理资源
    this.nodes = [];
    this.links = [];
    this.particles = [];
    
    console.log('[GraphViz] 资源已清理');
  }
};

// 导出
if (typeof window !== 'undefined') {
  window.GraphViz = GraphViz;
}
