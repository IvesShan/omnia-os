/**
 * 神经图谱可视化 - 支持 WebGL 3D 和 Canvas 2D 降级
 * 特性：力导向布局、悬停高亮、节点拖拽、发光效果
 */

const GraphViz = {
  // 渲染模式
  renderMode: '2d', // '3d' or '2d'
  
  // Three.js 核心对象 (3D 模式)
  scene: null,
  camera: null,
  renderer: null,
  composer: null,
  controls: null,
  
  // Canvas 2D 对象 (2D 降级模式)
  canvas: null,
  ctx: null,
  
  // 粒子系统
  brainParticles: null,
  particleCount: 5000,
  
  // 知识图谱
  graphData: { nodes: [], edges: [] },
  nodeObjects: [],
  connectionLines: [],
  nodeMap: {},
  
  // 力导向模拟
  simulation: {
    nodes: [],
    running: true,
    alpha: 1.0,
    alphaDecay: 0.008,
    velocityDecay: 0.4
  },
  
  // 交互状态
  hoveredNode: null,
  selectedNode: null,
  draggedNode: null,
  raycaster: null,
  mouse: { x: 0, y: 0 },
  
  // 动画
  animationId: null,
  time: 0,
  
  // 类型颜色映射 (Obsidian 风格)
  typeColors: {
    'PERSON': '#22d3ee',
    'PROJECT': '#a855f7',
    'FILE': '#10b981',
    'CONCEPT': '#ff8a00',
    'DATE': '#6366f1',
    'ENTITY': '#ec4899',
    'DEFAULT': '#64748b'
  },
  typeColorsHex: {
    'PERSON': 0x22d3ee,
    'PROJECT': 0xa855f7,
    'FILE': 0x10b981,
    'CONCEPT': 0xff8a00,
    'DATE': 0x6366f1,
    'ENTITY': 0xec4899,
    'DEFAULT': 0x64748b
  },
  
  // 检测 WebGL 支持
  isWebGLAvailable() {
    try {
      const canvas = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && 
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  },
  
  async init() {
    console.log("[GraphViz] 初始化神经图谱");
    
    try {
      await this.loadStats();
      await this.loadGraph();
      
      // 检测是否支持 WebGL
      if (this.isWebGLAvailable() && typeof THREE !== 'undefined') {
        console.log("[GraphViz] 使用 WebGL 3D 渲染");
        this.renderMode = '3d';
        this.initThreeJS();
        this.createBrainParticles();
        this.createKnowledgeNodes();
        this.initForceSimulation();
        this.setupInteraction3D();
        this.setupPostProcessing();
      } else {
        console.log("[GraphViz] WebGL 不可用，使用 Canvas 2D 降级渲染");
        this.renderMode = '2d';
        this.initCanvas2D();
        this.createKnowledgeNodes2D();
        this.initForceSimulation();
        this.setupInteraction2D();
      }
      
      this.animate();
      console.log("[GraphViz] 初始化完成 (" + this.renderMode + " 模式)");
    } catch (error) {
      console.error("[GraphViz] 初始化错误:", error);
      // 最终降级：纯文本列表
      this.showFallbackList();
    }
  },

  // ========== Canvas 2D 降级方案 ==========
  
  initCanvas2D() {
    const container = document.getElementById('graph-canvas');
    if (!container) {
      console.error('[GraphViz] 找不到 graph-canvas');
      return;
    }
    
    container.innerHTML = '';
    
    const width = container.clientWidth || 300;
    const height = container.clientHeight || 280;
    
    this.canvas = document.createElement('canvas');
    this.canvas.width = width * (window.devicePixelRatio || 1);
    this.canvas.height = height * (window.devicePixelRatio || 1);
    this.canvas.style.width = width + 'px';
    this.canvas.style.height = height + 'px';
    container.appendChild(this.canvas);
    
    this.ctx = this.canvas.getContext('2d');
    this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    
    this.canvasWidth = width;
    this.canvasHeight = height;
    this.offsetX = width / 2;
    this.offsetY = height / 2;
    this.scale2d = 40; // 像素/单位
    
    // 窗口调整
    window.addEventListener('resize', () => {
      const w = container.clientWidth || 300;
      const h = container.clientHeight || 280;
      this.canvas.width = w * (window.devicePixelRatio || 1);
      this.canvas.height = h * (window.devicePixelRatio || 1);
      this.canvas.style.width = w + 'px';
      this.canvas.style.height = h + 'px';
      this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
      this.canvasWidth = w;
      this.canvasHeight = h;
      this.offsetX = w / 2;
      this.offsetY = h / 2;
    });
  },
  
  createKnowledgeNodes2D() {
    console.log('[GraphViz] 创建 2D 知识节点:', this.graphData.nodes.length, '个');
    
    this.simulation.nodes = this.graphData.nodes.map((node, i) => ({
      id: node.name || node.id,
      x: (Math.random() - 0.5) * 6,
      y: (Math.random() - 0.5) * 6,
      z: 0,
      vx: 0, vy: 0, vz: 0,
      data: node
    }));
    
    this.graphData.nodes.forEach((node, i) => {
      node.label = node.label || node.name || node.id;
      node.type = node.type || 'ENTITY';
      this.nodeMap[node.name || node.id] = i;
    });
  },
  
  setupInteraction2D() {
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      this.mouse.x = e.clientX - rect.left;
      this.mouse.y = e.clientY - rect.top;
      this.checkHover2D();
      
      if (this.draggedNode !== null) {
        const node = this.simulation.nodes[this.draggedNode];
        node.x = (this.mouse.x - this.offsetX) / this.scale2d;
        node.y = (this.mouse.y - this.offsetY) / this.scale2d;
      }
    });
    
    container.addEventListener('mousedown', (e) => {
      if (this.hoveredNode !== null) {
        this.draggedNode = this.hoveredNode;
      }
    });
    
    container.addEventListener('mouseup', () => {
      if (this.draggedNode !== null) {
        this.draggedNode = null;
        this.simulation.alpha = 0.3;
        this.simulation.running = true;
      }
    });
    
    container.addEventListener('click', () => {
      if (this.hoveredNode !== null && this.draggedNode === null) {
        const node = this.simulation.nodes[this.hoveredNode];
        this.showNodeDetails(node.data);
      }
    });
    
    // 缩放
    container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      this.scale2d *= delta;
      this.scale2d = Math.max(15, Math.min(100, this.scale2d));
    });
  },
  
  checkHover2D() {
    this.hoveredNode = null;
    const nodes = this.simulation.nodes;
    
    for (let i = 0; i < nodes.length; i++) {
      const sx = nodes[i].x * this.scale2d + this.offsetX;
      const sy = nodes[i].y * this.scale2d + this.offsetY;
      const dx = this.mouse.x - sx;
      const dy = this.mouse.y - sy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      
      if (dist < 12) {
        this.hoveredNode = i;
        break;
      }
    }
  },
  
  render2D() {
    const ctx = this.ctx;
    if (!ctx) return;
    
    const w = this.canvasWidth;
    const h = this.canvasHeight;
    
    // 清空
    ctx.fillStyle = 'rgba(10, 14, 39, 0.95)';
    ctx.fillRect(0, 0, w, h);
    
    // 绘制连线
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.2)';
    ctx.lineWidth = 1;
    this.graphData.edges.forEach(edge => {
      const si = this.nodeMap[edge.source];
      const ti = this.nodeMap[edge.target];
      if (si === undefined || ti === undefined) return;
      
      const sn = this.simulation.nodes[si];
      const tn = this.simulation.nodes[ti];
      
      const sx = sn.x * this.scale2d + this.offsetX;
      const sy = sn.y * this.scale2d + this.offsetY;
      const tx = tn.x * this.scale2d + this.offsetX;
      const ty = tn.y * this.scale2d + this.offsetY;
      
      // 高亮连接
      const isHighlighted = this.hoveredNode === si || this.hoveredNode === ti;
      ctx.strokeStyle = isHighlighted ? 'rgba(255, 138, 0, 0.6)' : 'rgba(34, 211, 238, 0.15)';
      ctx.lineWidth = isHighlighted ? 2 : 1;
      
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
    });
    
    // 绘制节点
    const nodes = this.simulation.nodes;
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const data = node.data;
      const x = node.x * this.scale2d + this.offsetX;
      const y = node.y * this.scale2d + this.offsetY;
      
      const color = this.typeColors[data.type] || this.typeColors.DEFAULT;
      const isHovered = this.hoveredNode === i;
      const radius = isHovered ? 8 : 5;
      
      // 发光效果
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 3);
      gradient.addColorStop(0, color + '40');
      gradient.addColorStop(1, color + '00');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, radius * 3, 0, Math.PI * 2);
      ctx.fill();
      
      // 节点
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
      
      // 标签
      if (isHovered || nodes.length < 30) {
        ctx.fillStyle = isHovered ? '#ffffff' : '#94a3b8';
        ctx.font = isHovered ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(data.label || data.name, x, y - radius - 6);
      }
    }
    
    // 模式标识
    ctx.fillStyle = 'rgba(100, 116, 139, 0.5)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('Canvas 2D', 8, h - 8);
  },
  
  // ========== WebGL 3D 方案 (原代码) ==========
  
  initThreeJS() {
    const container = document.getElementById('graph-canvas');
    if (!container) {
      console.error('[GraphViz] 找不到 graph-canvas');
      return;
    }
    
    let width = container.clientWidth || 300;
    let height = container.clientHeight || 280;
    
    container.innerHTML = '';
    
    this.scene = new THREE.Scene();
    
    const aspect = width / height;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
    this.camera.position.set(0, 0, 8);
    
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);
    
    if (typeof OrbitControls !== 'undefined') {
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.enableZoom = true;
      this.controls.autoRotate = false;
    }
    
    this.raycaster = new THREE.Raycaster();
    
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    this.scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0x00ffff, 1, 20);
    pointLight.position.set(5, 5, 5);
    this.scene.add(pointLight);
    
    const pointLight2 = new THREE.PointLight(0xff8a00, 1, 20);
    pointLight2.position.set(-5, -5, 5);
    this.scene.add(pointLight2);
    
    window.addEventListener('resize', () => {
      if (!this.camera || !this.renderer) return;
      const w = container.clientWidth || 300;
      const h = container.clientHeight || 280;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });
  },

  createBrainParticles() {
    if (typeof THREE === 'undefined') return;
    
    const positions = new Float32Array(this.particleCount * 3);
    const colors = new Float32Array(this.particleCount * 3);
    
    const colorOrange = new THREE.Color(0xff8a00);
    const colorCyan = new THREE.Color(0x22d3ee);
    
    for (let i = 0; i < this.particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.5 + Math.random() * 0.5;
      
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);
      
      const color = Math.random() > 0.5 ? colorOrange : colorCyan;
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    
    const material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        pointSize: { value: 1.0 }
      },
      vertexShader: `
        attribute vec3 color;
        varying vec3 vColor;
        uniform float time;
        uniform float pointSize;
        
        void main() {
          vColor = color;
          vec3 pos = position;
          pos += 0.1 * sin(time + position.x * 10.0) * normalize(position);
          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          gl_PointSize = pointSize * (30.0 / -mvPosition.z);
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        
        void main() {
          float dist = length(gl_PointCoord - vec2(0.5));
          if (dist > 0.5) discard;
          float alpha = 1.0 - smoothstep(0.3, 0.5, dist);
          gl_FragColor = vec4(vColor, alpha * 0.3);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    
    this.brainParticles = new THREE.Points(geometry, material);
    this.scene.add(this.brainParticles);
  },

  async loadStats() {
    try {
      const response = await fetch('/api/graph/stats');
      const data = await response.json();
      
      const nodesEl = document.getElementById('gs-nodes');
      const edgesEl = document.getElementById('gs-edges');
      
      if (nodesEl) nodesEl.textContent = data.nodes || '—';
      if (edgesEl) edgesEl.textContent = data.edges || '—';
    } catch (error) {
      console.error('[GraphViz] 加载统计失败:', error);
    }
  },
  
  async loadGraph() {
    try {
      const response = await fetch('/api/graph');
      const data = await response.json();
      
      this.graphData = {
        nodes: data.nodes || [],
        edges: data.edges || []
      };
      
      console.log('[GraphViz] 加载图谱:', this.graphData.nodes.length, '节点');
    } catch (error) {
      console.error('[GraphViz] 加载图谱失败:', error);
    }
  },

  createKnowledgeNodes() {
    console.log('[GraphViz] 创建知识节点:', this.graphData.nodes.length, '个');
    
    this.simulation.nodes = this.graphData.nodes.map((node, i) => ({
      id: node.name || node.id,
      x: (Math.random() - 0.5) * 6,
      y: (Math.random() - 0.5) * 6,
      z: (Math.random() - 0.5) * 6,
      vx: 0, vy: 0, vz: 0,
      data: node
    }));
    
    this.graphData.nodes.forEach((node, i) => {
      node.label = node.label || node.name || node.id;
      node.type = node.type || 'ENTITY';
      const color = this.typeColorsHex[node.type] || this.typeColorsHex.DEFAULT;
      
      const geometry = new THREE.SphereGeometry(0.12, 16, 16);
      const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.3,
        metalness: 0.7,
        roughness: 0.3
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      
      const simNode = this.simulation.nodes[i];
      mesh.position.set(simNode.x, simNode.y, simNode.z);
      
      const glowGeometry = new THREE.SphereGeometry(0.18, 16, 16);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      mesh.add(glow);
      
      mesh.userData = { node, index: i, originalColor: color };
      this.scene.add(mesh);
      this.nodeObjects.push(mesh);
      this.nodeMap[node.name || node.id] = mesh;
    });
    
    this.createConnections();
  },

  createConnections() {
    this.connectionLines = [];
    
    this.graphData.edges.forEach(edge => {
      const sourceMesh = this.nodeMap[edge.source];
      const targetMesh = this.nodeMap[edge.target];
      
      if (sourceMesh && targetMesh) {
        const points = [sourceMesh.position.clone(), targetMesh.position.clone()];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
          color: 0x22d3ee,
          transparent: true,
          opacity: 0.2
        });
        
        const line = new THREE.Line(geometry, material);
        line.userData = { source: edge.source, target: edge.target };
        this.scene.add(line);
        this.connectionLines.push(line);
      }
    });
    
    console.log('[GraphViz] 创建连线:', this.connectionLines.length, '条');
  },
  
  initForceSimulation() {
    this.simulation.alpha = 1.0;
    this.simulation.running = true;
  },
  
  updateForceSimulation() {
    if (!this.simulation.running) return;
    
    const nodes = this.simulation.nodes;
    const alpha = this.simulation.alpha;
    const is2D = this.renderMode === '2d';
    
    // 斥力
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const dz = is2D ? 0 : (nodes[j].z - nodes[i].z);
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        const force = (2.0 * alpha) / (dist * dist);
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = is2D ? 0 : (dz / dist) * force;
        
        nodes[i].vx -= fx;
        nodes[i].vy -= fy;
        if (!is2D) nodes[i].vz -= fz;
        nodes[j].vx += fx;
        nodes[j].vy += fy;
        if (!is2D) nodes[j].vz += fz;
      }
    }
    
    // 引力
    this.graphData.edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);
      
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dz = is2D ? 0 : (target.z - source.z);
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        const force = (dist - 1.5) * 0.1 * alpha;
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = is2D ? 0 : (dz / dist) * force;
        
        source.vx += fx;
        source.vy += fy;
        if (!is2D) source.vz += fz;
        target.vx -= fx;
        target.vy -= fy;
        if (!is2D) target.vz -= fz;
      }
    });
    
    // 向心力
    nodes.forEach(node => {
      const dist = Math.sqrt(node.x * node.x + node.y * node.y + (is2D ? 0 : node.z * node.z));
      if (dist > 4) {
        const force = (dist - 4) * 0.02 * alpha;
        node.vx -= (node.x / dist) * force;
        node.vy -= (node.y / dist) * force;
        if (!is2D) node.vz -= (node.z / dist) * force;
      }
    });
    
    // 更新位置
    const decay = this.simulation.velocityDecay;
    nodes.forEach((node, i) => {
      const isDragged3D = this.renderMode === '3d' && this.draggedNode && this.nodeObjects[i] === this.draggedNode;
      const isDragged2D = this.renderMode === '2d' && this.draggedNode === i;
      if (isDragged3D || isDragged2D) return;
      
      node.vx *= (1 - decay);
      node.vy *= (1 - decay);
      if (!is2D) node.vz *= (1 - decay);
      
      node.x += node.vx;
      node.y += node.vy;
      if (!is2D) node.z += node.vz;
      
      if (this.renderMode === '3d' && this.nodeObjects[i]) {
        this.nodeObjects[i].position.set(node.x, node.y, node.z);
      }
    });
    
    // 更新 3D 连线
    if (this.renderMode === '3d') {
      this.connectionLines.forEach(line => {
        const sourceMesh = this.nodeMap[line.userData.source];
        const targetMesh = this.nodeMap[line.userData.target];
        if (sourceMesh && targetMesh) {
          const positions = line.geometry.attributes.position.array;
          positions[0] = sourceMesh.position.x;
          positions[1] = sourceMesh.position.y;
          positions[2] = sourceMesh.position.z;
          positions[3] = targetMesh.position.x;
          positions[4] = targetMesh.position.y;
          positions[5] = targetMesh.position.z;
          line.geometry.attributes.position.needsUpdate = true;
        }
      });
    }
    
    // 衰减
    this.simulation.alpha -= this.simulation.alphaDecay;
    if (this.simulation.alpha < 0.01) {
      this.simulation.running = false;
    }
  },

  setupInteraction3D() {
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      this.checkHover();
    });
    
    container.addEventListener('mousedown', (e) => {
      if (this.hoveredNode) {
        this.draggedNode = this.hoveredNode;
        this.controls.enabled = false;
      }
    });
    
    container.addEventListener('mouseup', () => {
      if (this.draggedNode) {
        this.draggedNode = null;
        this.controls.enabled = true;
        this.simulation.alpha = 0.3;
        this.simulation.running = true;
      }
    });
    
    container.addEventListener('click', (e) => {
      if (this.hoveredNode && !this.draggedNode) {
        this.showNodeDetails(this.hoveredNode.userData.node);
      }
    });
    
    container.addEventListener('mousemove', (e) => {
      if (this.draggedNode) {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), -this.draggedNode.position.z);
        const point = new THREE.Vector3();
        this.raycaster.ray.intersectPlane(plane, point);
        
        if (point) {
          this.draggedNode.position.copy(point);
          const idx = this.draggedNode.userData.index;
          this.simulation.nodes[idx].x = point.x;
          this.simulation.nodes[idx].y = point.y;
          this.simulation.nodes[idx].z = point.z;
        }
      }
    });
  },
  
  checkHover() {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.nodeObjects);
    
    if (this.hoveredNode && (!intersects.length || intersects[0].object !== this.hoveredNode)) {
      this.setNodeHighlight(this.hoveredNode, false);
      this.hoveredNode = null;
    }
    
    if (intersects.length > 0) {
      const node = intersects[0].object;
      if (node !== this.hoveredNode) {
        this.hoveredNode = node;
        this.setNodeHighlight(node, true);
      }
    }
  },
  
  setNodeHighlight(node, highlight) {
    if (!node) return;
    
    const scale = highlight ? 1.5 : 1.0;
    node.scale.setScalar(scale);
    
    const glow = node.children[0];
    if (glow) {
      glow.material.opacity = highlight ? 0.4 : 0.15;
      glow.scale.setScalar(highlight ? 1.3 : 1.0);
    }
    
    const nodeId = node.userData.node?.name || node.userData.node?.id;
    
    this.connectionLines.forEach(line => {
      const isConnected = line.userData.source === nodeId || line.userData.target === nodeId;
      line.material.opacity = highlight && isConnected ? 0.6 : 0.2;
      line.material.color.setHex(highlight && isConnected ? 0xff8a00 : 0x22d3ee);
    });
    
    this.nodeObjects.forEach(otherNode => {
      const otherId = otherNode.userData.node?.name || otherNode.userData.node?.id;
      const isNeighbor = this.graphData.edges.some(
        e => (e.source === nodeId && e.target === otherId) || 
             (e.target === nodeId && e.source === otherId)
      );
      
      if (highlight && isNeighbor && otherNode !== node) {
        otherNode.scale.setScalar(1.3);
        const otherGlow = otherNode.children[0];
        if (otherGlow) otherGlow.material.opacity = 0.3;
      } else if (!highlight || otherNode !== node) {
        otherNode.scale.setScalar(1.0);
        const otherGlow = otherNode.children[0];
        if (otherGlow) otherGlow.material.opacity = 0.15;
      }
    });
  },

  showNodeDetails(node) {
    console.log('[GraphViz] 显示节点详情:', node);
    
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
    
    const color = this.typeColors[node.type] || this.typeColors.DEFAULT;
    
    panel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0; color: ${color}; font-size: 18px;">${node.label || node.name}</h3>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #64748b; cursor: pointer; font-size: 20px;">&times;</button>
      </div>
      <div style="margin-bottom: 12px;">
        <span style="color: #64748b; font-size: 12px;">类型</span>
        <div style="color: ${color}; font-weight: 500;">${node.type || 'ENTITY'}</div>
      </div>
      ${node.evidence ? `
        <div style="margin-bottom: 12px;">
          <span style="color: #64748b; font-size: 12px;">来源</span>
          <div style="color: #94a3b8; font-size: 14px;">${node.evidence}</div>
        </div>
      ` : ''}
      <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(100, 116, 139, 0.3);">
        <span style="color: #64748b; font-size: 12px;">连接数</span>
        <div style="color: #22d3ee; font-weight: 500;">${this.getConnectionCount(node.name || node.id)}</div>
      </div>
    `;
    
    setTimeout(() => {
      if (panel.parentElement) panel.remove();
    }, 5000);
  },
  
  getConnectionCount(nodeId) {
    return this.graphData.edges.filter(
      e => e.source === nodeId || e.target === nodeId
    ).length;
  },

  setupPostProcessing() {
    if (typeof EffectComposer === 'undefined') {
      console.warn('[GraphViz] EffectComposer 未加载');
      return;
    }
    
    this.composer = new EffectComposer(this.renderer);
    
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);
    
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      0.4,
      0.4,
      0.85
    );
    this.composer.addPass(bloomPass);
  },
  
  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());
    
    this.time += 0.01;
    
    // 更新力导向
    this.updateForceSimulation();
    
    if (this.renderMode === '3d') {
      // 3D 渲染
      if (this.brainParticles && this.brainParticles.material.uniforms) {
        this.brainParticles.material.uniforms.time.value = this.time;
      }
      if (this.controls) {
        this.controls.update();
      }
      if (this.composer) {
        this.composer.render();
      } else if (this.renderer) {
        this.renderer.render(this.scene, this.camera);
      }
    } else {
      // 2D 渲染
      this.render2D();
    }
  },
  
  // 最终降级：纯文本列表
  showFallbackList() {
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
    container.innerHTML = '';
    container.style.overflow = 'auto';
    container.style.padding = '10px';
    
    const list = document.createElement('div');
    list.style.cssText = 'font-size: 12px; color: #94a3b8;';
    
    if (this.graphData.nodes.length === 0) {
      list.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px;">暂无图谱数据</div>';
    } else {
      this.graphData.nodes.forEach(node => {
        const color = this.typeColors[node.type] || this.typeColors.DEFAULT;
        const item = document.createElement('div');
        item.style.cssText = `padding: 4px 8px; margin: 2px 0; border-left: 3px solid ${color}; border-radius: 3px; background: rgba(255,255,255,0.03);`;
        item.innerHTML = `<span style="color: ${color}; font-weight: 500;">${node.label || node.name}</span> <span style="color: #475569; font-size: 10px;">${node.type || ''}</span>`;
        list.appendChild(item);
      });
    }
    
    container.appendChild(list);
  },
  
  destroy() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    if (this.renderer) {
      this.renderer.dispose();
    }
    if (this.scene) {
      this.scene.clear();
    }
  }
};

// 导出
if (typeof window !== 'undefined') {
  window.GraphViz = GraphViz;
}
