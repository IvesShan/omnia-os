/**
 * 神经图谱可视化 - Obsidian 风格升级版
 * 特性：力导向布局、悬停高亮、节点拖拽、发光效果
 */

const GraphViz = {
  // Three.js 核心对象
  scene: null,
  camera: null,
  renderer: null,
  composer: null,
  controls: null,
  
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
    alphaDecay: 0.01,
    velocityDecay: 0.4
  },
  
  // 交互状态
  hoveredNode: null,
  selectedNode: null,
  draggedNode: null,
  raycaster: null,
  mouse: new THREE.Vector2(),
  
  // 动画
  animationId: null,
  isPaused: false,
  time: 0,
  
  // 类型颜色映射 (Obsidian 风格)
  typeColors: {
    'PERSON': 0x22d3ee,
    'PROJECT': 0xa855f7,
    'FILE': 0x10b981,
    'CONCEPT': 0xff8a00,
    'DATE': 0x6366f1,
    'ENTITY': 0xec4899,
    'DEFAULT': 0x64748b
  },
  
  async init() {
    console.log("[GraphViz] 初始化 Obsidian 风格神经图谱");
    
    try {
      await this.loadStats();
      await this.loadGraph();
      this.initThreeJS();
      this.createBrainParticles();
      this.createKnowledgeNodes();
      this.initForceSimulation();
      this.setupInteraction();
      this.setupPostProcessing();
      this.animate();
      
      console.log("[GraphViz] 初始化完成");
    } catch (error) {
      console.error("[GraphViz] 初始化错误:", error);
    }
  },

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
    
    // 轨道控制器
    if (typeof OrbitControls !== 'undefined') {
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      this.controls.enableZoom = true;
      this.controls.autoRotate = false;
    }
    
    // 射线检测器
    this.raycaster = new THREE.Raycaster();
    
    // 光源
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    this.scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0x00ffff, 1, 20);
    pointLight.position.set(5, 5, 5);
    this.scene.add(pointLight);
    
    const pointLight2 = new THREE.PointLight(0xff8a00, 1, 20);
    pointLight2.position.set(-5, -5, 5);
    this.scene.add(pointLight2);
    
    // 窗口调整
    window.addEventListener('resize', () => {
      if (!this.camera || !this.renderer) return;
      const w = container.clientWidth || 300;
      const h = container.clientHeight || 280;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });

    // 页面可见性检测 - 后台时暂停渲染
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.isPaused = true;
        console.log('[GraphViz] 页面隐藏，暂停渲染');
      } else {
        this.isPaused = false;
        console.log('[GraphViz] 页面可见，恢复渲染');
      }
    });

  },
  createBrainParticles() {
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
      const response = await fetch('/api/graph/stats', { cache: 'no-store' });
      const text = await response.text();
      try {
        const data = JSON.parse(text);
        const nodesEl = document.getElementById('gs-nodes');
        const edgesEl = document.getElementById('gs-edges');
        if (nodesEl) nodesEl.textContent = data.nodes || '—';
        if (edgesEl) edgesEl.textContent = data.edges || '—';
      } catch (parseErr) {
        // Response was not JSON (likely HTML error page) — silently ignore
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
        this.graphData = {
          nodes: data.nodes || [],
          edges: data.edges || []
        };
        console.log('[GraphViz] 加载图谱:', this.graphData.nodes.length, '节点');
      } catch (parseErr) {
        console.warn('[GraphViz] graph 非 JSON 响应，跳过');
        this.graphData = { nodes: [], edges: [] };
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.warn('[GraphViz] 加载图谱失败:', error.message);
      }
      this.graphData = { nodes: [], edges: [] };
    }
  },

  createKnowledgeNodes() {
    console.log('[GraphViz] 创建知识节点:', this.graphData.nodes.length, '个');
    
    // 初始化力导向节点数据
    this.simulation.nodes = this.graphData.nodes.map((node, i) => ({
      id: node.name || node.id,
      x: (Math.random() - 0.5) * 6,
      y: (Math.random() - 0.5) * 6,
      z: (Math.random() - 0.5) * 6,
      vx: 0, vy: 0, vz: 0,
      data: node
    }));
    
    // 创建 3D 节点对象
    this.graphData.nodes.forEach((node, i) => {
      node.label = node.label || node.name || node.id;
      node.type = node.type || 'ENTITY';
      const color = this.typeColors[node.type] || this.typeColors.DEFAULT;
      
      // 主球体
      const geometry = new THREE.SphereGeometry(0.12, 16, 16);
      const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.3,
        metalness: 0.7,
        roughness: 0.3
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      
      // 初始位置
      const simNode = this.simulation.nodes[i];
      mesh.position.set(simNode.x, simNode.y, simNode.z);
      
      // 发光光晕
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
    
    // 创建连线
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
    // 力导向参数
    this.simulation.alpha = 1.0;
    this.simulation.running = true;
  },
  
  updateForceSimulation() {
    if (!this.simulation.running) return;
    
    const nodes = this.simulation.nodes;
    const alpha = this.simulation.alpha;
    
    // 斥力（节点之间）
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const dz = nodes[j].z - nodes[i].z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        const force = (2.0 * alpha) / (dist * dist);
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = (dz / dist) * force;
        
        nodes[i].vx -= fx;
        nodes[i].vy -= fy;
        nodes[i].vz -= fz;
        nodes[j].vx += fx;
        nodes[j].vy += fy;
        nodes[j].vz += fz;
      }
    }
    
    // 引力（连接的节点）
    this.graphData.edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);
      
      if (source && target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dz = target.z - source.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        const force = (dist - 1.5) * 0.1 * alpha;
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        const fz = (dz / dist) * force;
        
        source.vx += fx;
        source.vy += fy;
        source.vz += fz;
        target.vx -= fx;
        target.vy -= fy;
        target.vz -= fz;
      }
    });
    
    // 向心力
    nodes.forEach(node => {
      const dist = Math.sqrt(node.x * node.x + node.y * node.y + node.z * node.z);
      if (dist > 4) {
        const force = (dist - 4) * 0.02 * alpha;
        node.vx -= (node.x / dist) * force;
        node.vy -= (node.y / dist) * force;
        node.vz -= (node.z / dist) * force;
      }
    });
    
    // 更新位置
    const decay = this.simulation.velocityDecay;
    nodes.forEach((node, i) => {
      if (this.draggedNode && this.nodeObjects[i] === this.draggedNode) return;
      
      node.vx *= (1 - decay);
      node.vy *= (1 - decay);
      node.vz *= (1 - decay);
      
      node.x += node.vx;
      node.y += node.vy;
      node.z += node.vz;
      
      this.nodeObjects[i].position.set(node.x, node.y, node.z);
    });
    
    // 更新连线
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
    
    // 衰减
    this.simulation.alpha -= this.simulation.alphaDecay;
    if (this.simulation.alpha < 0.01) {
      this.simulation.running = false;
    }
  },

  setupInteraction() {
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
    // 鼠标移动 - 悬停检测
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      
      this.checkHover();
    });
    
    // 鼠标按下 - 开始拖拽
    container.addEventListener('mousedown', (e) => {
      if (this.hoveredNode) {
        this.draggedNode = this.hoveredNode;
        this.controls.enabled = false;
      }
    });
    
    // 鼠标释放 - 结束拖拽
    container.addEventListener('mouseup', () => {
      if (this.draggedNode) {
        this.draggedNode = null;
        this.controls.enabled = true;
        // 重新启动力导向
        this.simulation.alpha = 0.3;
        this.simulation.running = true;
      }
    });
    
    // 鼠标点击 - 显示详情
    container.addEventListener('click', (e) => {
      if (this.hoveredNode && !this.draggedNode) {
        this.showNodeDetails(this.hoveredNode.userData.node);
      }
    });
    
    // 拖拽移动
    container.addEventListener('mousemove', (e) => {
      if (this.draggedNode) {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), -this.draggedNode.position.z);
        const point = new THREE.Vector3();
        this.raycaster.ray.intersectPlane(plane, point);
        
        if (point) {
          this.draggedNode.position.copy(point);
          
          // 更新模拟数据
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
    
    // 重置之前悬停的节点
    if (this.hoveredNode && (!intersects.length || intersects[0].object !== this.hoveredNode)) {
      this.setNodeHighlight(this.hoveredNode, false);
      this.hoveredNode = null;
    }
    
    // 设置新的悬停节点
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
    
    // 更新光晕
    const glow = node.children[0];
    if (glow) {
      glow.material.opacity = highlight ? 0.4 : 0.15;
      glow.scale.setScalar(highlight ? 1.3 : 1.0);
    }
    
    // 高亮连接的节点和连线
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
    
    // 创建或更新详情面板
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
    const colorHex = '#' + color.toString(16).padStart(6, '0');
    
    panel.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <h3 style="margin: 0; color: ${colorHex}; font-size: 18px;">${node.label || node.name}</h3>
        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #64748b; cursor: pointer; font-size: 20px;">&times;</button>
      </div>
      <div style="margin-bottom: 12px;">
        <span style="color: #64748b; font-size: 12px;">类型</span>
        <div style="color: ${colorHex}; font-weight: 500;">${node.type || 'ENTITY'}</div>
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
    
    // 3秒后自动关闭
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
    try {
      if (typeof EffectComposer === 'undefined' || typeof RenderPass === 'undefined') {
        console.warn('[GraphViz] 后处理库未加载，降级为基本渲染');
        this.composer = null;
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
    } catch (e) {
      console.warn('[GraphViz] 后处理初始化失败，降级为基本渲染:', e.message);
      this.composer = null;
    }
  },
  
  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());

    // 后台时跳过渲染
    if (this.isPaused) return;
    
    this.time += 0.01;
    
    // 更新粒子
    if (this.brainParticles && this.brainParticles.material.uniforms) {
      this.brainParticles.material.uniforms.time.value = this.time;
    }
    
    // 更新力导向
    this.updateForceSimulation();
    
    // 更新控制器
    if (this.controls) {
      this.controls.update();
    }
    
    // 渲染
    if (this.composer) {
      this.composer.render();
    } else if (this.renderer) {
      this.renderer.render(this.scene, this.camera);
    }
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
