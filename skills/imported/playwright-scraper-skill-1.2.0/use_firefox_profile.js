const { firefox } = require('playwright');
const path = require('path');

const FIREFOX_PROFILE = '/home/uosun-shan/snap/firefox/common/.mozilla/firefox/cpctyrvl.default';

async function useFirefoxProfile() {
  console.log('🚀 尝试使用Firefox配置文件...');
  
  try {
    // 尝试启动Firefox并指定profile
    const browser = await firefox.launch({
      headless: false,
      slowMo: 200,
      args: [
        '-profile', FIREFOX_PROFILE
      ]
    });
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    // 访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/');
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/firefox_baidu.png', fullPage: true });
    console.log('📸 已保存截图');
    
    // 检查是否已登录
    const content = await page.content();
    if (content.includes('个人中心') || content.includes('退出')) {
      console.log('✅ Firefox已保持登录状态！');
      
      // 搜索词条
      await page.fill('input[name="word"]', '南京物熵科技有限公司');
      await page.press('input[name="word"]', 'Enter');
      await page.waitForTimeout(5000);
      
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/firefox_search.png', fullPage: true });
      console.log('📸 已保存搜索结果');
    } else {
      console.log('⚠️ 未检测到登录状态');
    }
    
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    console.log('⚠️ Firefox profile方式失败');
  }
}

useFirefoxProfile();
