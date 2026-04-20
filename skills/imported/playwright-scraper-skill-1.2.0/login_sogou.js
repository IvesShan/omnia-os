const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 访问搜狗百科
  await page.goto('https://baike.sogou.com/');
  console.log('请手动登录账号: 18912958280 / s46853622');
  console.log('登录完成后按回车继续...');
  
  // 等待用户登录
  await page.waitForTimeout(30000);
  
  // 检查是否登录成功
  const isLoggedIn = await page.evaluate(() => {
    return document.body.innerText.includes('退出') || document.body.innerText.includes('个人中心');
  });
  
  if (isLoggedIn) {
    console.log('登录成功！');
    // 访问创建词条页面
    await page.goto('https://baike.sogou.com/create/');
    await page.waitForTimeout(5000);
  } else {
    console.log('未检测到登录状态，请手动完成登录');
  }
  
  // 保持浏览器打开
  await new Promise(() => {});
})();
