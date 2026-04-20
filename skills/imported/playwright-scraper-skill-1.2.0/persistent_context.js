const { firefox } = require('playwright');

const FIREFOX_PROFILE = '/home/uosun-shan/snap/firefox/common/.mozilla/firefox/cpctyrvl.default';

async function usePersistentContext() {
  console.log('🚀 使用Firefox持久化上下文...');
  
  try {
    // 使用launchPersistentContext
    const context = await firefox.launchPersistentContext(FIREFOX_PROFILE, {
      headless: false,
      slowMo: 200,
      viewport: { width: 1280, height: 800 }
    });
    
    const page = await context.newPage();
    
    // 访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/');
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/persistent_baidu.png', fullPage: true });
    console.log('📸 已保存截图');
    
    // 检查登录状态
    const content = await page.content();
    if (content.includes('个人中心') || content.includes('退出')) {
      console.log('✅ 已保持登录状态！');
      
      // 搜索词条
      await page.fill('input[name="word"]', '南京物熵科技有限公司');
      await page.press('input[name="word"]', 'Enter');
      await page.waitForTimeout(5000);
      
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/persistent_search.png', fullPage: true });
      console.log('📸 已保存搜索结果');
      
      // 查找创建词条按钮
      const hasCreateBtn = await page.evaluate(() => {
        return document.body.innerText.includes('创建词条') || 
               document.body.innerText.includes('我来完善');
      });
      
      if (hasCreateBtn) {
        console.log('✅ 可以创建/编辑词条！');
        
        // 点击创建词条
        await page.click('text=创建词条').catch(() => {
          return page.click('text=我来完善');
        });
        
        await page.waitForTimeout(3000);
        await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/persistent_edit.png', fullPage: true });
        console.log('📸 已进入编辑页面');
      }
    } else {
      console.log('⚠️ 未检测到登录状态，可能需要重新登录');
    }
    
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    console.log('⚠️ 可能Firefox正在被使用，无法同时打开');
  }
}

usePersistentContext();
