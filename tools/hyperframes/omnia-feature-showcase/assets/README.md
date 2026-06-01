# WebUI Screenshots for HyperFrames

## 📸 Captured Screenshots

All real UI screenshots have been captured from `http://localhost:8765` using Playwright.

### Full Dashboard
- **real-ui-full.png** (1920×1080) - Complete WebUI dashboard

### Individual Panels
- **real-ui-memory.png** (294×219) - Memory Palace panel
- **real-ui-graph.png** (290×572) - Neural Graph panel
- **real-ui-system.png** (290×105) - System vitals panel
- **real-ui-skills.png** (290×104) - Skill matrix panel
- **real-ui-git.png** (294×121) - Git status panel
- **real-ui-workflow.png** (290×168) - Workflow panel
- **real-ui-api.png** (290×541) - API selector panel
- **real-ui-notif.png** (290×72) - Notification panel
- **real-ui-daemon.png** (294×131) - Link status panel

### Legacy Screenshots (for reference)
- real-ui-multi-turn.png (1920×1080)
- real-ui-streaming.png (1920×1080)
- real-ui-tools.png (1920×1080)

## 🎬 Scene Usage

Each scene in `compositions/` uses these screenshots as backgrounds:

| Scene | Background Image | Duration |
|-------|-----------------|----------|
| scene-hook | (gradient text only) | 3s |
| scene-intro | (animated logo) | 5s |
| scene-memory | real-ui-memory.png | 12s |
| scene-graph | real-ui-graph.png | 12s |
| scene-tools | real-ui-tools.png | 12s |
| scene-streaming | real-ui-streaming.png | 6s |
| scene-multiturn | real-ui-multi-turn.png | 8s |
| scene-cta | (gradient text only) | 7s |

## 🔧 Re-capture Screenshots

To update screenshots after WebUI changes:

```bash
cd /home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase
python3 capture_real_webui.py
```

## 📋 Requirements

- Playwright installed (`pip install playwright`)
- Chromium browser installed (`playwright install chromium`)
- WebUI running on `http://localhost:8765`
