# Skill: 视频制作与剪辑

## 能力范围
1. **视频生成** — 从 HTML 生成动画视频 (HyperFrames)
2. **口播剪辑** — 语音转字幕 + 字幕烧录 + 片头动画 + 拼接输出

## 工具链
| 工具 | 作用 | 状态 |
|------|------|------|
| HyperFrames | HTML → MP4 动画视频 | ✅ Node.js 22 + FFmpeg |
| Whisper | 语音 → SRT 字幕 | ✅ ~/venvs/whisper/ |
| FFmpeg | 视频编辑（字幕/拼接/叠加） | ✅ 系统自带 |

## 生成动画视频

### 方式一：模板系统（推荐，审美最好）

预置了 5 套高质量动画模板，直接渲染即可：

```bash
# 科技故障风（赛博朋克，适合科技类视频）
hyperframes render \
  --input tools/video_generation/templates/tech_glitch/index.html \
  --output glitch_intro.mp4 --width 720 --height 1280 --duration 3 --fps 30

# 极简渐变风（玻璃态卡片，适合品牌展示）
hyperframes render \
  --input tools/video_generation/templates/minimal_gradient/index.html \
  --output gradient_intro.mp4 --width 720 --height 1280 --duration 3 --fps 30

# 粒子揭示风（Canvas 粒子，适合大气开场）
hyperframes render \
  --input tools/video_generation/templates/particle_reveal/index.html \
  --output particle_intro.mp4 --width 720 --height 1280 --duration 3 --fps 30

# 电影缩放风（胶片颗粒+黑边，适合故事感）
hyperframes render \
  --input tools/video_generation/templates/cinematic_zoom/index.html \
  --output cinematic_intro.mp4 --width 720 --height 1280 --duration 3 --fps 30

# 代码编辑器风（打字机效果，适合程序员/产品）
hyperframes render \
  --input tools/video_generation/templates/typewriter/index.html \
  --output code_intro.mp4 --width 720 --height 1280 --duration 3 --fps 30
```

**替换模板文字**：
```bash
# 修改品牌名称后渲染
sed 's/OMNIA/你的品牌/g; s/你的 AI 超级助手/你的副标题/g' \
  templates/tech_glitch/index.html > temp.html
hyperframes render --input temp.html --output intro.mp4
```

### 方式二：从零生成（不推荐，审美不稳定）
```bash
cd /tmp && npx hyperframes init my-video
cd my-video
# 编辑 HTML (GSAP 动画 + data 属性控制时间线)
npx hyperframes render renders/output.mp4
```

### 审美提升要点
1. **字体**：用 Google Fonts（Noto Sans SC、Orbitron、JetBrains Mono）
2. **缓动**：用 `cubic-bezier(0.16, 1, 0.3, 1)` 替代 linear
3. **层次**：背景+中景+前景分离
4. **质感**：玻璃态、粒子、光晕、扫描线、胶片颗粒
5. **色彩**：渐变背景 > 纯色背景

## 口播视频自动剪辑
```bash
# 基本用法：自动加字幕
bash tools/video_edit/auto_edit.sh input.mp4

# 完整参数
bash tools/video_edit/auto_edit.sh input.mp4 \
    --brand "无人机维修专家" \
    --style tiktok \
    --intro-duration 3 \
    --output output.mp4

# 字幕风格: tiktok(抖音风) / classic(经典) / minimal(简约)
# --no-intro 不加片头
```

## 脚本位置
- `tools/video_generation/templates/` — 高质量动画模板
- `tools/video_edit/auto_edit.sh` — 完整剪辑流水线
- `tools/video_edit/subtitle.sh` — 仅字幕烧录

## 工作流程
1. 用户提供口播视频 → `auto_edit.sh`
2. Whisper 语音识别 → 生成 SRT 字幕
3. FFmpeg 烧录字幕（支持多种风格）
4. HyperFrames 渲染片头动画（使用模板）
5. FFmpeg 拼接输出最终视频
