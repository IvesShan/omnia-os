# Omnia Feature Showcase

基于 HyperFrames 框架创建的 Omnia AI 助手功能介绍视频。

## 🎬 项目概述

这是一个 90 秒的功能展示视频，展示了 Omnia AI 助手的核心特性：

### 视频结构（8 个场景）

| 场景 | 时间 | 内容 |
|------|------|------|
| 1. Hook | 0-3s | "你有没有想过，如果 AI 能记住你说过的每一句话？" |
| 2. Intro | 3-8s | 介绍 Omnia - 有记忆的 AI 助手 |
| 3. Memory Palace | 8-20s | 记忆宫殿功能展示 |
| 4. Neural Graph | 20-32s | 神经图谱功能展示 |
| 5. Tools | 32-44s | 工具调用功能展示 |
| 6. Streaming | 44-50s | 流式对话功能展示 |
| 7. Multi-turn | 50-58s | 多轮对话功能展示 |
| 8. CTA | 58-65s | 号召行动 - "立即体验" |

## 🛠️ 技术栈

- **框架**: HyperFrames v0.6.55
- **动画**: GSAP 3.14.2
- **字体**: Inter + Noto Sans SC (本地托管)
- **渲染**: 1920×1080, 30fps, 标准质量

## 📁 项目结构

```
omnia-feature-showcase/
├── index.html                    # 主入口文件
├── hyperframes.json             # HyperFrames 配置
├── meta.json                    # 项目元数据
├── package.json                 # 项目依赖
├── compositions/                # 场景组件
│   ├── scene-hook.html         # Hook 场景
│   ├── scene-intro.html        # Intro 场景
│   ├── scene-memory.html       # 记忆宫殿场景
│   ├── scene-graph.html        # 神经图谱场景
│   ├── scene-tools.html        # 工具调用场景
│   ├── scene-streaming.html    # 流式对话场景
│   ├── scene-multiturn.html    # 多轮对话场景
│   └── scene-cta.html          # CTA 场景
├── assets/
│   └── fonts/                  # 本地字体文件
│       ├── inter-latin.woff2
│       ├── noto-sans-sc.woff2
│       └── fonts.css
└── out/                        # 输出目录
    └── omnia-showcase.mp4      # 渲染完成的视频 (4.0 MB)
```

## 🚀 使用方法

### 预览

```bash
cd /home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase
hyperframes preview
# 访问 http://localhost:8080
```

### 渲染视频

```bash
hyperframes render --output out/omnia-showcase.mp4 --quality standard
```

### 发布到 HyperFrames

```bash
hyperframes publish
```

## 🎨 设计特点

### 视觉风格
- **深色主题**: 专业的科技感
- **渐变色彩**: 青色 (#00d4ff) + 紫色 (#8b5cf6)
- **毛玻璃效果**: 现代感十足
- **流畅动画**: GSAP 驱动的丝滑过渡

### 动画效果
- **Hook**: 文字打字机效果，光标闪烁
- **Intro**: Logo 脉冲动画，特性卡片滑入
- **Memory**: 记忆节点连线动画，数据统计弹出
- **Graph**: 神经网络节点脉冲，连线渐现
- **Tools**: 工具卡片依次出现，hover 效果
- **Streaming**: 流式文字逐字显示
- **Multi-turn**: 对话历史滚动出现
- **CTA**: 渐变背景浮动，按钮脉冲

## 📊 渲染结果

- **文件大小**: 4.0 MB
- **时长**: 60 秒
- **格式**: MP4 (H.264)
- **分辨率**: 1920×1080
- **帧率**: 30fps

## 🔧 自定义修改

### 修改文案

编辑 `compositions/` 目录下的各个场景 HTML 文件，修改文本内容。

### 修改颜色

在各个场景的 `<style>` 部分修改 CSS 变量：
- 主色调: `#00d4ff` (青色)
- 辅助色: `#8b5cf6` (紫色)
- 背景色: `#0d1117` (深灰)

### 修改动画

在各个场景的 `<script>` 部分修改 GSAP 动画参数：
- `duration`: 动画时长
- `delay`: 动画延迟
- `ease`: 缓动函数

## 📝 注意事项

1. **字体**: 已使用本地字体文件，无需网络连接
2. **动画**: 所有动画使用 GSAP，性能优秀
3. **响应式**: 设计为 1920×1080，可根据需要调整
4. **兼容性**: 支持现代浏览器

## 🎯 后续优化建议

1. 添加背景音乐
2. 添加配音解说
3. 优化动画时长和节奏
4. 添加更多交互效果
5. 制作不同尺寸版本（竖版、方形）

## 📧 联系方式

如有问题或建议，请联系 Omnia 开发团队。

---

**Made with ❤️ by Omnia Team**
