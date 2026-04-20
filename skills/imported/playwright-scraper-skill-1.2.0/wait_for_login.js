const { chromium } = require('playwright');
const fs = require('fs');

async function waitForLogin() {
  console.log('🚀 启动等待登录流程...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 100
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问百度登录页
    console.log('📱 访问百度登录页，请扫码...');
    await page.goto('https://passport.baidu.com/v2/?login');
    await page.waitForTimeout(3000);
    
    // 2. 截图显示二维码
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/qr_code.png' });
    console.log('📸 已保存二维码截图');
    
    // 3. 等待登录成功（轮询检查）
    console.log('⏳ 等待扫码登录...');
    console.log('📱 请使用百度APP扫描二维码');
    console.log('✅ 登录成功后，告诉我，我继续操作');
    
    // 轮询等待登录
    let loggedIn = false;
    let attempts = 0;
    const maxAttempts = 60; // 最多等待5分钟
    
    while (!loggedIn && attempts < maxAttempts) {
      await page.waitForTimeout(5000);
      attempts++;
      
      // 检查是否已登录
      const url = page.url();
      if (!url.includes('passport.baidu.com')) {
        console.log('✅ 检测到登录成功！');
        loggedIn = true;
        break;
      }
      
      console.log(`⏳ 等待中... (${attempts}/${maxAttempts})`);
    }
    
    if (loggedIn) {
      console.log('🎉 登录成功，开始创建百度百科词条...');
      
      // 4. 访问百度百科
      await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/baidu_after_login.png', fullPage: true });
      
      console.log('📸 已保存百度百科页面');
      console.log('✅ 请检查页面，确认已登录');
      
      // 保持打开，等待后续指令
      await new Promise(() => {});
    } else {
      console.log('⏰ 等待超时，请重新运行脚本');
    }
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
  }
}

waitForLogin();
