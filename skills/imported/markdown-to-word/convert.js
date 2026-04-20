#!/usr/bin/env node
/**
 * Markdown 转 Word 转换器 (Node.js 版本)
 * 使用 docx 库直接生成 Word 文档
 */

const fs = require('fs');
const path = require('path');
const docx = require('docx');
const { Document, Paragraph, TextRun, Table, TableCell, TableRow, HeadingLevel,
        AlignmentType, Packer, BorderStyle, convertInchesToTwip } = docx;

function parseMarkdown(mdContent) {
  const lines = mdContent.split('\n');
  const children = [];
  let i = 0;
  
  while (i < lines.length) {
    let line = lines[i];
    
    // 跳过分隔线和空行
    if (line.trim() === '---' || line.trim() === '') {
      i++;
      continue;
    }
    
    // 一级标题 (# Title)
    if (line.startsWith('# ')) {
      children.push(new Paragraph({
        text: line.substring(2),
        heading: HeadingLevel.HEADING_1,
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 }
      }));
    }
    // 二级标题 (## Title)
    else if (line.startsWith('## ')) {
      children.push(new Paragraph({
        text: line.substring(3),
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 200, after: 100 }
      }));
    }
    // 三级标题 (### Title)
    else if (line.startsWith('### ')) {
      children.push(new Paragraph({
        text: line.substring(4),
        heading: HeadingLevel.HEADING_3,
        spacing: { before: 150, after: 80 }
      }));
    }
    // 四级标题 (#### Title)
    else if (line.startsWith('#### ')) {
      children.push(new Paragraph({
        text: line.substring(5),
        heading: HeadingLevel.HEADING_4,
        spacing: { before: 100, after: 60 }
      }));
    }
    // 表格
    else if (line.startsWith('|') && i + 1 < lines.length && lines[i + 1].includes('---')) {
      const tableData = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        if (!lines[i].includes('---')) {
          const cells = lines[i].split('|').slice(1, -1).map(c => c.trim());
          tableData.push(cells);
        }
        i++;
      }
      
      if (tableData.length > 0) {
        const rows = tableData.map((rowData, rowIndex) => {
          return new TableRow({
            children: rowData.map(cellText => new TableCell({
              children: [new Paragraph({
                children: parseInlineFormatting(cellText),
                spacing: { before: 60, after: 60 }
              })],
              borders: {
                top: { style: BorderStyle.SINGLE, size: 1 },
                bottom: { style: BorderStyle.SINGLE, size: 1 },
                left: { style: BorderStyle.SINGLE, size: 1 },
                right: { style: BorderStyle.SINGLE, size: 1 }
              }
            }))
          });
        });
        
        children.push(new Table({
          rows: rows,
          width: { size: 100, type: 'pct' }
        }));
        children.push(new Paragraph({ text: '' }));
      }
      continue;
    }
    // 无序列表
    else if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const text = line.trim().substring(2);
      children.push(new Paragraph({
        children: parseInlineFormatting(text),
        bullet: { level: 0 },
        spacing: { before: 40, after: 40 }
      }));
    }
    // 有序列表
    else if (/^\d+\.\s/.test(line.trim())) {
      const text = line.trim().replace(/^\d+\.\s/, '');
      children.push(new Paragraph({
        children: parseInlineFormatting(text),
        numbering: { reference: 'my-numbering', level: 0 },
        spacing: { before: 40, after: 40 }
      }));
    }
    // 复选框
    else if (line.trim().startsWith('- [ ]') || line.trim().startsWith('- [x]')) {
      const checked = line.toLowerCase().includes('[x]');
      const text = line.trim().substring(5).trim();
      children.push(new Paragraph({
        children: [
          new TextRun({ text: checked ? '☑ ' : '☐ ', font: 'Segoe UI Symbol' }),
          ...parseInlineFormatting(text)
        ],
        spacing: { before: 40, after: 40 }
      }));
    }
    // 普通段落
    else if (line.trim()) {
      children.push(new Paragraph({
        children: parseInlineFormatting(line),
        spacing: { before: 60, after: 60 }
      }));
    }
    
    i++;
  }
  
  return children;
}

function parseInlineFormatting(text) {
  const runs = [];
  let remaining = text;
  
  // 匹配 **加粗** 和 *斜体*
  const regex = /(\*\*.*?\*\*|\*.*?\*|__.*?__|_.*?_)/g;
  let lastIndex = 0;
  let match;
  
  while ((match = regex.exec(text)) !== null) {
    // 添加匹配前的普通文本
    if (match.index > lastIndex) {
      runs.push(new TextRun({ text: text.substring(lastIndex, match.index) }));
    }
    
    const matched = match[0];
    if (matched.startsWith('**') && matched.endsWith('**')) {
      runs.push(new TextRun({ text: matched.slice(2, -2), bold: true }));
    } else if (matched.startsWith('*') && matched.endsWith('*')) {
      runs.push(new TextRun({ text: matched.slice(1, -1), italics: true }));
    } else if (matched.startsWith('__') && matched.endsWith('__')) {
      runs.push(new TextRun({ text: matched.slice(2, -2), bold: true }));
    } else if (matched.startsWith('_') && matched.endsWith('_')) {
      runs.push(new TextRun({ text: matched.slice(1, -1), italics: true }));
    }
    
    lastIndex = match.index + matched.length;
  }
  
  // 添加剩余的普通文本
  if (lastIndex < text.length) {
    runs.push(new TextRun({ text: text.substring(lastIndex) }));
  }
  
  return runs.length > 0 ? runs : [new TextRun({ text: text })];
}

async function convertMarkdownToDocx(inputFile, outputFile) {
  if (!fs.existsSync(inputFile)) {
    console.error(`❌ 文件不存在: ${inputFile}`);
    process.exit(1);
  }

  if (!outputFile.endsWith('.docx')) {
    outputFile += '.docx';
  }

  console.log(`📝 正在转换: ${inputFile} → ${outputFile}`);
  
  const mdContent = fs.readFileSync(inputFile, 'utf-8');
  const children = parseMarkdown(mdContent);
  
  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: {
            top: convertInchesToTwip(1),
            right: convertInchesToTwip(1),
            bottom: convertInchesToTwip(1),
            left: convertInchesToTwip(1)
          }
        }
      },
      children: children
    }]
  });
  
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputFile, buffer);
  
  console.log(`✅ 转换完成: ${outputFile}`);
}

function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 1) {
    console.log(`
Usage: node convert.js <input.md> [output.docx]

Examples:
  node convert.js document.md
  node convert.js document.md output.docx
`);
    process.exit(0);
  }

  const inputFile = args[0];
  const outputFile = args[1] || inputFile.replace(/\.md$/i, '.docx');

  convertMarkdownToDocx(inputFile, outputFile).catch(err => {
    console.error('❌ 转换失败:', err.message);
    process.exit(1);
  });
}

module.exports = { convertMarkdownToDocx, parseMarkdown };

if (require.main === module) {
  main();
}