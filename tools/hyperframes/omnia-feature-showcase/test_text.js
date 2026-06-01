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
  
  // Load the actual WebUI
  await page.goto('http://localhost:8765', { waitUntil: 'networkidle2', timeout: 15000 });
  await sleep(3000);
  
  // Check what text is visible on the page
  const textContent = await page.evaluate(() => {
    const body = document.body.innerText;
    return body.substring(0, 500);
  });
  console.log('Page text:', textContent);
  
  // Check if there are any Chinese characters
  const hasChinese = await page.evaluate(() => {
    const text = document.body.innerText;
    const chineseRegex = /[\u4e00-\u9fff]/;
    return chineseRegex.test(text);
  });
  console.log('Has Chinese text:', hasChinese);
  
  await browser.close();
})();
