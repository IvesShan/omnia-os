const puppeteer = require('puppeteer');
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await puppeteer.launch({ 
    headless: 'new', 
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-gpu'] 
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  // Load the snapshot PNG and check for text
  await page.goto('file:///home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/snapshots/frame-00-at-2.0s.png', { waitUntil: 'load', timeout: 10000 });
  await sleep(1000);
  
  // Take a screenshot to verify
  await page.screenshot({ path: '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/snapshots/verify-frame-00.png' });
  console.log('✅ 验证截图已保存');
  
  // Now load the actual HTML file through HyperFrames preview
  // First check if HyperFrames preview server is running
  try {
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle2', timeout: 5000 });
    const text = await page.evaluate(() => document.body.innerText.substring(0, 300));
    console.log('HyperFrames preview 文本:', text);
  } catch(e) {
    console.log('HyperFrames preview 未运行:', e.message.substring(0, 100));
  }
  
  await browser.close();
})();
