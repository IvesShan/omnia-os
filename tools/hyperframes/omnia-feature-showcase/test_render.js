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
  
  // Open the HyperFrames composition page
  await page.goto('http://localhost:8765', { waitUntil: 'networkidle2', timeout: 15000 });
  await sleep(3000);
  
  // Take a screenshot of the main page to see actual rendering
  await page.screenshot({ path: 'out/test-real-ui.png' });
  console.log('✅ test-real-ui.png saved');
  
  // Also test: load a scene HTML directly
  await page.goto('file:///home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/compositions/scene-memory.html', { waitUntil: 'load', timeout: 10000 });
  await sleep(2000);
  await page.screenshot({ path: 'out/test-scene-memory.png' });
  console.log('✅ test-scene-memory.png saved');
  
  await browser.close();
  console.log('Done!');
})();
