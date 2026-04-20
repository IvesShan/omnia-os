const { chromium } = require('playwright');

async function searchAndCreateWiki() {
  console.log('🚀 搜索词条并创建...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/');
    await page.waitForTimeout(3000);
    
    // 2. 搜索词条
    console.log('🔍 搜索"南京物熵科技有限公司"...');
    await page.fill('input[name="word"], .search-input, [placeholder*="搜索"]', '南京物熵科技有限公司');
    await page.waitForTimeout(500);
    await page.click('button[type="submit"], .search-btn, text=搜索').catch(() => {
      return page.keyboard.press('Enter');
    });
    
    await page.waitForTimeout(5000);
    
    // 3. 截图查看结果
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/search_result.png', fullPage: true });
    console.log('📸 已保存搜索结果');
    
    // 4. 检查页面内容
    const content = await page.content();
    const url = page.url();
    
    console.log('当前URL:', url);
    
    if (url.includes('baike.baidu.com/item')) {
      // 词条已存在
      console.log('ℹ️ 词条已存在，检查是否有"我来完善"按钮');
      
      if (content.includes('我来完善') || content.includes('编辑')) {
        console.log('✅ 找到编辑按钮！');
        
        // 点击编辑
        await page.click('text=我来完善').catch(() => {
          return page.click('text=编辑');
        });
        
        await page.waitForTimeout(3000);
        await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/edit_mode.png', fullPage: true });
        console.log('📸 已进入编辑模式');
      } else {
        console.log('ℹ️ 词条已存在，可能不需要编辑');
      }
    } else if (content.includes('创建词条') || content.includes('暂无')) {
      // 词条不存在，可以创建
      console.log('✅ 词条不存在，可以创建！');
      
      // 查找创建词条按钮
      await page.click('text=创建词条').catch(() => {
        console.log('尝试其他方式创建...');
      });
      
      await page.waitForTimeout(3000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/create_mode.png', fullPage: true });
      console.log('📸 已进入创建模式');
    }
    
    // 5. 保持打开
    console.log('⏳ 浏览器保持打开，等待后续操作...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/search_error.png' });
  }
}

searchAndCreateWiki();
