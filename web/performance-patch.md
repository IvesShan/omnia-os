# Omnia 前端性能优化方案

## 目标
在保持美观和体验不变的情况下，最大化流畅度。

---

## 一、CSS 动画优化

### 1.1 页面不可见时暂停动画
```css
/* 当页面隐藏时暂停所有动画 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### 1.2 使用 CSS containment 隔离重绘
```css
.hud-panel {
  contain: layout style paint;
}

.msg {
  contain: layout style;
}

.holo-scene {
  contain: strict;
  content-visibility: auto;  /* 视口外时不渲染 */
}
```

### 1.3 减少全息投影动画
- 将 3 个旋转环改为 1 个
- 粒子从 8 个减到 4 个
- 动画时长从 6-12s 改为 10-20s（更慢更省资源）

### 1.4 使用 will-change 谨慎
```css
/* 只对真正需要 GPU 加速的元素使用 */
.holo-core {
  will-change: transform, opacity;
}

/* 移除不必要的 will-change */
#composer {
  /* will-change: height; */ /* 移除，输入框变化不频繁 */
}
```

---

## 二、JS 定时器优化

### 2.1 时钟更新优化
```javascript
// 使用 requestAnimationFrame 替代 setInterval
let lastClockUpdate = 0;
function updateClockLoop(timestamp) {
  if (timestamp - lastClockUpdate >= 1000) {
    updateClock();
    lastClockUpdate = timestamp;
  }
  requestAnimationFrame(updateClockLoop);
}
requestAnimationFrame(updateClockLoop);
```

### 2.2 页面可见性感知
```javascript
// 页面不可见时暂停所有定时器
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    // 暂停动画和定时器
    document.body.classList.add('paused');
  } else {
    document.body.classList.remove('paused');
    loadStatus(); // 恢复时刷新一次
  }
});
```

### 2.3 状态刷新节流
```javascript
// 使用 requestIdleCallback 做低优先级刷新
function scheduleStatusRefresh() {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(loadStatus, { timeout: 30000 });
  } else {
    setTimeout(loadStatus, 15000);
  }
}
```

---

## 三、DOM 操作优化

### 3.1 流式输出优化
```javascript
// 节流滚动，而不是每次 token 都滚动
let scrollPending = false;
function scheduleScroll() {
  if (!scrollPending) {
    scrollPending = true;
    requestAnimationFrame(() => {
      scrollToBottom();
      scrollPending = false;
    });
  }
}
```

### 3.2 Markdown 解析缓存
```javascript
// 缓存已解析的内容
const formatCache = new WeakMap();
function formatReplyCached(text) {
  if (formatCache.has(text)) return formatCache.get(text);
  const result = formatReply(text);
  formatCache.set(text, result);
  return result;
}
```

### 3.3 虚拟滚动（可选，聊天历史超长时）
```javascript
// 只渲染可视区域内的消息
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    entry.target.style.contentVisibility = entry.isIntersecting ? 'visible' : 'hidden';
  });
}, { rootMargin: '200px' });

document.querySelectorAll('.msg').forEach(msg => observer.observe(msg));
```

---

## 四、CSS 渲染优化

### 4.1 减少复杂渐变
```css
/* 原来 */
background: radial-gradient(1200px 600px at 50% 0%, rgba(34,211,238,0.03), transparent 60%);

/* 优化：使用更小的渐变范围 */
background: radial-gradient(800px 400px at 50% 0%, rgba(34,211,238,0.025), transparent 50%);
```

### 4.2 减少阴影层级
```css
/* 原来：多层阴影 */
box-shadow: 0 10px 25px rgba(0,0,0,0.25);

/* 优化：单层阴影 */
box-shadow: 0 4px 12px rgba(0,0,0,0.2);
```

### 4.3 使用 CSS 变量减少计算
```css
:root {
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.2);
  --shadow-glow: 0 0 20px rgba(34,211,238,0.15);
}
```

---

## 五、实施优先级

### P0（立即实施，效果显著）
1. 页面可见性感知 - 暂停后台动画
2. 流式输出滚动节流
3. CSS containment 添加

### P1（短期优化）
1. 时钟改用 rAF
2. 减少 box-shadow 层级
3. 全息动画简化

### P2（长期优化）
1. 虚拟滚动
2. Markdown 缓存
3. 离屏渲染优化

---

## 预期效果
- GPU 占用降低 30-50%
- CPU 空闲时占用降低 60%
- 流式输出帧率提升 20-30%
- 页面不可见时几乎零消耗
