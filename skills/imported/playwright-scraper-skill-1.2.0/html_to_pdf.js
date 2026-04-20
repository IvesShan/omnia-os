const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // 设置视口为1280x720
  await page.setViewportSize({
    width: 1280,
    height: 720
  });
  
  // 加载HTML文件
  const htmlPath = path.resolve('/home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_配图版.html');
  await page.goto('file://' + htmlPath, {
    waitUntil: 'networkidle',
    timeout: 60000
  });
  
  // 等待图片加载
  await page.waitForTimeout(3000);
  
  // 生成PDF
  await page.pdf({
    path: '/home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_最终版.pdf',
    width: '1280px',
    height: '720px',
    printBackground: true
  });
  
  console.log('✅ PDF生成成功!');
  console.log('📄 文件路径: /home/uosun-shan/.openclaw/workspace/projects/drone_course/Day01_PPT_最终版.pdf');
  
  await browser.close();
})();
