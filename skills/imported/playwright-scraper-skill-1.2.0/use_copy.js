const { firefox } = require('playwright');

const FIREFOX_COPY = '/tmp/firefox_copy';

async function useCopiedProfile() {
  console.log('🚀 使用复制的Firefox配置...');
  
  try {
    const context = await firefox.launchPersistentContext(FIREFOX_COPY, {
      headless: false,
      slowMo: 200,
      viewport: { width: 1280, height: 800 }
    });
    
    const page = await context.newPage();
    
    // 访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/');
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/copy_baidu.png', fullPage: true });
    console.log('📸 已保存截图');
    
    // 检查登录状态
    const content = await page.content();
    if (content.includes('个人中心') || content.includes('退出')) {
      console.log('✅ 已保持登录状态！');
      
      // 搜索词条
      console.log('🔍 搜索词条...');
      await page.fill('input[name="word"]', '南京物熵科技有限公司');
      await page.press('input[name="word"]', 'Enter');
      await page.waitForTimeout(5000);
      
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/copy_search.png', fullPage: true });
      console.log('📸 已保存搜索结果');
      
      // 查找创建词条按钮
      const hasCreate = await page.evaluate(() => {
        return document.body.innerText.includes('创建词条');
      });
      
      const hasEdit = await page.evaluate(() => {
        return document.body.innerText.includes('我来完善');
      });
      
      if (hasCreate) {
        console.log('✅ 找到创建词条按钮！');
        await page.click('text=创建词条');
      } else if (hasEdit) {
        console.log('✅ 找到编辑按钮！');
        await page.click('text=我来完善');
      }
      
      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/copy_edit.png', fullPage: true });
      console.log('📸 已进入编辑页面');
      
    } else {
      console.log('⚠️ 未检测到登录状态');
    }
    
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
  }
}

useCopiedProfile();
