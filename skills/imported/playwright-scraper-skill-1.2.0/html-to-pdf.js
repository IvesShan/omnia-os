const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function htmlToPDF(inputFile, outputFile) {
  if (!fs.existsSync(inputFile)) {
    console.error(`Error: File not found ${inputFile}`);
    process.exit(1);
  }

  const inputPath = path.resolve(inputFile);
  const outputPath = outputFile ? path.resolve(outputFile) : inputPath.replace('.html', '.pdf');

  console.log(`Converting ${inputPath} to PDF...`);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Load HTML file
  await page.goto(`file://${inputPath}`, { waitUntil: 'networkidle' });

  // Generate PDF - Landscape format for slides
  await page.pdf({
    path: outputPath,
    width: '1280px',
    height: '720px',
    printBackground: true,
    landscape: true
  });

  await browser.close();

  console.log(`✅ PDF saved to: ${outputPath}`);
}

// Command line usage
const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile) {
  console.log('Usage: node html-to-pdf.js <input.html> [output.pdf]');
  process.exit(1);
}

htmlToPDF(inputFile, outputFile);
