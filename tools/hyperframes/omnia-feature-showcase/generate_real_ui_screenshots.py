#!/usr/bin/env python3
"""Generate screenshots that match the real Omnia WebUI style."""

from PIL import Image, ImageDraw, ImageFont
import os

# Font loading
FONT_PATH = '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/assets/fonts/noto-sans-sc.woff2'
FONT_FALLBACK = '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'

def get_font(size=16):
    """Load Chinese font."""
    for path in [FONT_PATH, FONT_FALLBACK]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

# Pre-load fonts
FONT_SM = get_font(14)
FONT_MD = get_font(16)
FONT_LG = get_font(24)
FONT_XL = get_font(32)

# Colors from real UI
BG_COLOR = (15, 23, 42)
PANEL_BG = (30, 41, 59)
ACCENT_CYAN = (34, 211, 238)
ACCENT_PURPLE = (168, 85, 247)
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (148, 163, 184)
GREEN = (34, 197, 94)
BORDER_COLOR = (51, 65, 85)

def create_base_image(width=1920, height=1080):
    img = Image.new('RGB', (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(20, 30, 50), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(20, 30, 50), width=1)
    return img, draw

def draw_panel(draw, x, y, w, h, title="", tag=""):
    draw.rectangle([x, y, x+w, y+h], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.line([(x, y+32), (x+w, y+32)], fill=BORDER_COLOR, width=1)
    if tag:
        draw.text((x+10, y+8), tag, fill=ACCENT_CYAN, font=FONT_MD)
    if title:
        draw.text((x+80, y+8), title, fill=TEXT_WHITE, font=FONT_MD)

def draw_omnia_logo(draw, x, y):
    draw.polygon([(x, y+20), (x+15, y), (x+30, y+20)], outline=TEXT_WHITE, width=2)
    draw.arc([(x+5, y+5), (x+15, y+15)], 0, 360, fill=ACCENT_CYAN, width=2)
    draw.arc([(x+15, y+5), (x+25, y+15)], 0, 360, fill=ACCENT_CYAN, width=2)

def create_full_dashboard():
    img, draw = create_base_image()
    # Top bar
    draw.rectangle([0, 0, 1920, 60], fill=(15, 23, 42))
    draw.line([(0, 60), (1920, 60)], fill=BORDER_COLOR, width=1)
    draw_omnia_logo(draw, 20, 15)
    draw.text((60, 12), "OMNIA", fill=TEXT_WHITE, font=FONT_LG)
    draw.text((60, 38), "永不遗忘的操作系统", fill=TEXT_GRAY, font=FONT_SM)
    draw.text((900, 15), "00:00:00", fill=ACCENT_CYAN, font=FONT_LG)
    draw.text((900, 38), "SYSTEM ONLINE", fill=TEXT_GRAY, font=FONT_SM)
    # Panels
    draw_panel(draw, 20, 80, 300, 150, "链路状态", "SYS.LINK")
    links = [("守护进程", "ACTIVE", GREEN), ("API 通道", "CONNECTED", GREEN), ("IDE 桥接", "READY", GREEN)]
    for i, (name, status, color) in enumerate(links):
        y = 125 + i * 35
        draw.ellipse([(30, y+5), (40, y+15)], fill=color)
        draw.text((50, y), name, fill=TEXT_GRAY, font=FONT_MD)
        draw.text((200, y), status, fill=color, font=FONT_MD)
    draw_panel(draw, 20, 250, 300, 120, "记忆宫殿", "MEM.PALACE")
    memories = [("事实", "190"), ("关系", "51"), ("习惯", "15"), ("时间线", "1904")]
    for i, (label, count) in enumerate(memories):
        x = 40 + (i % 2) * 140
        y = 295 + (i // 2) * 40
        draw.text((x, y), count, fill=ACCENT_CYAN, font=FONT_LG)
        draw.text((x, y+28), label, fill=TEXT_GRAY, font=FONT_SM)
    draw_panel(draw, 20, 390, 300, 120, "Git 态势", "GIT.OP")
    draw.text((40, 435), "分支", fill=TEXT_GRAY, font=FONT_MD)
    draw.text((200, 435), "main", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((40, 465), "24h 提交", fill=TEXT_GRAY, font=FONT_MD)
    draw.text((200, 465), "12", fill=GREEN, font=FONT_MD)
    draw_panel(draw, 20, 530, 300, 150, "环境快照", "ENV.SNAP")
    envs = [("HOST", "shan-pc"), ("MODEL", "gpt-4o"), ("SHELL", "bash"), ("OS", "Ubuntu 22.04")]
    for i, (label, value) in enumerate(envs):
        y = 575 + i * 25
        draw.text((40, y), label, fill=TEXT_GRAY, font=FONT_MD)
        draw.text((150, y), value, fill=TEXT_WHITE, font=FONT_MD)
    # Chat area
    draw_panel(draw, 340, 80, 900, 600, "", "")
    draw.text((380, 100), "欢迎来到 Omnia。我是与你共同成长的操作系统。", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((380, 130), "从此刻起，我们所做的一切，我都会铭记。", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((380, 160), "Omnia · 刚刚", fill=TEXT_GRAY, font=FONT_SM)
    draw.rectangle([360, 620, 1220, 670], fill=(15, 23, 42), outline=BORDER_COLOR, width=1)
    draw.text((380, 640), "输入消息...", fill=TEXT_GRAY, font=FONT_MD)
    # Right column
    draw_panel(draw, 1260, 80, 640, 350, "神经图谱", "NEURAL.GRAPH")
    draw.rectangle([1280, 130, 1880, 380], fill=(15, 23, 42), outline=BORDER_COLOR, width=1)
    nodes = [(1400, 200), (1550, 250), (1700, 200), (1450, 320), (1650, 300)]
    for x, y in nodes:
        draw.ellipse([(x-8, y-8), (x+8, y+8)], fill=ACCENT_CYAN, outline=TEXT_WHITE, width=1)
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            draw.line([nodes[i], nodes[j]], fill=(50, 70, 100), width=1)
    draw.text((1280, 390), "节点: 247  关系: 568", fill=TEXT_GRAY, font=FONT_SM)
    draw_panel(draw, 1260, 450, 310, 100, "API 提供商", "API.SEL")
    draw.text((1290, 495), "xiaomi/mimo-v2-flash", fill=TEXT_WHITE, font=FONT_MD)
    draw_panel(draw, 1590, 450, 310, 100, "IDE 上下文", "IDE.CTX")
    draw.text((1620, 495), "未连接", fill=TEXT_GRAY, font=FONT_MD)
    draw_panel(draw, 1260, 570, 310, 110, "系统体征", "SYS.VITAL")
    vitals = [("CPU", "23%"), ("MEM", "4.2GB"), ("DISK", "156GB"), ("TEMP", "42°C")]
    for i, (label, value) in enumerate(vitals):
        x = 1280 + (i % 2) * 140
        y = 615 + (i // 2) * 30
        draw.text((x, y), label, fill=TEXT_GRAY, font=FONT_MD)
        draw.text((x+50, y), value, fill=TEXT_WHITE, font=FONT_MD)
    draw_panel(draw, 1590, 570, 310, 110, "通知中心", "NOTIF")
    draw.text((1620, 615), "暂无新通知", fill=TEXT_GRAY, font=FONT_MD)
    draw_panel(draw, 20, 700, 600, 100, "技能矩阵", "SKILL.MTX")
    draw.text((40, 745), "已装载技能: 15", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((250, 745), "自动锻造: ON", fill=GREEN, font=FONT_MD)
    draw_panel(draw, 640, 700, 300, 100, "记忆搜索", "MEM.SEARCH")
    draw.rectangle([660, 740, 920, 770], fill=(15, 23, 42), outline=BORDER_COLOR, width=1)
    draw.text((670, 748), "搜索记忆...", fill=TEXT_GRAY, font=FONT_MD)
    draw_panel(draw, 960, 700, 300, 100, "一键工作流", "WORKFLOW")
    draw.text((980, 745), "Git 状态  备份空间", fill=TEXT_GRAY, font=FONT_SM)
    draw.text((980, 770), "部署 SEO  课件统计", fill=TEXT_GRAY, font=FONT_SM)
    draw_panel(draw, 1280, 700, 620, 100, "", "")
    draw.text((1300, 720), "INFINITE 机体", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((1300, 745), "LINK: STRONG", fill=GREEN, font=FONT_MD)
    draw.text((1500, 745), "MEM: 2060", fill=ACCENT_CYAN, font=FONT_MD)
    draw.text((1650, 745), "SKILL: 15", fill=ACCENT_CYAN, font=FONT_MD)
    # Bottom bar
    draw.rectangle([0, 820, 1920, 850], fill=(15, 23, 42))
    draw.line([(0, 820), (1920, 820)], fill=BORDER_COLOR, width=1)
    draw.text((20, 828), "COGNITION ACTIVE", fill=GREEN, font=FONT_MD)
    draw.text((900, 828), "需要你的确认 - Omnia 请求执行一个操作。", fill=TEXT_GRAY, font=FONT_SM)
    return img

def create_memory_palace_closeup():
    img, draw = create_base_image()
    draw.rectangle([0, 0, 1920, 80], fill=PANEL_BG)
    draw.text((40, 20), "MEM.PALACE", fill=ACCENT_CYAN, font=FONT_LG)
    draw.text((250, 20), "记忆宫殿 - 详细视图", fill=TEXT_WHITE, font=FONT_LG)
    draw.text((40, 55), "共 2060 条记忆", fill=TEXT_GRAY, font=FONT_MD)
    categories = [
        ("事实 (Facts)", "190", "关于系统、用户、项目的确定性知识"),
        ("关系 (Relations)", "51", "人物、项目、概念之间的关系网络"),
        ("习惯 (Habits)", "15", "用户的工作习惯、偏好、行为模式"),
        ("时间线 (Timeline)", "1904", "按时间顺序记录的事件和对话"),
    ]
    for i, (name, count, desc) in enumerate(categories):
        y = 100 + i * 120
        draw.rectangle([40, y, 900, y+100], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        draw.text((60, y+15), name, fill=TEXT_WHITE, font=FONT_MD)
        draw.text((60, y+45), desc, fill=TEXT_GRAY, font=FONT_SM)
        draw.text((800, y+25), count, fill=ACCENT_CYAN, font=FONT_XL)
    draw.text((960, 100), "最近记忆", fill=TEXT_WHITE, font=FONT_LG)
    recent = ["用户询问神经图谱功能", "系统展示了记忆宫殿界面", "讨论了AI助手的发展方向", "创建了Omnia功能介绍视频"]
    for i, text in enumerate(recent):
        y = 140 + i * 40
        draw.rectangle([960, y, 1880, y+30], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
        draw.text((980, y+8), text, fill=TEXT_GRAY, font=FONT_MD)
    return img

def create_neural_graph_closeup():
    img, draw = create_base_image()
    draw.rectangle([0, 0, 1920, 80], fill=PANEL_BG)
    draw.text((40, 20), "NEURAL.GRAPH", fill=ACCENT_CYAN, font=FONT_LG)
    draw.text((300, 20), "神经图谱 - 可视化", fill=TEXT_WHITE, font=FONT_LG)
    draw.text((40, 55), "247 个节点 · 568 条边 · 7 种类型", fill=TEXT_GRAY, font=FONT_MD)
    draw.rectangle([40, 100, 1400, 700], fill=(15, 23, 42), outline=BORDER_COLOR, width=1)
    nodes_with_labels = [
        (200, 200, "Omnia", ACCENT_CYAN), (400, 300, "原点", ACCENT_PURPLE),
        (600, 200, "无限", ACCENT_CYAN), (800, 350, "神经图谱", GREEN),
        (300, 450, "记忆宫殿", GREEN), (500, 500, "工具调用", TEXT_GRAY),
        (700, 450, "流式对话", TEXT_GRAY), (900, 250, "WebUI", TEXT_GRAY),
        (1100, 300, "记忆搜索", TEXT_GRAY),
    ]
    edges = [(0,1), (0,2), (1,3), (2,3), (1,4), (3,5), (3,6), (0,7), (4,8)]
    for i, j in edges:
        x1, y1 = nodes_with_labels[i][0], nodes_with_labels[i][1]
        x2, y2 = nodes_with_labels[j][0], nodes_with_labels[j][1]
        draw.line([(x1,y1), (x2,y2)], fill=(50, 70, 100), width=2)
    for x, y, label, color in nodes_with_labels:
        draw.ellipse([(x-12, y-12), (x+12, y+12)], fill=color, outline=TEXT_WHITE, width=2)
        draw.text((x-30, y+20), label, fill=TEXT_WHITE, font=FONT_SM)
    draw.rectangle([1420, 100, 1880, 400], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.text((1440, 120), "图例", fill=TEXT_WHITE, font=FONT_LG)
    for i, (label, color) in enumerate([("项目", ACCENT_CYAN), ("人物", ACCENT_PURPLE), ("概念", GREEN), ("文件", TEXT_GRAY)]):
        y = 170 + i * 40
        draw.ellipse([(1450, y), (1470, y+20)], fill=color)
        draw.text((1490, y), label, fill=TEXT_WHITE, font=FONT_MD)
    draw.rectangle([1420, 420, 1880, 600], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.text((1440, 440), "统计", fill=TEXT_WHITE, font=FONT_LG)
    for i, (label, value) in enumerate([("项目节点", "23"), ("人物节点", "45"), ("概念节点", "89"), ("文件节点", "67")]):
        y = 490 + i * 30
        draw.text((1460, y), label, fill=TEXT_GRAY, font=FONT_MD)
        draw.text((1750, y), value, fill=ACCENT_CYAN, font=FONT_MD)
    return img

def create_streaming_chat():
    img, draw = create_base_image()
    draw.rectangle([0, 0, 1920, 60], fill=(15, 23, 42))
    draw.text((40, 20), "OMNIA", fill=TEXT_WHITE, font=FONT_LG)
    draw.text((160, 20), "流式对话", fill=TEXT_GRAY, font=FONT_LG)
    draw.rectangle([40, 80, 1880, 700], fill=PANEL_BG, outline=BORDER_COLOR, width=1)
    draw.rectangle([1400, 100, 1840, 160], fill=(30, 58, 138))
    draw.text((1420, 120), "Omnia有什么功能？", fill=TEXT_WHITE, font=FONT_MD)
    draw.text((1750, 140), "用户", fill=TEXT_GRAY, font=FONT_SM)
    ai_messages = [
        "Omnia 是一个有记忆的 AI 操作系统，",
        "核心功能包括：", "",
        "1. 记忆宫殿 - 记住你说过的每一句话",
        "2. 神经图谱 - 理解知识之间的关系",
        "3. 工具调用 - 自动执行 40+ 种操作",
        "4. 流式对话 - 实时响应你的问题", "",
        "我是你的私人 AI 助手，",
        "永远不会忘记我们的对话。"
    ]
    y = 180
    for i, line in enumerate(ai_messages):
        alpha = max(100, 255 - i * 15)
        color = (alpha, alpha, alpha)
        draw.text((100, y), line, fill=color, font=FONT_MD)
        y += 28
    draw.rectangle([100, y, 108, y+20], fill=ACCENT_CYAN)
    draw.rectangle([40, 720, 1880, 780], fill=(15, 23, 42), outline=BORDER_COLOR, width=1)
    draw.text((60, 740), "继续说...", fill=TEXT_GRAY, font=FONT_MD)
    draw.text((1700, 740), "上下文 45%", fill=TEXT_GRAY, font=FONT_MD)
    return img

def main():
    output_dir = '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/assets'
    os.makedirs(output_dir, exist_ok=True)
    print("🎨 Generating real UI screenshots with Chinese fonts...")
    screenshots = {
        'real-ui-memory.png': create_memory_palace_closeup(),
        'real-ui-graph.png': create_neural_graph_closeup(),
        'real-ui-streaming.png': create_streaming_chat(),
        'real-ui-tools.png': create_full_dashboard(),
        'real-ui-multi-turn.png': create_full_dashboard(),
    }
    for filename, img in screenshots.items():
        path = os.path.join(output_dir, filename)
        img.save(path, quality=95)
        print(f"✅ Generated: {filename}")
    print(f"\n🎉 All {len(screenshots)} screenshots generated!")

if __name__ == '__main__':
    main()
