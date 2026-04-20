# Markdown to Word Skill

将 Markdown 文件转换为 Microsoft Word 文档 (.docx)。

## 功能

- 支持标题、段落、列表、表格
- 支持加粗、斜体等格式
- 支持复选框列表
- 自动处理中文字体

## 使用方式

### 命令行

```bash
# 基本用法（输出同名 .docx 文件）
node skills/markdown-to-word/convert.js document.md

# 指定输出文件名
node skills/markdown-to-word/convert.js document.md output.docx
```

### 作为模块调用

```javascript
const { convertMarkdownToDocx } = require('./skills/markdown-to-word/convert');

convertMarkdownToDocx('input.md', 'output.docx');
```

## 依赖安装

首次使用需要安装 Python 依赖：

```bash
pip3 install python-docx
```

或运行转换命令时会自动尝试安装。

## 支持的 Markdown 语法

- `# 标题` - 各级标题
- `**加粗**` - 加粗文本
- `*斜体*` - 斜体文本
- `- 列表项` - 无序列表
- `1. 列表项` - 有序列表
- `- [ ] 任务` - 复选框
- `| 表格 |` - 表格

## 示例

```bash
# 转换股东合作协议
node skills/markdown-to-word/convert.js \
  "南京物熵科技有限公司_股东合作协议.md" \
  "股东合作协议.docx"
```