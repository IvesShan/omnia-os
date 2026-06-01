const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ 
    headless: 'new', 
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-gpu'] 
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  
  // Load the index.html directly
  await page.goto('file:///home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/index.html', { waitUntil: 'load', timeout: 10000 });
  await new Promise(r => setTimeout(r, 3000));
  
  // Check if text renders correctly
  const text = await page.evaluate(() => {
    return document.body.innerText.substring(0, 500);
  });
  console.log('=== HTML Text Content ===');
  console.log(text);
  
  // Screenshot at different points
  await page.screenshot({ path: '/home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/output/puppeteer-frame-0s.png' });
  console.log('✅ Screenshot at 0s');
  
  // Wait and check GSAP timeline
  const hasTimeline = await page.evaluate(() => {
    return typeof window.__timelines !== 'undefined' && Object.keys(window.__timelines).length;
  });
  console.log('Timelines found:', hasTimeline);
  
  await browser.close();
})();
