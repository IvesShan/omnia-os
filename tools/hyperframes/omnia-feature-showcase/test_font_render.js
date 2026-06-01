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
  
  // Load index.html which has all scenes
  await page.goto('file:///home/shan/omnia-os/tools/hyperframes/omnia-feature-showcase/index.html', { waitUntil: 'load', timeout: 10000 });
  await sleep(3000);
  
  // Screenshot the full page
  await page.screenshot({ path: 'output/test-index-render.png' });
  console.log('✅ test-index-render.png');
  
  // Check if fonts loaded
  const fontsLoaded = await page.evaluate(() => {
    return document.fonts.ready.then(() => {
      const fonts = [];
      document.fonts.forEach(f => fonts.push(`${f.family} (${f.status})`));
      return fonts;
    });
  });
  console.log('Fonts:', fontsLoaded);
  
  // Check if any text is visible
  const textContent = await page.evaluate(() => {
    const texts = [];
    document.querySelectorAll('.callout-title, .callout-desc, .callout-stats span').forEach(el => {
      texts.push(el.textContent + ' -> ' + getComputedStyle(el).fontFamily);
    });
    return texts;
  });
  console.log('Text elements:', textContent);
  
  await browser.close();
})();
