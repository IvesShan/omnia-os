/**
 * Omnia 全息大脑可视化 - Three.js
 * 灵感来自 porweb 项目
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

class BrainVisualization {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('[BrainViz] 容器未找到');
            return;
        }
        
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.composer = null;
        this.controls = null;
        this.particles = null;
        this.nodes = [];
        this.edges = [];
        this.brainGroup = null;
        this.time = 0;
        
        this.init();
    }
    
    init() {
        console.log('[BrainViz] 初始化全息大脑...');
        
        // 场景
        this.scene = new THREE.Scene();
        // 移除背景色，使用透明背景
        // this.scene.background = new THREE.Color(0x0a0a1a);
        this.scene.fog = new THREE.FogExp2(0x0a0a1a, 0.02);
        
        // 相机
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
        this.camera.position.set(0, 0, 50);
        
        // 渲染器
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true  // 透明背景
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.5;
        this.container.appendChild(this.renderer.domElement);
        
        // 后期处理 - Bloom 发光效果
        this.composer = new EffectComposer(this.renderer);
        const renderPass = new RenderPass(this.scene, this.camera);
        this.composer.addPass(renderPass);
        
        const bloomPass = new UnrealBloomPass(
            new THREE.Vector2(width, height),
            1.5,  // strength
            0.4,  // radius
            0.85  // threshold
        );
        this.composer.addPass(bloomPass);
        
        // 控制器
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.autoRotate = true;
        this.controls.autoRotateSpeed = 1.0;  // 提高自动旋转速度
        this.controls.minDistance = 20;
        this.controls.maxDistance = 100;
        this.controls.enablePan = true;
        this.controls.enableZoom = true;
        
        // 创建大脑
        this.createBrain();
        
        // 创建粒子
        this.createParticles();
        
        // 创建光源
        this.createLights();
        
        // 加载数据
        this.loadGraphData();
        
        // 窗口调整
        window.addEventListener('resize', () => this.onResize());
        
        // 开始动画
        this.animate();
        
        console.log('[BrainViz] 初始化完成');
    }
    
    createBrain() {
        this.brainGroup = new THREE.Group();
        
        // 大脑轮廓 - 使用多个球体模拟
        const brainGeometry = new THREE.IcosahedronGeometry(15, 3);
        const brainMaterial = new THREE.MeshPhongMaterial({
            color: 0x1e293b,
            transparent: true,
            opacity: 0.3,
            wireframe: true
        });
        const brainMesh = new THREE.Mesh(brainGeometry, brainMaterial);
        this.brainGroup.add(brainMesh);
        
        // 添加发光内核
        const coreGeometry = new THREE.IcosahedronGeometry(8, 2);
        const coreMaterial = new THREE.MeshBasicMaterial({
            color: 0x22d3ee,
            transparent: true,
            opacity: 0.2
        });
        const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
        this.brainGroup.add(coreMesh);
        
        this.scene.add(this.brainGroup);
    }
    
    createParticles() {
        // 创建粒子系统
        const particleCount = 2000;
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);
        
        for (let i = 0; i < particleCount; i++) {
            // 球形分布
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            const radius = 15 + Math.random() * 10;
            
            positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            positions[i * 3 + 2] = radius * Math.cos(phi);
            
            // 颜色渐变
            const color = new THREE.Color();
            color.setHSL(0.5 + Math.random() * 0.2, 0.8, 0.6);
            colors[i * 3] = color.r;
            colors[i * 3 + 1] = color.g;
            colors[i * 3 + 2] = color.b;
        }
        
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        
        const material = new THREE.PointsMaterial({
            size: 0.5,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });
        
        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }
    
    createLights() {
        // 环境光
        const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
        this.scene.add(ambientLight);
        
        // 点光源
        const pointLight1 = new THREE.PointLight(0x22d3ee, 1, 100);
        pointLight1.position.set(20, 20, 20);
        this.scene.add(pointLight1);
        
        const pointLight2 = new THREE.PointLight(0xa855f7, 1, 100);
        pointLight2.position.set(-20, -20, 20);
        this.scene.add(pointLight2);
    }
    
    async loadGraphData() {
        try {
            const response = await fetch('/api/graph?limit=50');
            const data = await response.json();
            
            if (!data || !data.nodes) return;
            
            // 创建节点
            data.nodes.forEach((node, i) => {
                const geometry = new THREE.SphereGeometry(0.5, 16, 16);
                const material = new THREE.MeshBasicMaterial({
                    color: this.getTypeColor(node.type),
                    transparent: true,
                    opacity: 0.8
                });
                const mesh = new THREE.Mesh(geometry, material);
                
                // 随机位置
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                const radius = 12 + Math.random() * 8;
                
                mesh.position.x = radius * Math.sin(phi) * Math.cos(theta);
                mesh.position.y = radius * Math.sin(phi) * Math.sin(theta);
                mesh.position.z = radius * Math.cos(phi);
                
                this.scene.add(mesh);
                this.nodes.push(mesh);
            });
            
            console.log(`[BrainViz] 加载了 ${this.nodes.length} 个节点`);
        } catch (error) {
            console.error('[BrainViz] 加载数据失败:', error);
        }
    }
    
    getTypeColor(type) {
        const colors = {
            'PERSON': 0x22d3ee,
            'PROJECT': 0xa855f7,
            'FILE': 0x10b981,
            'CONCEPT': 0xf59e0b,
            'EVENT': 0xef4444
        };
        return colors[type] || 0x6366f1;
    }
    
    onResize() {
        if (!this.container) return;
        
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        this.renderer.setSize(width, height);
        this.composer.setSize(width, height);
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        this.time += 0.01;
        
        // 移除大脑自动旋转（使用 OrbitControls 的 autoRotate）
        // if (this.brainGroup) {
        //     this.brainGroup.rotation.y += 0.002;
        // }
        
        // 粒子动画 - 移除上下摆动
        if (this.particles) {
            // 移除上下摆动效果
            // const positions = this.particles.geometry.attributes.position.array;
            // for (let i = 0; i < positions.length; i += 3) {
            //     positions[i + 1] += Math.sin(this.time + i) * 0.01;
            // }
            // this.particles.geometry.attributes.position.needsUpdate = true;
            
            // 保持缓慢旋转
            this.particles.rotation.y += 0.0005;
        }
        
        // 节点脉动
        this.nodes.forEach((node, i) => {
            const scale = 1 + Math.sin(this.time * 2 + i) * 0.1;
            node.scale.setScalar(scale);
        });
        
        this.controls.update();
        this.composer.render();
    }
    
    destroy() {
        if (this.renderer) {
            this.renderer.dispose();
        }
        if (this.container && this.renderer.domElement) {
            this.container.removeChild(this.renderer.domElement);
        }
    }
}

// 导出
window.BrainVisualization = BrainVisualization;

// 自动初始化
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('brain-container');
    if (container) {
        window.brainViz = new BrainVisualization('brain-container');
    }
});
