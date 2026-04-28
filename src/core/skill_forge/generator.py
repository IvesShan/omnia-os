"""Skill Forge — Skill Generator

from core.logging_config import get_logger

logger = get_logger(__name__)

Converts a DetectedPattern into a structured SKILL.md draft.
V0.1 uses built-in templates per bucket; falls back to a generic template.
"""

from __future__ import annotations

import re
from textwrap import dedent
from typing import Dict, List

from .detector import DetectedPattern


BUILTIN_TEMPLATES: Dict[str, Dict[str, str]] = {
    "auto-forge-frontend-page-dev": {
        "description": "根据设计需求快速生成或调整前端页面（HTML/CSS/JS）。支持深色/浅色主题切换、响应式布局、SVG插图、以及无依赖的纯静态页面输出。",
        "triggers": [
            "用户提到'做一个页面'、'生成网站'、'改主题'或给出具体设计风格参考（如 CutCut、Stripe、Apple Keynote）",
            "需要批量修改课件或演示文稿的外观和配色",
        ],
        "capabilities": [
            "生成纯 HTML/CSS/JS 单页应用（无外部依赖）",
            "批量替换主题色、背景色、字体配置",
            "生成 SVG 插图和图表",
            "确保页面支持键盘/触摸交互和响应式适配",
        ],
        "example": '''
用户：帮我把这30个课件全部改成白色清爽主题
Omnia：
1. 扫描所有课件文件，提取颜色变量和模板结构
2. 生成批量替换脚本 (batch_light_theme.py)
3. 执行替换并逐个验证渲染效果
4. 汇报修改数量和可能存在的遗漏文件
''',
    },
    "auto-forge-deployment-devops": {
        "description": "自动化部署、定时任务设置、以及开发运维脚本的编写与维护。支持 EdgeOne、Vercel 等平台的一键部署和 Cron 监控。",
        "triggers": [
            "用户提到'部署到线上'、'设置定时任务'、'帮我搞个自动化'",
            "需要修复或更新 CI/CD、Cron、systemd 等运维配置",
        ],
        "capabilities": [
            "编写并部署自动化脚本（SEO pipeline、内容分发、备份等）",
            "配置 Cron 任务和系统守护进程",
            "使用 EdgeOne CLI / Vercel CLI 等工具推送线上部署",
            "监控部署日志并报告异常",
        ],
        "example": '''
用户：我不想每天手动发文章，能自动化吗？
Omnia：
1. 分析现有的内容生成流程
2. 编写一个 daily publisher 脚本
3. 配置 Cron 在每天固定时间执行
4. 设置日志监控和失败告警
''',
    },
    "auto-forge-content-generation": {
        "description": "根据主题、关键词或产品信息，自动生成适合多平台分发的内容文案（知乎、小红书、抖音等），并处理 SEO 优化和社交媒体发布策略。",
        "triggers": [
            "用户提到'写文案'、'生成内容'、'做SEO'、'发小红书/知乎/抖音'",
            "需要批量生成产品介绍、营销软文或长尾关键词文章",
        ],
        "capabilities": [
            "根据关键词生成知乎/小红书/抖音风格的文案",
            "自动生成 SEO 标题、描述和标签",
            "批量生成28天内容日历和一键复制发布控制台",
            "优化文案以适应不同平台的字数和语气规范",
        ],
        "example": '''
用户：帮我写10篇关于无人机维修的长尾文章
Omnia：
1. 提取关键词列表（如'mavic 2 云台校准'、'mini 3 无法起飞'）
2. 为每篇文章生成标题、正文结构和 meta 描述
3. 输出为可直接部署的 HTML 文件或 Markdown
4. 生成内容分发控制台，支持一键复制各平台文案
''',
    },
    "auto-forge-miaoxiujiang-dev": {
        "description": "喵修匠（无人机维修平台）的前后端开发、流程加固和系统调试。涵盖工单状态机、商家工作台、报价系统、发货与付款流程等。",
        "triggers": [
            "用户提到'喵修匠'、'工单'、'商家后台'、'发货'、'报价'、'维修流程'",
            "需要修复或新增与喵修匠相关的任何功能",
        ],
        "capabilities": [
            "维护工单状态机（draft → diagnosed → quoted → paid → repaired → shipped → delivered）",
            "开发或修复商家工作台（workbench）、报价后台（pricing_admin）、AI 诊断页面",
            "对接微信支付、发货物流、库存管理等功能",
            "根据用户反馈快速定位并修复流程阻塞点",
        ],
        "example": '''
用户：商家工作台点了发货没反应
Omnia：
1. 检查前端 API 调用和请求参数
2. 检查后端状态机对发货状态的转义条件
3. 确认发货函数是否正确定义和暴露
4. 修复问题并验证完整流程（发货 → 状态更新 → 用户端同步）
''',
    },
    "auto-forge-system-fix": {
        "description": "系统级问题排查、错误修复和环境配置调试。擅长从 symptom 深入 root cause，不轻易绕路。",
        "triggers": [
            "用户报告报错、功能失效、页面白屏、部署失败等异常",
            "需要升级、配置或修复本地开发环境和工具链",
        ],
        "capabilities": [
            "分析前后端报错日志并定位根因",
            "修复代码缺陷、兼容性问题、网络/API 配置错误",
            "提供稳健的回滚和验证方案",
            "将修复过程沉淀为可复用的检查清单或脚本",
        ],
        "example": '''
用户：workbench 页面加载不出来
Omnia：
1. 打开浏览器控制台和 Network 面板确认具体错误
2. 检查 JS 文件是否有 ReferenceError、404、CORS 等问题
3. 追踪到缺失的函数定义或错误的 API_BASE 配置
4. 修复并验证页面恢复正常加载
''',
    },
    "auto-forge-courseware-design": {
        "description": "基于 Apple Keynote + Stripe 风格，设计和生成无人机培训课程的 HTML 课件。支持深色/浅色主题、SVG 图解、进度导航和响应式布局。",
        "triggers": [
            "用户提到'课件'、'讲义'、'课程'、'presentation'、'slides'",
            "需要为无人机维修课程生成新的章节课件或更新现有课件样式",
        ],
        "capabilities": [
            "生成无外部依赖的 HTML/CSS/SVG 课件",
            "统一应用设计系统（Inter 字体、配色、间距、圆角）",
            "添加键盘/空格/触摸翻页交互和进度条",
            "批量转换深色/浅色主题",
        ],
        "example": '''
用户：把无人机维修店利润分析做成一个11页的直播课件
Omnia：
1. 梳理核心数据点和叙事结构
2. 按 Apple Keynote 风格设计每一页的布局和文字
3. 生成纯 HTML 文件，内置 SVG 图表和 Bento Grid
4. 测试翻页交互和移动端适配
''',
    },
    "auto-forge-data-processing": {
        "description": "处理 CSV、Excel、JSON 等数据文件的导入、解析、清洗和格式化。擅长编写一次性或批量的数据处理脚本。",
        "triggers": [
            "用户提到'导入数据'、'解析 Excel'、'处理 CSV'、'数据清洗'",
            "需要把一种格式的数据转换成另一种格式或写入数据库",
        ],
        "capabilities": [
            "读取并解析 xlsx / csv / json 文件",
            "生成清洗、去重、格式化脚本",
            "将数据写入 SQLite、生成 SQL 插入语句",
            "输出结构化的报告或错误日志",
        ],
        "example": '''
用户：帮我把这个 Excel 表格里的数据导入到数据库
Omnia：
1. 读取 Excel 文件并检测列名和数据类型
2. 处理缺失值、格式异常和重复行
3. 生成对应的 SQL schema 和 INSERT 脚本
4. 执行导入并验证行数一致
''',
    },
}


def _fallback_template(pattern: DetectedPattern) -> Dict[str, str]:
    """Build a generic template from evidence."""
    verbs = set()
    for e in pattern.evidence:
        # Greedy verb extraction (Chinese + English)
        matches = re.findall(r"([\u4e00-\u9fa5]{2,}了|[\u4e00-\u9fa5]{2,}成|\w+ed|\w+ing|\w+ize|\w+ise)", e)
        verbs.update(matches[:3])
    verb_list = ", ".join(sorted(verbs)) if verbs else "处理相关任务"
    return {
        "description": f"根据用户需求，{pattern.pattern_name}。擅长从对话和项目上下文中提取意图并转化为可执行方案。",
        "triggers": [
            f"用户提到与 '{pattern.pattern_name}' 相关的需求或问题",
        ],
        "capabilities": [
            f"分析证据中的常见操作（{verb_list}）",
            "生成对应脚本、配置或文档",
            "验证执行结果并报告状态",
        ],
        "example": f"""
用户：帮我处理一个 {pattern.pattern_name} 的任务
Omnia：
1. 分析当前上下文和历史记忆
2. 生成对应的执行方案
3. 执行任务并验证结果
4. 汇报完成状态和可能的后续建议
""",
    }


class SkillGenerator:
    """Generates a SKILL.md draft from a detected pattern."""

    def generate(self, pattern: DetectedPattern) -> str:
        tmpl = BUILTIN_TEMPLATES.get(pattern.pattern_id, _fallback_template(pattern))

        triggers = "\n".join(f"- {t}" for t in tmpl["triggers"])
        capabilities = "\n".join(f"- {c}" for c in tmpl["capabilities"])
        evidence_md = "\n".join(f"- {e}" for e in pattern.evidence[:7])

        skill_md = dedent(
            f"""\
            # {pattern.pattern_name}

            ## Description
            {tmpl['description']}

            ## When to Activate
            {triggers}

            ## Capabilities
            {capabilities}

            ## Example Usage
            {tmpl['example'].strip()}

            ## Evidence Base
            The following task patterns from memory triggered this skill creation:
            {evidence_md}

            ---
            *Auto-generated by Omnia Skill Forge v0.1*
            *Pattern ID: {pattern.pattern_id} | Confidence: {pattern.confidence:.2f} | Frequency: {pattern.frequency}*
            """
        )
        return skill_md.strip() + "\n"

    def write(self, pattern: DetectedPattern, out_dir: str = ".") -> str:
        """Generate and write the SKILL.md to disk. Returns the written path."""
        from pathlib import Path

        content = self.generate(pattern)
        dest = Path(out_dir) / f"{pattern.suggested_skill_name}" / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return str(dest)


if __name__ == "__main__":

    from .detector import PatternDetector

    pd = PatternDetector()
    patterns = pd.detect()
    sg = SkillGenerator()

    print(f"Detected {len(patterns)} pattern(s).\n")
    for p in patterns:
        md = sg.generate(p)
        logger.info("=" * 60)
        logger.info(md)
        logger.info("=" * 60)
