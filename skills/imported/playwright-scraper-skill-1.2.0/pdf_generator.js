const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    headless: true
  });
  
  const page = await browser.newPage();
  
  // 设置视口
  await page.setViewportSize({
    width: 1280,
    height: 720
  });
  
  // 加载HTML文件 - 使用干净版
  const htmlPath = path.resolve('/home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_干净版.html');
  await page.goto('file://' + htmlPath, {
    waitUntil: 'networkidle',
    timeout: 60000
  });
  
  // 等待图片加载
  await page.waitForTimeout(3000);
  
  // 生成PDF
  await page.pdf({
    path: '/home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_干净版.pdf',
    width: '1280px',
    height: '720px',
    printBackground: true
  });
  
  console.log('✅ PDF生成成功!');
  console.log('📄 文件路径: /home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_干净版.pdf');
  
  await browser.close();
})();