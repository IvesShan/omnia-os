const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();
  await page.goto('https://www.kdocs.cn/l/cn6S4ZvbWTf7', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(5000);
  const title = await page.title();
  const html = await page.content();
  await page.screenshot({ path: '/tmp/kdocs_screenshot.png', fullPage: true });
  console.log(JSON.stringify({ title, htmlLength: html.length, url: page.url() }));
  await browser.close();
})();
