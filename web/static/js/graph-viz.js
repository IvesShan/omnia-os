/**
 * 神经图谱可视化 - Obsidian 风格升级版
 * 特性：力导向布局、悬停高亮、节点拖拽、发光效果、平滑动画
 */

const GraphViz = {
  // Three.js 核心对象
  scene: null,
  camera: null,
  renderer: null,
  composer: null,
  controls: null,
  
  // 力导向参数
  forceSimulation: null,
  nodePositions: [],
  velocities: [],
  
  // 粒子系统
  brainParticles: null,
  particleCount: 3000,
  
  // 知识图谱
  graphData: { nodes: [], edges: [] },
  nodeObjects: [],
  nodeGlows: [],
  connectionLines: [],
  nodeMap: {},
  
  // 交互状态
  hoveredNode: null,
  selectedNode: null,
  draggedNode: null,
  raycaster: null,
  mouse: new THREE.Vector2(),
  
  // 动画
  animationId: null,
  time: 0,
  
  // 类型颜色映射 (Obsidian 风格)
  typeColors: {
    'PERSON': 0x22d3ee,    // 青色
    'PROJECT': 0xa855f7,   // 紫色
    'FILE': 0x10b981,      // 绿色
    'CONCEPT': 0xff8a00,   // 橙色
    'DATE': 0x6366f1,      // 靛蓝
    'ENTITY': 0xec4899,    // 粉色
    'DEFAULT': 0x64748b    // 灰色
  },
  
  // 力导向参数
  forceStrength: {
    repulsion: 0.8,        // 排斥力
    attraction: 0.005,     // 吸引力
    centerPull: 0.01,      // 向心力
    damping: 0.85          // 阻尼
  },
  
  async init() {
    console.log("[GraphViz] 初始化 Obsidian 风格神经图谱");
    
    try {
      // 加载数据
      await this.loadStats();
      await this.loadGraph();
      
      // 初始化 3D 场景
      this.initThreeJS();
      
      // 初始化射线检测
      this.raycaster = new THREE.Raycaster();
      
      // 创建全息大脑粒子
      this.createBrainParticles();
      
      // 创建知识图谱节点
      this.createKnowledgeNodes();
      
      // 初始化力导向布局
      this.initForceLayout();
      
      // 设置后处理
      this.setupPostProcessing();
      
      // 设置交互事件
      this.setupInteractions();
      
      // 开始动画
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
    
    // 场景
    this.scene = new THREE.Scene();
    
    // 相机
    this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    this.camera.position.set(0, 0, 6);
    
    // 渲染器
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
      this.controls.autoRotate = true;
      this.controls.autoRotateSpeed = 0.5;
    }
    
    // 光源
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    this.scene.add(ambientLight);
    
    const pointLight1 = new THREE.PointLight(0x00ffff, 0.8, 15);
    pointLight1.position.set(3, 3, 3);
    this.scene.add(pointLight1);
    
    const pointLight2 = new THREE.PointLight(0xff8a00, 0.8, 15);
    pointLight2.position.set(-3, -3, 3);
    this.scene.add(pointLight2);
    
    // 窗口调整
    window.addEventListener('resize', () => this.onResize());
  },
  
  createBrainParticles() {
    const positions = new Float32Array(this.particleCount * 3);
    const colors = new Float32Array(this.particleCount * 3);
    const sizes = new Float32Array(this.particleCount);
    
    const colorOrange = new THREE.Color(0xff8a00);
    const colorCyan = new THREE.Color(0x22d3ee);
    
    for (let i = 0; i < this.particleCount; i++) {
      // 大脑形状分布
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 1.8 + Math.random() * 0.3;
      
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.8; // 扁平化
      positions[i * 3 + 2] = r * Math.cos(phi);
      
      const color = Math.random() > 0.5 ? colorOrange : colorCyan;
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
      
      sizes[i] = 0.5 + Math.random() * 1.5;
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    
    const material = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 }
      },
      vertexShader: `
        attribute vec3 color;
        attribute float size;
        varying vec3 vColor;
        varying float vAlpha;
        uniform float time;
        
        void main() {
          vColor = color;
          
          vec3 pos = position;
          float pulse = sin(time * 2.0 + position.x * 5.0) * 0.05;
          pos += pulse * normalize(position);
          
          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          gl_PointSize = size * (40.0 / -mvPosition.z);
          
          vAlpha = 0.3 + 0.2 * sin(time + position.y * 10.0);
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vAlpha;
        
        void main() {
          float dist = length(gl_PointCoord - vec2(0.5));
          if (dist > 0.5) discard;
          
          float alpha = (1.0 - smoothstep(0.2, 0.5, dist)) * vAlpha;
          gl_FragColor = vec4(vColor, alpha);
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
    
    // 创建节点
    this.graphData.nodes.forEach((node, i) => {
      node.label = node.label || node.name || node.id;
      node.type = node.type || 'ENTITY';
      const color = this.typeColors[node.type] || this.typeColors.DEFAULT;
      
      // 主节点
      const geometry = new THREE.SphereGeometry(0.12, 24, 24);
      const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.3,
        metalness: 0.7,
        roughness: 0.3
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      
      // 初始随机位置
      const theta = (i / this.graphData.nodes.length) * Math.PI * 2;
      const phi = Math.random() * Math.PI;
      const r = 1.5 + Math.random() * 0.5;
      
      mesh.position.set(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi)
      );
      
      mesh.userData = { ...node, index: i };
      this.scene.add(mesh);
      this.nodeObjects.push(mesh);
      this.nodeMap[node.name || node.id] = mesh;
      
      // 发光光晕
      const glowGeometry = new THREE.SphereGeometry(0.2, 16, 16);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide
      });
      
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.copy(mesh.position);
      this.scene.add(glow);
      this.nodeGlows.push(glow);
      
      // 初始化力导向数据
      this.nodePositions.push(mesh.position.clone());
      this.velocities.push(new THREE.Vector3());
    });
    
    // 创建连线
    this.graphData.edges.forEach(edge => {
      const sourceNode = this.nodeMap[edge.source];
      const targetNode = this.nodeMap[edge.target];
      
      if (sourceNode && targetNode) {
        this.createConnection(sourceNode, targetNode);
      }
    });
  },
  
  createConnection(source, target) {
    const points = [source.position.clone(), target.position.clone()];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    
    const material = new THREE.LineBasicMaterial({
      color: 0x22d3ee,
      transparent: true,
      opacity: 0.2,
      linewidth: 1
    });
    
    const line = new THREE.Line(geometry, material);
    line.userData = { source, target };
    this.scene.add(line);
    this.connectionLines.push(line);
  },
  
  initForceLayout() {
    // 力导向模拟将在 animate() 中进行
    console.log('[GraphViz] 力导向布局已初始化');
  },
  
  applyForces() {
    const nodes = this.nodeObjects;
    const n = nodes.length;
    
    if (n === 0) return;
    
    // 重置速度
    for (let i = 0; i < n; i++) {
      this.velocities[i].set(0, 0, 0);
    }
    
    // 节点间排斥力
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const posI = this.nodePositions[i];
        const posJ = this.nodePositions[j];
        
        const diff = posI.clone().sub(posJ);
        const dist = diff.length() || 0.1;
        
        // 排斥力（距离越近越强）
        const force = this.forceStrength.repulsion / (dist * dist);
        const forceVec = diff.normalize().multiplyScalar(force);
        
        this.velocities[i].add(forceVec);
        this.velocities[j].sub(forceVec);
      }
    }
    
    // 连接吸引力
    this.graphData.edges.forEach(edge => {
      const sourceIdx = this.nodeObjects.findIndex(n => 
        n.userData.name === edge.source || n.userData.id === edge.source
      );
      const targetIdx = this.nodeObjects.findIndex(n => 
        n.userData.name === edge.target || n.userData.id === edge.target
      );
      
      if (sourceIdx >= 0 && targetIdx >= 0) {
        const posS = this.nodePositions[sourceIdx];
        const posT = this.nodePositions[targetIdx];
        
        const diff = posT.clone().sub(posS);
        const dist = diff.length();
        
        // 吸引力（距离越远越强）
        const force = diff.normalize().multiplyScalar(
          dist * this.forceStrength.attraction
        );
        
        this.velocities[sourceIdx].add(force);
        this.velocities[targetIdx].sub(force);
      }
    });
    
    // 向心力
    const center = new THREE.Vector3(0, 0, 0);
    for (let i = 0; i < n; i++) {
      const toCenter = center.clone().sub(this.nodePositions[i]);
      this.velocities[i].add(toCenter.multiplyScalar(this.forceStrength.centerPull));
    }
    
    // 应用速度（带阻尼）
    for (let i = 0; i < n; i++) {
      // 如果是拖拽的节点，跳过
      if (this.draggedNode === this.nodeObjects[i]) continue;
      
      this.velocities[i].multiplyScalar(this.forceStrength.damping);
      this.nodePositions[i].add(this.velocities[i]);
      
      // 更新节点位置
      this.nodeObjects[i].position.copy(this.nodePositions[i]);
      this.nodeGlows[i].position.copy(this.nodePositions[i]);
    }
    
    // 更新连线
    this.connectionLines.forEach(line => {
      const { source, target } = line.userData;
      const positions = line.geometry.attributes.position.array;
      positions[0] = source.position.x;
      positions[1] = source.position.y;
      positions[2] = source.position.z;
      positions[3] = target.position.x;
      positions[4] = target.position.y;
      positions[5] = target.position.z;
      line.geometry.attributes.position.needsUpdate = true;
    });
  },
  
  setupInteractions() {
    const container = document.getElementById('graph-canvas');
    if (!container) return;
    
    // 鼠标移动
    container.addEventListener('mousemove', (e) => {
      const rect = container.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      
      this.checkHover();
    });
    
    // 鼠标按下
    container.addEventListener('mousedown', (e) => {
      if (this.hoveredNode) {
        this.draggedNode = this.hoveredNode;
        this.controls.enabled = false;
      }
    });
    
    // 鼠标释放
    container.addEventListener('mouseup', () => {
      this.draggedNode = null;
      this.controls.enabled = true;
    });
    
    // 点击
    container.addEventListener('click', (e) => {
      if (this.hoveredNode && this.hoveredNode !== this.selectedNode) {
        this.selectNode(this.hoveredNode);
      } else if (this.selectedNode) {
        this.deselectNode();
      }
    });
    
    // 双击展开
    container.addEventListener('dblclick', () => {
      if (this.hoveredNode) {
        this.expandNode(this.hoveredNode);
      }
    });
  },
  
  checkHover() {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.nodeObjects);
    
    if (intersects.length > 0) {
      const newHovered = intersects[0].object;
      if (newHovered !== this.hoveredNode) {
        this.unhoverNode();
        this.hoveredNode = newHovered;
        this.highlightNode(this.hoveredNode);
      }
      
      // 拖拽
      if (this.draggedNode) {
        const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
        const point = new THREE.Vector3();
        this.raycaster.ray.intersectPlane(plane, point);
        
        const idx = this.nodeObjects.indexOf(this.draggedNode);
        if (idx >= 0) {
          this.nodePositions[idx].copy(point);
          this.draggedNode.position.copy(point);
          this.nodeGlows[idx].position.copy(point);
        }
      }
    } else {
      this.unhoverNode();
    }
  },
  
  highlightNode(node) {
    const idx = this.nodeObjects.indexOf(node);
    if (idx < 0) return;
    
    // 放大光晕
    this.nodeGlows[idx].scale.setScalar(2);
    this.nodeGlows[idx].material.opacity = 0.4;
    
    // 高亮节点
    node.material.emissiveIntensity = 0.8;
    
    // 高亮连接的线
    const nodeId = node.userData.name || node.userData.id;
    this.connectionLines.forEach(line => {
      const { source, target } = line.userData;
      if (source.userData.name === nodeId || source.userData.id === nodeId ||
          target.userData.name === nodeId || target.userData.id === nodeId) {
        line.material.opacity = 0.8;
        line.material.color.setHex(0x00ffff);
      }
    });
    
    // 高亮连接的节点
    this.graphData.edges.forEach(edge => {
      if (edge.source === nodeId || edge.target === nodeId) {
        const connectedId = edge.source === nodeId ? edge.target : edge.source;
        const connectedNode = this.nodeMap[connectedId];
        if (connectedNode) {
          const cIdx = this.nodeObjects.indexOf(connectedNode);
          if (cIdx >= 0) {
            this.nodeGlows[cIdx].scale.setScalar(1.5);
            this.nodeGlows[cIdx].material.opacity = 0.25;
          }
        }
      }
    });
    
    // 显示标签
    this.showLabel(node);
  },
  
  unhoverNode() {
    if (!this.hoveredNode) return;
    
    const idx = this.nodeObjects.indexOf(this.hoveredNode);
    if (idx >= 0) {
      this.nodeGlows[idx].scale.setScalar(1);
      this.nodeGlows[idx].material.opacity = 0.15;
      this.hoveredNode.material.emissiveIntensity = 0.3;
    }
    
    // 恢复连接线
    this.connectionLines.forEach(line => {
      line.material.opacity = 0.2;
      line.material.color.setHex(0x22d3ee);
    });
    
    // 恢复连接节点
    this.nodeGlows.forEach(glow => {
      glow.scale.setScalar(1);
      glow.material.opacity = 0.15;
    });
    
    this.hideLabel();
    this.hoveredNode = null;
  },
  
  selectNode(node) {
    this.selectedNode = node;
    
    // 聚焦相机
    const targetPos = node.position.clone();
    // 平滑移动相机到节点附近
    
    // 显示详情面板
    this.showDetailPanel(node);
  },
  
  deselectNode() {
    this.selectedNode = null;
    this.hideDetailPanel();
  },
  
  expandNode(node) {
    console.log('[GraphViz] 展开节点:', node.userData.label);
    // TODO: 加载更多连接
  },
  
  showLabel(node) {
    let label = document.getElementById('graph-label');
    if (!label) {
      label = document.createElement('div');
      label.id = 'graph-label';
      label.style.cssText = `
        position: fixed;
        padding: 6px 12px;
        background: rgba(10, 14, 39, 0.9);
        border: 1px solid rgba(34, 211, 238, 0.5);
        border-radius: 4px;
        color: #fff;
        font-size: 12px;
        pointer-events: none;
        z-index: 1000;
        white-space: nowrap;
      `;
      document.body.appendChild(label);
    }
    
    label.textContent = node.userData.label;
    label.style.display = 'block';
    
    // 计算屏幕位置
    const vector = node.position.clone();
    vector.project(this.camera);
    
    const container = document.getElementById('graph-canvas');
    const rect = container.getBoundingClientRect();
    
    label.style.left = (rect.left + (vector.x + 1) * rect.width / 2 + 15) + 'px';
    label.style.top = (rect.top + (-vector.y + 1) * rect.height / 2 - 10) + 'px';
  },
  
  hideLabel() {
    const label = document.getElementById('graph-label');
    if (label) label.style.display = 'none';
  },
  
  showDetailPanel(node) {
    let panel = document.getElementById('graph-detail');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'graph-detail';
      panel.style.cssText = `
        position: fixed;
        right: 20px;
        top: 80px;
        width: 280px;
        padding: 16px;
        background: rgba(10, 14, 39, 0.95);
        border: 1px solid rgba(34, 211, 238, 0.3);
        border-radius: 8px;
        color: #fff;
        font-size: 13px;
        z-index: 1000;
      `;
      document.body.appendChild(panel);
    }
    
    const typeColor = {
      'PERSON': '#22d3ee',
      'PROJECT': '#a855f7',
      'FILE': '#10b981',
      'CONCEPT': '#ff8a00',
      'DATE': '#6366f1',
      'ENTITY': '#ec4899',
      'DEFAULT': '#64748b'
    };
    
    const color = typeColor[node.userData.type] || typeColor.DEFAULT;
    
    panel.innerHTML = `
      <div style="margin-bottom: 12px;">
        <span style="color: ${color}; font-weight: 600; font-size: 16px;">
          ${node.userData.label}
        </span>
        <span style="color: #64748b; font-size: 11px; margin-left: 8px;">
          ${node.userData.type}
        </span>
      </div>
      <div style="color: #94a3b8; font-size: 12px; line-height: 1.6;">
        <div>连接数: ${this.getNodeConnections(node)}</div>
      </div>
      <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(100, 116, 139, 0.3);">
        <button onclick="GraphViz.deselectNode()" style="
          background: rgba(34, 211, 238, 0.1);
          border: 1px solid rgba(34, 211, 238, 0.3);
          color: #22d3ee;
          padding: 6px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
        ">关闭</button>
      </div>
    `;
    
    panel.style.display = 'block';
  },
  
  hideDetailPanel() {
    const panel = document.getElementById('graph-detail');
    if (panel) panel.style.display = 'none';
  },
  
  getNodeConnections(node) {
    const nodeId = node.userData.name || node.userData.id;
    return this.graphData.edges.filter(e => 
      e.source === nodeId || e.target === nodeId
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
      0.5,
      0.85
    );
    this.composer.addPass(bloomPass);
  },
  
  onResize() {
    const container = document.getElementById('graph-canvas');
    if (!container || !this.camera || !this.renderer) return;
    
    const width = container.clientWidth || 300;
    const height = container.clientHeight || 280;
    
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  },
  
  animate() {
    this.animationId = requestAnimationFrame(() => this.animate());
    
    this.time += 0.016;
    
    // 更新粒子
    if (this.brainParticles && this.brainParticles.material.uniforms) {
      this.brainParticles.material.uniforms.time.value = this.time;
    }
    
    // 力导向布局
    this.applyForces();
    
    // 节点脉动
    this.nodeObjects.forEach((mesh, i) => {
      const baseScale = mesh === this.hoveredNode ? 1.3 : 1;
      const pulse = Math.sin(this.time * 2 + i * 0.5) * 0.05;
      mesh.scale.setScalar(baseScale + pulse);
    });
    
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
    
    // 清理 DOM 元素
    const label = document.getElementById('graph-label');
    const detail = document.getElementById('graph-detail');
    if (label) label.remove();
    if (detail) detail.remove();
  }
};

// 导出
if (typeof window !== 'undefined') {
  window.GraphViz = GraphViz;
}
