const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 产品列表
const products = [
  { name: 'mini4pro', url: 'https://www.dji.com/mini-4-pro' },
  { name: 'air3', url: 'https://www.dji.com/air-3' },
  { name: 'mavic3pro', url: 'https://www.dji.com/mavic-3-pro' },
  { name: 'fpv', url: 'https://www.dji.com/fpv' },
  { name: 'avata2', url: 'https://www.dji.com/avata-2' }
];

const outputDir = process.argv[2] || '/home/uosun-shan/.openclaw/workspace/projects/drone_course/images_final';

// 确保输出目录存在
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

async function captureProduct(url, name) {
  console.log(`Capturing ${name} from ${url}...`);
  
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      viewport: { width: 1280, height: 720 }
    });
    
    const page = await context.newPage();
    
    // 隐藏自动化标记
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    });
    
    // 访问页面
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    
    // 等待页面加载
    await page.waitForTimeout(5000);
    
    // 截图
    const screenshotPath = path.join(outputDir, `dji_${name}.png`);
    await page.screenshot({ 
      path: screenshotPath, 
      fullPage: false,
      clip: { x: 0, y: 0, width: 1280, height: 720 }
    });
    
    console.log(`✅ Saved: ${screenshotPath}`);
    return { success: true, path: screenshotPath };
    
  } catch (error) {
    console.error(`❌ Error capturing ${name}:`, error.message);
    return { success: false, error: error.message };
  } finally {
    await browser.close();
  }
}

async function main() {
  const results = [];
  
  for (const product of products) {
    const result = await captureProduct(product.url, product.name);
    results.push({ name: product.name, ...result });
    
    // 随机延迟，避免被检测
    if (product !== products[products.length - 1]) {
      const delay = 3000 + Math.random() * 2000;
      console.log(`Waiting ${Math.round(delay)}ms...`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  
  console.log('\n=== Capture Results ===');
  results.forEach(r => {
    if (r.success) {
      console.log(`✅ ${r.name}: ${r.path}`);
    } else {
      console.log(`❌ ${r.name}: ${r.error}`);
    }
  });
}

main().catch(console.error);
