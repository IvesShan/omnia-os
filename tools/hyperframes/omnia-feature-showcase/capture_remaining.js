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
  await page.goto('http://localhost:8765', { waitUntil: 'networkidle2', timeout: 15000 });
  await sleep(3000);
  
  // For streaming chat - stay on main chat view (default state)
  await page.screenshot({ path: 'assets/real-ui-streaming.png' });
  console.log('✅ real-ui-streaming.png (default chat view)');
  
  // For multi-turn - click on chat area
  try {
    const chatInput = await page.$('textarea, input[type="text"]');
    if (chatInput) {
      await chatInput.click();
      await sleep(500);
    }
    await page.screenshot({ path: 'assets/real-ui-multi-turn.png' });
    console.log('✅ real-ui-multi-turn.png (chat with input focus)');
  } catch(e) { console.log('⚠️ multi-turn:', e.message); }
  
  await browser.close();
  console.log('Done!');
})();
