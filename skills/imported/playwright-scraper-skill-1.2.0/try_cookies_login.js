const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Firefox cookies路径
const FIREFOX_PROFILE = '/home/uosun-shan/snap/firefox/common/.mozilla/firefox/cpctyrvl.default';
const COOKIES_DB = path.join(FIREFOX_PROFILE, 'cookies.sqlite');

async function tryLoginWithCookies() {
  console.log('🚀 尝试使用Firefox登录状态...');
  
  // 检查cookies文件是否存在
  if (!fs.existsSync(COOKIES_DB)) {
    console.log('❌ 未找到cookies文件');
    return;
  }
  
  console.log('✅ 找到Firefox cookies');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 直接访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
    await page.waitForTimeout(5000);
    
    // 2. 截图查看状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/baidu_check_login.png', fullPage: true });
    console.log('📸 已截图检查登录状态');
    
    // 3. 检查页面内容
    const content = await page.content();
    const url = page.url();
    
    console.log('当前URL:', url);
    
    if (content.includes('个人中心') || content.includes('退出') || !content.includes('登录')) {
      console.log('✅ 检测到已登录状态！');
      
      // 4. 检查是否可以创建/编辑词条
      if (content.includes('创建词条') || content.includes('我来完善')) {
        console.log('📝 可以创建/编辑词条！');
        
        // 点击创建词条
        await page.click('text=创建词条').catch(() => {
          console.log('尝试点击"我来完善"...');
          return page.click('text=我来完善');
        });
        
        await page.waitForTimeout(3000);
        await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/baidu_edit_page.png', fullPage: true });
        console.log('📸 已进入编辑页面');
        
        // 5. 填写词条内容
        console.log('📝 准备填写词条内容...');
        // 这里需要等待用户确认编辑界面已打开
        
      } else {
        console.log('ℹ️ 词条已存在或需要其他操作');
      }
    } else {
      console.log('⚠️ 未检测到登录状态，可能需要重新登录');
    }
    
    // 保持打开
    console.log('⏳ 保持浏览器打开...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/error_cookies.png' });
  }
}

tryLoginWithCookies();
