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
  isDraggedNode: false,
  dragStartPos: { x: 0, y: 0 },
  lastMouse: { x: 0, y: 0 },
  
  // 力导向参数
  physics: {
    repulsion: 500,            // 斥力强度（正值）
    springStrength: 0.005,     // 弹簧强度
    idealLinkLength: 120,      // 理想链接长度
    damping: 0.95,             // 阻尼（提高到0.95）
    centerForce: 0,            // 向心力（设为0）
    maxVelocity: 8,            // 最大速度（降低到8）
    coolingFactor: 0.995,      // 冷却因子
    minAlpha: 0.1,             // 最小活跃度（提高到0.1）
    convergenceThreshold: 0.05,
    convergenceFrames: 60,
  },
  
  // 边类型权重（用于计算理想长度）
  edgeTypeWeights: {
    'BELONGS_TO': 0.6,      // 属于：短边
    'DEPENDS_ON': 0.8,      // 依赖：中等边
    'RELATED_TO': 1.2,      // 相关：长边
    'WORKED_ON': 0.7,       // 工作：中短边
    'KNOWS_ABOUT': 1.5,     // 知道：最长边
    'default': 1.0
  },
  
  alpha: 1.0,
  // 添加微弱的随机扰动，让节点持续轻微运动
  perturbationStrength: 0.02,
  
  convergence: {
    frameCount: 0,
    isConverged: false,
    history: []
  },
  
  grid: {
    cellSize: 150,
    cells: {}
  },
  
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
  
  particles: [],
  particleTimer: 0,
  animationFrameId: null,
  isInitialized: false,
  
  performance: {
    lastFrameTime: 0,
    frameCount: 0,
    fps: 0
  },
  
  async init() {
    if (this.isInitialized) {
      await this.loadStats();
      await this.loadGraph();
      this.resetConvergence();
      return;
    }
    
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
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
      const data = JSON.parse(await response.text());
      const nodesEl = document.getElementById('gs-nodes');
      const edgesEl = document.getElementById('gs-edges');
      if (nodesEl) nodesEl.textContent = data.nodes || '—';
      if (edgesEl) edgesEl.textContent = data.edges || '—';
    } catch (error) {}
  },
  
  async loadGraph() {
    try {
      const response = await fetch('/api/graph', { cache: 'no-store' });
      const data = JSON.parse(await response.text());
      
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
      
      // 去重边：同一对节点只保留一条边
      const edgeSet = new Set();
      this.links = [];
      (data.edges || []).forEach(e => {
        const key = [e.source, e.target].sort().join('→');
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          this.links.push({
            source: e.source,
            target: e.target,
            type: e.type || 'RELATED',
            weight: e.weight || 1.0
          });
        }
      });
      
      this.nodeMap = {};
      this.nodes.forEach(n => this.nodeMap[n.id] = n);
      this.calculateNodeSizes();
      
      console.log('[GraphViz] 加载图谱:', this.nodes.length, '节点,', this.links.length, '边（去重后）');
    } catch (error) {
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
    const nodeCount = this.nodes.length;
    const spreadRadius = Math.sqrt(nodeCount) * 50;
    
    this.nodes.forEach((node, i) => {
      const angle = i * 2.399963;
      const r = Math.sqrt(i / nodeCount) * spreadRadius;
      node.x = r * Math.cos(angle) + (Math.random() - 0.5) * 60;
      node.y = r * Math.sin(angle) + (Math.random() - 0.5) * 60;
      node.vx = 0;
      node.vy = 0;
    });
    
    const width = this.canvas.width / window.devicePixelRatio;
    const height = this.canvas.height / window.devicePixelRatio;
    this.transform.x = width / 2;
    this.transform.y = height / 2;
    this.transform.scale = 0.3;
    
    this.alpha = 1.0;
    
    if (nodeCount > 1000) {
      this.physics.repulsion = 1200;
      this.physics.idealLinkLength = 250;
      this.physics.springStrength = 0.002;
      this.physics.damping = 0.82;
      this.physics.centerForce = 0;
      this.physics.coolingFactor = 0.999;
      this.grid.cellSize = 250;
    } else if (nodeCount > 300) {
      this.physics.repulsion = 1000;
      this.physics.idealLinkLength = 200;
      this.physics.springStrength = 0.003;
      this.physics.damping = 0.84;
      this.physics.centerForce = 0;
      this.physics.coolingFactor = 0.998;
      this.grid.cellSize = 220;
    } else {
      this.physics.repulsion = 800;
      this.physics.idealLinkLength = 150;
      this.physics.springStrength = 0.004;
      this.physics.damping = 0.85;
      this.physics.centerForce = 0;
      this.physics.coolingFactor = 0.997;
      this.grid.cellSize = 180;
    }
    
    this.physics.convergenceFrames = Math.min(120, Math.floor(nodeCount / 10));
  },
  
  startAnimation() {
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
    
    const animate = (timestamp) => {
      if (timestamp - this.performance.lastFrameTime >= 1000) {
        this.performance.fps = this.performance.frameCount;
        this.performance.frameCount = 0;
        this.performance.lastFrameTime = timestamp;
      }
      this.performance.frameCount++;
      
      // 永远更新物理
      this.update();
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
          // 不强制停止，让节点继续微微运动
        }
        return false;  // 继续动画
      }
    } else {
      this.convergence.frameCount = 0;
      this.convergence.isConverged = false;
    }
    
    return false;  // 永远继续动画
  },
  
  buildGrid() {
    const cellSize = this.grid.cellSize;
    this.grid.cells = {};
    this.nodes.forEach(node => {
      const cellX = Math.floor(node.x / cellSize);
      const cellY = Math.floor(node.y / cellSize);
      const key = `${cellX},${cellY}`;
      if (!this.grid.cells[key]) this.grid.cells[key] = [];
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
        if (this.grid.cells[key]) neighbors.push(...this.grid.cells[key]);
      }
    }
    return neighbors;
  },
  
  update() {
    if (this.nodes.length === 0) return;
    if (this.draggedNode && this.isDraggedNode) return;
    
    this.buildGrid();
    
    // 1. 斥力
    this.nodes.forEach(nodeA => {
      const neighbors = this.getNeighborNodes(nodeA);
      neighbors.forEach(nodeB => {
        if (nodeA === nodeB) return;
        
        const dx = nodeA.x - nodeB.x;
        const dy = nodeA.y - nodeB.y;
        const distSq = dx * dx + dy * dy;
        
        const minDist = 10;
        if (distSq < minDist * minDist) {
          const angle = Math.atan2(dy, dx) || (Math.random() * Math.PI * 2);
          nodeA.vx += Math.cos(angle) * 3;
          nodeA.vy += Math.sin(angle) * 3;
          return;
        }
        
        const force = this.physics.repulsion / distSq;
        const fx = (dx / Math.sqrt(distSq)) * force;
        const fy = (dy / Math.sqrt(distSq)) * force;
        
        nodeA.vx += fx;
        nodeA.vy += fy;
      });
    });
    
    // 2. 弹簧力（根据边类型调整理想长度）
    this.links.forEach(link => {
      const source = this.nodeMap[link.source];
      const target = this.nodeMap[link.target];
      if (!source || !target) return;
      
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      if (dist < 1) return;
      
      // 根据边类型计算理想长度
      const typeWeight = this.edgeTypeWeights[link.type] || this.edgeTypeWeights.default;
      const idealLength = this.physics.idealLinkLength * typeWeight;
      
      // 弹簧力
      const displacement = dist - idealLength;
      const force = displacement * this.physics.springStrength;
      
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    });
    
    // 3. 向心力（设为0，不拉向中心）
    
    // 3.5 添加微弱的随机扰动，让节点持续轻微运动
    this.nodes.forEach(node => {
      // 节点越少扰动越大，越多扰动越小
      const perturb = this.perturbationStrength * Math.sqrt(this.nodes.length);
      node.vx += (Math.random() - 0.5) * perturb;
      node.vy += (Math.random() - 0.5) * perturb;
    });
    
    // 4. 更新位置
    this.nodes.forEach(node => {
      const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      if (speed > this.physics.maxVelocity) {
        node.vx = (node.vx / speed) * this.physics.maxVelocity;
        node.vy = (node.vy / speed) * this.physics.maxVelocity;
      }
      
      node.vx *= this.physics.damping;
      node.vy *= this.physics.damping;
      
      node.x += node.vx * this.alpha;
      node.y += node.vy * this.alpha;
    });
    
    // 5. 冷却（保持最小活跃度，让节点持续微微运动）
    this.alpha *= this.physics.coolingFactor;
    if (this.alpha < 0.1) this.alpha = 0.1;  // 保持最小活跃度为0.1
  },
  
  render() {
    const ctx = this.ctx;
    const width = this.canvas.width / window.devicePixelRatio;
    const height = this.canvas.height / window.devicePixelRatio;
    
    ctx.fillStyle = this.colors.bg;
    ctx.fillRect(0, 0, width, height);
    
    this.drawGrid(ctx, width, height);
    
    ctx.save();
    ctx.translate(this.transform.x, this.transform.y);
    ctx.scale(this.transform.scale, this.transform.scale);
    
    this.drawLinks(ctx);
    this.drawParticles(ctx);
    this.drawNodes(ctx);
    
    ctx.restore();
    
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
        this.particles.push({ source: link.source, target: link.target, progress: 0 });
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
    
    const hoveredNode = this.findNodeAt(x, y);
    if (hoveredNode !== this.hoveredNode) {
      this.hoveredNode = hoveredNode;
      this.canvas.style.cursor = hoveredNode ? 'pointer' : 'default';
    }
    
    if (this.isDragging) {
      const dx = e.clientX - this.dragStartPos.x;
      const dy = e.clientY - this.dragStartPos.y;
      const dragDist = Math.sqrt(dx * dx + dy * dy);
      
      if (this.draggedNode && dragDist > 5) {
        this.isDraggedNode = true;
        this.draggedNode.x = x;
        this.draggedNode.y = y;
        this.draggedNode.vx = 0;
        this.draggedNode.vy = 0;
        this.resetConvergence();
      } else if (!this.draggedNode) {
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
    
    const scaleRatio = newScale / this.transform.scale;
    this.transform.x = mouseX - (mouseX - this.transform.x) * scaleRatio;
    this.transform.y = mouseY - (mouseY - this.transform.y) * scaleRatio;
    this.transform.scale = newScale;
  },
  
  onDblClick(e) {
    this.fitView();
  },
  
  fitView() {
    if (this.nodes.length === 0) return;
    
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
    const scale = Math.min(scaleX, scaleY, 2);
    
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
      if (dist < node.size * 2 / this.transform.scale) return node;
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
  }
};

if (typeof window !== 'undefined') window.GraphViz = GraphViz;
