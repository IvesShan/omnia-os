/**
 * Omnia 神经图谱 - porweb 风格
 * 基于 Datadryft/porweb 的视觉风格
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js';
import { EffectComposer } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/postprocessing/UnrealBloomPass.js';

class NeuralGraphPorweb {
  constructor(container) {
    this.container = container;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.composer = null;
    this.controls = null;
    
    // 大脑粒子
    this.brainParticles = null;
    this.brainRef = null;
    
    // 背景粒子
    this.backgroundParticles = null;
    
    // 知识节点
    this.knowledgeNodes = [];
    this.connections = [];
    this.nodeMap = new Map();
    
    // 鼠标跟踪
    this.mouse = new THREE.Vector2();
    this.targetRotation = new THREE.Vector2();
    
    this.time = 0;
    
    this.init();
    this.createBackgroundParticles();
    this.createBrain();
    this.createKnowledgeNodes();
    this.setupPostProcessing();
    this.setupEventListeners();
    this.animate();
  }
  
  init() {
    // 场景 - 深色背景
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0a0f);
    
    // 相机
    const aspect = this.container.clientWidth / this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1000);
    this.camera.position.set(0, 0, 5);
    
    // 渲染器
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.container.appendChild(this.renderer.domElement);
    
    // 控制器 - 不自动旋转，让鼠标控制
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.enableZoom = true;
    this.controls.autoRotate = false;
  }
  
  /**
   * 创建背景粒子 - porweb 风格
   * 5000 个青色粒子缓慢旋转
   */
  createBackgroundParticles() {
    const particleCount = 5000;
    const positions = new Float32Array(particleCount * 3);
    
    // 球形分布，半径 10
    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 8 + Math.random() * 4;
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    
    const material = new THREE.PointsMaterial({
      color: 0x00ffff,
      size: 0.035,
      transparent: true,
      opacity: 0.9,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    
    this.backgroundParticles = new THREE.Points(geometry, material);
    this.backgroundParticles.rotation.set(0, 0, Math.PI / 4);
    this.scene.add(this.backgroundParticles);
  }
  
  /**
   * 创建大脑粒子 - porweb 颜色方案
   * 主要是暗色，只有少量亮橙色高亮
   */
  createBrain() {
    const particleCount = 50000;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    
    // porweb 颜色方案
    const colorSpark = new THREE.Color(0xffc266);      // 火花 0.1%
    const colorHighlight = new THREE.Color(0xff8a00);  // 亮橙色 1%
    const colorDarkOrange = new THREE.Color(0x4a2000); // 深橙色 20%
    const colorVoid = new THREE.Color(0x00151a);       // 暗色 79%
    
    for (let i = 0; i < particleCount; i++) {
      // 球形分布（模拟大脑形状）
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 1.5 + Math.random() * 0.5;
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
      
      // porweb 颜色逻辑
      const randomVal = Math.random();
      let color;
      
      if (randomVal > 0.999) {
        color = colorSpark;        // 火花 0.1%
      } else if (randomVal > 0.99) {
        color = colorHighlight;    // 亮橙色 1%
      } else if (randomVal > 0.8) {
        color = colorDarkOrange;   // 深橙色 19%
      } else {
        color = colorVoid;         // 暗色 80%
      }
      
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }
    
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    
    const material = new THREE.PointsMaterial({
      size: 0.006,  // porweb 的大小
      vertexColors: true,
      transparent: true,
      sizeAttenuation: true,
      depthWrite: false,
    });
    
    this.brainParticles = new THREE.Points(geometry, material);
    this.scene.add(this.brainParticles);
  }
  
  /**
   * 创建知识节点 - 发光点
   */
  async createKnowledgeNodes() {
    try {
      const response = await fetch('http://localhost:8765/api/memory/neural-graph');
      const data = await response.json();
      
      if (!data.nodes || data.nodes.length === 0) {
        console.log('没有节点数据');
        return;
      }
      
      // 创建发光节点
      const nodeGeometry = new THREE.SphereGeometry(0.05, 16, 16);
      const nodeMaterial = new THREE.MeshBasicMaterial({
        color: 0xff8a00,
        transparent: true,
        opacity: 0.9,
      });
      
      // 只显示部分节点（太多会卡）
      const maxNodes = Math.min(data.nodes.length, 50);
      const step = Math.ceil(data.nodes.length / maxNodes);
      
      for (let i = 0; i < data.nodes.length; i += step) {
        const node = data.nodes[i];
        
        // 球面分布
        const theta = (i / data.nodes.length) * Math.PI * 4;
        const phi = Math.acos((i / data.nodes.length) * 2 - 1);
        const radius = 1.2 + Math.random() * 0.3;
        
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.sin(phi) * Math.sin(theta);
        const z = radius * Math.cos(phi);
        
        const mesh = new THREE.Mesh(nodeGeometry, nodeMaterial.clone());
        mesh.position.set(x, y, z);
        mesh.userData = { id: node.id, label: node.label, type: node.type };
        
        this.knowledgeNodes.push(mesh);
        this.nodeMap.set(node.id, mesh);
        this.scene.add(mesh);
      }
      
      // 创建连接线
      this.createConnections(data.links);
      
    } catch (error) {
      console.error('加载节点失败:', error);
    }
  }
  
  createConnections(links) {
    const maxLinks = Math.min(links.length, 100);
    
    for (let i = 0; i < maxLinks; i++) {
      const link = links[i];
      const sourceNode = this.nodeMap.get(link.source);
      const targetNode = this.nodeMap.get(link.target);
      
      if (sourceNode && targetNode) {
        const points = [
          sourceNode.position.clone(),
          targetNode.position.clone()
        ];
        
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
          color: 0x00ffff,
          transparent: true,
          opacity: 0.3,
        });
        
        const line = new THREE.Line(geometry, material);
        this.connections.push(line);
        this.scene.add(line);
      }
    }
  }
  
  setupPostProcessing() {
    this.composer = new EffectComposer(this.renderer);
    
    const renderPass = new RenderPass(this.scene, this.camera);
    this.composer.addPass(renderPass);
    
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(this.container.clientWidth, this.container.clientHeight),
      0.5,  // 强度
      0.4,  // 半径
      0.85  // 阈值
    );
    this.composer.addPass(bloomPass);
  }
  
  setupEventListeners() {
    // 鼠标移动跟踪
    window.addEventListener('mousemove', (event) => {
      this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    });
    
    // 窗口大小调整
    window.addEventListener('resize', () => {
      const width = this.container.clientWidth;
      const height = this.container.clientHeight;
      
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      
      this.renderer.setSize(width, height);
      this.composer.setSize(width, height);
    });
  }
  
  animate() {
    requestAnimationFrame(() => this.animate());
    
    this.time += 0.016;
    
    // 背景粒子旋转
    if (this.backgroundParticles) {
      this.backgroundParticles.rotation.x -= 0.016 / 30;
      this.backgroundParticles.rotation.y -= 0.016 / 35;
    }
    
    // 大脑粒子 - porweb 风格的鼠标跟踪和脉冲
    if (this.brainParticles) {
      // 鼠标跟踪旋转
      const sensitivity = 0.5;
      const lerpFactor = 0.1;
      
      const targetX = this.mouse.y * sensitivity;
      const targetY = this.mouse.x * sensitivity + (this.time / 20);
      
      this.brainParticles.rotation.x = THREE.MathUtils.lerp(
        this.brainParticles.rotation.x, 
        targetX, 
        lerpFactor
      );
      this.brainParticles.rotation.y = THREE.MathUtils.lerp(
        this.brainParticles.rotation.y, 
        targetY, 
        lerpFactor
      );
      
      // 脉冲效果
      const pulse = 1.8 + Math.sin(this.time * 2) * 0.02;
      this.brainParticles.scale.set(pulse, pulse, pulse);
    }
    
    this.controls.update();
    this.composer.render();
  }
}

// 导出
window.NeuralGraphPorweb = NeuralGraphPorweb;
