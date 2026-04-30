---
name: scroll-animation-2026
description: 2026年滚动驱动动画(Scroll-driven Animation)完整指南 - 技术栈、库选型、代码模板、行业案例
tags: [web, animation, scroll, 3d, frontend, design, scrollytelling]
created: 2026-04-30
version: 1.0.0
---

# 滚动驱动动画 (Scroll-driven Animation) 2026

## 术语速查

| 术语 | 含义 |
|------|------|
| **Scroll-scrubbing** | 滚动位置直接控制动画帧，像拖动视频进度条 |
| **Scroll-driven Animation** | CSS 官方术语，2024 年正式进入 CSS 规范 |
| **Scrollytelling** | 用滚动来"讲故事"的设计模式（纽约时报、苹果官网最爱用） |
| **Parallax 3D** | 多层 3D 元素随滚动以不同速度移动 |
| **Pin & Scrub** | 元素固定在视口中，动画随滚动播放 |

## 核心技术栈总览

### 🏆 底层引擎库

| 库 | Stars | 定位 | GitHub |
|:---|:-----:|:-----|:-------|
| **Three.js** | 112K+ | Web 3D 渲染引擎，一切 3D 网页效果的基础 | `mrdoob/three.js` |
| **Motion** (原 Framer Motion) | 31K+ | React/JS 动画库，声明式 API，scroll 动画首选 | `motiondivision/motion` |
| **React Three Fiber** | 30K+ | Three.js 的 React 封装，写 3D 就像写组件 | `pmndrs/react-three-fiber` |
| **GSAP** | 24K+ | 业界最强 JS 动画引擎，ScrollTrigger 是滚动画的黄金标准 | `greensock/GSAP` |
| **Lenis** | 13K+ | 2025-2026 最火的平滑滚动库，替代 Locomotive Scroll | `darkroomengineering/lenis` |
| **Locomotive Scroll** | 8K+ | 经典平滑滚动 + 视差，Lenis 出现前的主流选择 | `locomotivemtl/locomotive-scroll` |

### 🎯 2026 年三大主流技术组合

#### 组合一：苹果官网风格（行业标准）
```
Lenis（平滑滚动）+ GSAP ScrollTrigger（动画控制）+ Three.js（3D 模型）
```
- 适用：产品展示、品牌官网、3D 交互
- 代表：Apple 产品页、Airbnb 年度回顾
- Demo：`adrianhajdin/gsap_macbook_landing` ⭐176

#### 组合二：React 全家桶
```
Next.js + Motion (Framer Motion) + React Three Fiber
```
- 适用：React 项目、SaaS 官网、作品集
- 代表：`codebucks27/wibe-studio` ⭐242，`barvian/musee` ⭐199

#### 组合三：纯 CSS 原生方案（新兴，轻量场景首选）
```
CSS scroll-timeline + scroll-driven animations（无需 JS）
```
- 适用：简单视差、进度指示器、轻量动画
- 代表：`bramus/scroll-driven-animations-debugger-extension` ⭐57

## 热门 Demo / 模板项目

### 高星参考项目

| 项目 | Stars | 技术栈 | 描述 |
|:-----|:-----:|:-------|:-----|
| `DavidHDev/react-bits` | 38K+ | React | 开源动画组件合集，大量 scroll 效果 |
| `fireship-io/threejs-scroll-animation-demo` | 1.6K | Three.js | 3D 滚动作品集网站教程 |
| `adrianhajdin/jsm_gta_vi_landing` | 175 | React + GSAP | GTA VI 风格的电影级滚动网页 |
| `adrianhajdin/gsap_macbook_landing` | 176 | React + Three.js + GSAP | 苹果 MacBook 风格 3D 滚动 |
| `codrops/OnScrollColumnsRows` | 117 | GSAP | Codrops 出品的滚动列/行动画 |
| `codebucks27/3D-Landing-page-for-Apple-iPhone` | 106 | React + Three.js | iPhone 风格 3D 滚动落地页 |
| `giksaw/valentines2026` | 12 | 3D + Scroll | 电影级 3D 滚动网站 |
| `mirayatech/mochi-motion` | 104 | JS | 专注 scroll 动画的轻量库 |

## 代码模板

### 模板 1：Lenis + GSAP ScrollTrigger（最常用）

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    .section { height: 100vh; display: flex; align-items: center; justify-content: center; }
    .box { width: 200px; height: 200px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 16px; }
    .spacer { height: 50vh; }
  </style>
</head>
<body>
  <div class="spacer"></div>
  <div class="section">
    <div class="box" id="animated-box"></div>
  </div>
  <div class="spacer"></div>

  <!-- Lenis 平滑滚动 -->
  <script src="https://unpkg.com/lenis@latest/dist/lenis.min.js"></script>
  <!-- GSAP + ScrollTrigger -->
  <script src="https://unpkg.com/gsap@3/dist/gsap.min.js"></script>
  <script src="https://unpkg.com/gsap@3/dist/ScrollTrigger.min.js"></script>

  <script>
    // 初始化 Lenis
    const lenis = new Lenis();
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((time) => lenis.raf(time * 1000));
    gsap.ticker.lagSmoothing(0);

    // 滚动动画
    gsap.to('#animated-box', {
      rotation: 360,
      scale: 1.5,
      borderRadius: '50%',
      scrollTrigger: {
        trigger: '#animated-box',
        start: 'top center',
        end: 'bottom center',
        scrub: true,  // 关键：scrub: true 让动画跟随滚动
      }
    });
  </script>
</body>
</html>
```

### 模板 2：Three.js 3D 模型滚动控制

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// 场景设置
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('canvas-container').appendChild(renderer.domElement);

// 加载 3D 模型
const loader = new GLTFLoader();
let model;
loader.load('/model.glb', (gltf) => {
  model = gltf.scene;
  scene.add(model);

  // 滚动控制模型旋转
  gsap.to(model.rotation, {
    y: Math.PI * 2,      // 旋转一圈
    x: Math.PI * 0.5,    // 倾斜
    scrollTrigger: {
      trigger: '#canvas-container',
      start: 'top top',
      end: 'bottom bottom',
      scrub: 1,           // 1秒延迟跟随，更丝滑
      pin: true,          // 固定在视口中
    }
  });
});

// 渲染循环
function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
```

### 模板 3：CSS 原生 scroll-timeline（零 JS）

```css
/* 定义滚动时间线 */
@keyframes fade-slide-up {
  from { opacity: 0; transform: translateY(100px); }
  to   { opacity: 1; transform: translateY(0); }
}

.scroll-reveal {
  animation: fade-slide-up linear both;
  animation-timeline: view();          /* 基于元素进入视口 */
  animation-range: entry 0% entry 100%; /* 进入时播放 */
}

/* 进度条 */
.progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea, #764ba2);
  width: 100%;
  transform-origin: left;
  animation: grow-progress linear;
  animation-timeline: scroll();        /* 基于页面滚动 */
}

@keyframes grow-progress {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}
```

## 设计模式

### 1. Pin & Scrub（固定 + 擦除）
元素固定在视口中，动画随滚动播放。
```
应用场景：产品 360° 旋转、步骤讲解、数据可视化
```

### 2. Parallax Layers（视差分层）
不同层以不同速度滚动，产生深度感。
```
应用场景：首页 Hero、背景装饰、图片展
```

### 3. Scroll-triggered Sequence（滚动触发序列）
滚动到特定位置触发一组动画。
```
应用场景：数字计数器、图标入场、文字打字机
```

### 4. Horizontal Scroll（水平滚动）
垂直滚动映射为水平移动。
```
应用场景：时间线、作品集、图片画廊
```

### 5. 3D Scene Scrub（3D 场景擦除）
滚动控制 Three.js 场景的相机或模型。
```
应用场景：产品展示、建筑漫游、虚拟展厅
```

## 2024-2026 技术演变

```
Locomotive Scroll → Lenis（更轻、更快、维护活跃）
Framer Motion     → Motion（去 React 化，支持纯 JS/Vue/Svelte）
GSAP ScrollTrigger → 依然是复杂场景的王者，无替代品
CSS scroll-timeline → 原生方案崛起，简单场景不再需要 JS
Three.js + Scroll   → 苹果/产品展示的标配，R3F 降低 React 门槛
```

## 性能优化清单

- [ ] 使用 `will-change: transform` 提示浏览器（仅在动画元素上）
- [ ] 动画只用 `transform` 和 `opacity`，避免触发 layout
- [ ] Lenis 的 `lerp` 值调低（0.05-0.1）让滚动更丝滑
- [ ] Three.js 场景用 `requestAnimationFrame` 按需渲染
- [ ] 大图用 `loading="lazy"` 或 Intersection Observer 懒加载
- [ ] 移动端降低 Three.js 的 `pixelRatio`（1.5 足够）
- [ ] GSAP 的 `scrub: 1` 比 `scrub: true` 更丝滑（有 1 秒延迟跟随）
- [ ] 用 Chrome DevTools → Performance 面板检查帧率，目标 60fps

## 常见坑

| 坑 | 解决方案 |
|:---|:---------|
| Lenis 和 GSAP ScrollTrigger 冲突 | 必须在 lenis.on('scroll') 里调用 ScrollTrigger.update |
| Three.js 模型加载后白屏 | 检查 camera 位置、灯光、模型 scale |
| 移动端滚动卡顿 | 降低 Three.js 复杂度，用 Lenis 的 touch multiplier |
| CSS scroll-timeline 浏览器兼容 | 2025 年后主流浏览器已支持，但 Safari 需要 18+ |
| scrub 动画不生效 | 确认 trigger 元素有足够的滚动空间（start/end 距离够大） |

## 学习资源

- GSAP ScrollTrigger 文档: https://gsap.com/docs/v3/Plugins/ScrollTrigger/
- Lenis GitHub: https://github.com/darkroomengineering/lenis
- Three.js Journey (Bruno Simon): https://threejs-journey.com
- CSS Scroll-driven Animations: https://developer.chrome.com/docs/css-ui/scroll-driven-animations
- Codrops (Tympanus): https://tympanus.net/codrops/
- Adrian Hajdin YouTube: 大量 scroll animation 教程
- Lottie + Scroll: https://lottiefiles.com

---

**更新日期**: 2026-04-30
**版本**: 1.0.0
**数据来源**: GitHub Stars、npm trends、行业案例研究
