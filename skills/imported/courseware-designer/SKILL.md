# Courseware Designer Skill - 课件设计专家

## 概述

本 Skill 封装了专业课件/演示文稿设计的最佳实践，基于 Apple Keynote + Stripe 风格，适用于技术课程、培训课件、产品演示等场景。

## 适用场景

- 开发培训课程课件（HTML格式）
- 设计产品演示文稿
- 制作技术分享幻灯片
- 创建企业介绍/宣传材料

## 核心能力

### 1. 设计系统规范

#### 色彩系统
```css
:root {
  /* 背景色层级 */
  --bg-primary: #000000;           /* 主背景 - 纯黑 */
  --bg-secondary: #1a1a2e;         /* 次级背景 - 深蓝黑 */
  --bg-tertiary: #1c1c1e;          /* 第三级背景 */
  --bg-elevated: #2c2c3a;          /* 提升背景 - 卡片等 */
  --bg-hover: rgba(255, 255, 255, 0.05);
  
  /* 文字色层级 */
  --text-primary: #ffffff;                    /* 主文字 - 纯白 */
  --text-secondary: rgba(255, 255, 255, 0.9); /* 次级文字 */
  --text-tertiary: rgba(255, 255, 255, 0.7);  /* 第三级文字 */
  --text-muted: rgba(255, 255, 255, 0.5);     /* 辅助文字 */
  
  /* 强调色 - 科技感 */
  --accent-blue: #0a84ff;          /* 科技蓝 - 信息、链接 */
  --accent-green: #30d158;         /* 绿色 - 成功、实操 */
  --accent-purple: #bf5af2;        /* 紫色 - 专业、高端 */
  --accent-orange: #ff9f0a;        /* 橙色 - 警告、注意 */
  --accent-red: #ff453a;           /* 红色 - 危险、错误 */
}
```

#### 字体系统
```css
:root {
  --font-primary: 'Inter', -apple-system, sans-serif;
  
  /* 字体规格 */
  --text-xs: 13px;      /* 标签、章节标记 */
  --text-sm: 15px;      /* 辅助文字 */
  --text-base: 17px;    /* 基础文字 */
  --text-lg: 20px;      /* 大正文 */
  --text-xl: 24px;      /* 小标题 */
  --text-2xl: 32px;     /* 副标题 */
  --text-3xl: 48px;     /* 中标题 */
  --text-4xl: 56px;     /* 大标题 */
  --text-5xl: 72px;     /* 超大标题 */
  --text-6xl: 80px;     /* 巨型标题 - 封面 */
  
  /* 字重 */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  
  /* 行高 */
  --leading-tight: 1.2;
  --leading-normal: 1.6;
}
```

#### 间距系统
```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  --space-24: 96px;
  
  /* 页面边距 */
  --page-padding-x: 80px;
  --page-padding-y: 60px;
  
  /* 内容最大宽度 */
  --content-max-width: 1200px;
  
  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}
```

### 2. 布局原则

#### 幻灯片结构
```
每页幻灯片结构:
├── 章节标签 (13px, uppercase, 蓝色)
├── 大标题 (48-80px, bold)
├── 副标题/正文 (20-24px)
└── 内容区 (卡片/表格/列表)
```

#### 网格系统
- 12列网格
- 边距：80px（桌面）/ 40px（平板）/ 20px（手机）
- 列间距：24px

#### 内容类型
1. **封面页**: 全屏深色背景 + 超大标题居中
2. **目录页**: 阶段卡片 + 时间标注
3. **内容页**: 左右分栏 或 上下结构
4. **表格页**: 数据对比表格
5. **总结页**: 要点列表 + 强调色标注

### 3. 技术实现规范

#### HTML基础结构
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>课件标题</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* 设计系统变量 */
        :root {
            /* 色彩、字体、间距变量 */
        }
        
        /* 基础样式 */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100%; overflow: hidden; }
        
        /* 幻灯片容器 */
        .slides-container { /* 全屏容器 */ }
        
        /* 单页幻灯片 */
        .slide { /* 绝对定位，全屏 */ }
        .slide.active { opacity: 1; visibility: visible; }
        
        /* 进度条、页码、导航提示 */
        .progress-bar { /* 底部蓝色进度条 */ }
        .page-number { /* 右下角页码 */ }
        .nav-hint { /* 底部导航提示 */ }
    </style>
</head>
<body>
    <!-- 进度条 -->
    <div class="progress-bar" id="progressBar"></div>
    
    <!-- 页码 -->
    <div class="page-number" id="pageNumber">1 / 12</div>
    
    <!-- Logo -->
    <img src="logo.svg" alt="Logo" class="logo">
    
    <!-- 幻灯片容器 -->
    <div class="slides-container" id="slidesContainer">
        <!-- 各页幻灯片 -->
    </div>
    
    <!-- 交互脚本 -->
    <script>
        // 幻灯片控制逻辑
    </script>
</body>
</html>
```

#### 交互功能
```javascript
// 键盘控制
document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
    else if (e.key === 'ArrowLeft') prevSlide();
});

// 触摸滑动
let touchStartX = 0;
document.addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
});
document.addEventListener('touchend', (e) => {
    const diff = touchStartX - e.changedTouches[0].screenX;
    if (Math.abs(diff) > 50) diff > 0 ? nextSlide() : prevSlide();
});

// 点击区域翻页
document.addEventListener('click', (e) => {
    const screenWidth = window.innerWidth;
    if (e.clientX > screenWidth * 0.66) nextSlide();
    else if (e.clientX < screenWidth * 0.33) prevSlide();
});
```

### 4. 组件库

#### 章节标签
```html
<div class="section-label">Day 01 · 第一阶段</div>
```
```css
.section-label {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent-blue);
    margin-bottom: 24px;
}
```

#### 卡片组件
```html
<div class="card">
    <h3>卡片标题</h3>
    <p>卡片内容</p>
</div>
```
```css
.card {
    background: var(--bg-tertiary);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid var(--border-secondary);
}
```

#### 卡片网格
```html
<div class="card-grid">
    <div class="card">...</div>
    <div class="card">...</div>
</div>
```
```css
.card-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
}
```

#### 表格组件
```html
<table class="price-table">
    <thead>...</thead>
    <tbody>...</tbody>
</table>
```

#### 引用框
```html
<div class="quote-box">
    "引用内容"
</div>
```
```css
.quote-box {
    background: var(--bg-secondary);
    border-left: 4px solid var(--accent-blue);
    padding: 24px 32px;
    font-style: italic;
}
```

### 5. 响应式适配

```css
@media (max-width: 1024px) {
    .slide { padding: 48px; }
    .title-xl { font-size: 56px; }
    .card-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
    .slide { padding: 24px; }
    .title-xl { font-size: 40px; }
}
```

## 使用示例

### 示例1：创建课程课件

**用户需求**: 帮我设计一个Day 02基础拆装入门的课件

**应用本Skill**:
1. 确定课件结构（封面→目标→工具→实操→总结）
2. 应用设计系统（深色主题、Inter字体、卡片布局）
3. 实现交互功能（键盘/触摸/点击翻页）
4. 添加进度条和页码

**输出**: 完整的HTML课件文件

### 示例2：设计宣传海报

**用户需求**: 设计一个课程宣传海报

**应用本Skill**:
1. 扩大页面尺寸（800px宽度，适合打印/分享）
2. 使用渐变背景 + 发光效果
3. 突出关键数据（大字号数字）
4. 四阶段卡片布局
5. 添加联系方式和二维码区域

**输出**: 高清PNG海报

### 示例3：优化现有课件

**用户需求**: 优化这个课件的视觉效果

**应用本Skill**:
1. 检查色彩系统是否统一
2. 优化字体层级（标题/正文大小对比）
3. 增加卡片阴影和悬停效果
4. 统一间距和圆角
5. 添加进度条和页码

## 设计检查清单

创建课件后，检查以下项目：

- [ ] 使用深色主题（#000000背景）
- [ ] Inter字体已加载
- [ ] 色彩系统统一（蓝/绿/紫/橙/红）
- [ ] 字体层级清晰（80px标题→20px正文）
- [ ] 间距一致（24px卡片间距，80px页面边距）
- [ ] 交互功能完整（键盘/触摸/点击）
- [ ] 进度条和页码正常显示
- [ ] Logo位置正确（右上角120px）
- [ ] 响应式适配（手机/平板/桌面）
- [ ] 无emoji（使用方括号文字替代）

## 注意事项

1. **避免使用emoji**: 某些系统显示为灰色方块，使用 `[ 文字 ]` 替代
2. **图片路径**: 使用相对路径，确保课件可移植
3. **字体加载**: 确保Google Fonts链接可用
4. **性能优化**: 避免过多动画，保持流畅
5. **兼容性**: 测试Chrome/Firefox/Safari

## 相关文件

- 设计系统: `design-tokens.css`
- 示例课件: `day01/课件.html`
- 宣传海报: `宣传海报_课程大纲.html`

---

*Skill Version: 1.0.0*  
*Created: 2026-03-19*  
*Based on: Apple Keynote + Stripe design system*
