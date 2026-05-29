# Omnia 功能介绍视频制作指南

## 🎯 目标
制作一个 50 秒的抖音视频，展示 Omnia 的核心功能，使用真实 UI 界面。

## ✅ 已完成
- [x] 真实 UI 截图生成（4 张）
- [x] 中文语音脚本
- [x] 视频配置文件

## 📸 已生成的截图
1. `src/assets/images/real/real-webui-full.png` - 完整仪表盘
2. `src/assets/images/real/real-memory-palace.png` - 记忆宫殿
3. `src/assets/images/real/real-neural-graph.png` - 神经图谱
4. `src/assets/images/real/real-streaming-chat.png` - 流式对话

## 🎬 下一步：录制真实 UI 操作视频

### 方法 1：使用 OBS Studio（推荐）
1. 安装 OBS：`sudo apt install obs-studio`
2. 打开 Omnia WebUI：http://localhost:8765
3. 录制以下操作：
   - 打开页面，展示整体界面（3秒）
   - 点击记忆宫殿，展示记忆数据（5秒）
   - 点击神经图谱，展示图谱可视化（5秒）
   - 在对话框输入问题，展示流式回答（5秒）
   - 连续追问，展示多轮对话（5秒）
   - 使用记忆搜索功能（3秒）

### 方法 2：使用 SimpleScreenRecorder
1. 安装：`sudo apt install simplescreenrecorder`
2. 录制区域选择 1920x1080
3. 录制上述操作

## 🎙️ 语音制作

### 方案 1：自己录音
1. 使用手机或电脑麦克风
2. 按照 `voiceover-script.md` 朗读
3. 保存为 MP3 格式

### 方案 2：使用 AI 语音
1. 使用剪映的 AI 配音功能
2. 或使用 Azure TTS / Google TTS
3. 复制 `voiceover-script.md` 中的文本

## 🎵 背景音乐
- 搜索抖音热门科技 BGM
- 推荐：赛博朋克风格、未来感电子音乐
- 音量调低（30%），不要盖过语音

## ✂️ 剪辑步骤（使用剪映）

### 1. 导入素材
- 截图：`src/assets/images/real/*.png`
- 录屏视频
- 语音文件
- 背景音乐

### 2. 时间线安排
```
0-4秒   | 开场白 + Hook截图
4-12秒  | 记忆宫殿 + 截图/录屏
12-20秒 | 神经图谱 + 截图/录屏
20-28秒 | 工具调用 + 录屏
28-34秒 | 流式对话 + 录屏
34-40秒 | 多轮对话 + 录屏
40-46秒 | 记忆搜索 + 录屏
46-50秒 | 结尾 CTA
```

### 3. 添加效果
- 截图添加缩放动画（Ken Burns 效果）
- 录屏添加鼠标高亮
- 文字添加淡入淡出
- 转场使用滑动效果

### 4. 添加字幕
- 使用剪映的自动字幕功能
- 或手动添加关键信息字幕
- 字幕位置：屏幕下方 1/3 处

## 📱 发布到抖音

### 标题建议
- "我给自己造了一个有记忆的AI"
- "关掉窗口它还记得你说过什么"
- "这才是真正的AI助手"

### 标签
#AI #人工智能 #AI助手 #效率工具 #科技 #程序员 #Omnia #记忆宫殿 #神经图谱

### 封面
使用神经图谱截图作为封面，添加大字："有记忆的AI"

## 📁 文件结构
```
omnia-feature-showcase/
├── src/assets/images/real/          # 真实 UI 截图
├── voiceover-script.md              # 语音脚本
├── config-real-ui.toml              # 视频配置
├── GENERATION-GUIDE.md              # 本指南
└── output/                          # 输出目录
```

## 🚀 快速开始
1. 用 OBS 录制 30 秒 WebUI 操作
2. 用剪映导入截图 + 录屏
3. 添加 AI 配音（复制语音脚本）
4. 添加背景音乐
5. 导出 1080x1920 竖版视频
6. 发布到抖音

---
**预计制作时间：30-60 分钟**
