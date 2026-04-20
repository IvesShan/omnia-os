const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function loginBaidu() {
  console.log('🚀 启动百度百科登录...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 直接访问百度百科目标词条页
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
    await page.waitForTimeout(5000);
    
    // 2. 截图查看当前状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_current.png', fullPage: true });
    console.log('📸 已保存当前页面截图');
    
    // 3. 检查页面内容
    const content = await page.content();
    console.log('页面内容检查中...');
    
    // 4. 如果需要登录，点击登录按钮
    if (content.includes('登录') || content.includes('login')) {
      console.log('🔐 需要登录，点击登录按钮...');
      
      // 尝试多种方式找到登录按钮
      const loginBtn = await page.$('a:has-text("登录"), .login, [name="tj_login"]');
      if (loginBtn) {
        await loginBtn.click();
        await page.waitForTimeout(3000);
      }
      
      // 5. 截图登录弹窗
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_popup.png' });
      console.log('📸 已保存登录弹窗截图');
      
      // 6. 查找并点击"账号登录"
      const tabs = await page.$$('li, .tab-item, [role="tab"]');
      for (const tab of tabs) {
        const text = await tab.textContent();
        if (text && text.includes('账号登录')) {
          await tab.click();
          console.log('🖱️ 点击账号登录');
          await page.waitForTimeout(2000);
          break;
        }
      }
      
      // 7. 输入账号密码
      console.log('⌨️ 输入账号密码...');
      await page.fill('input[name="userName"], #TANGRAM__PSP_4__userName', USERNAME);
      await page.waitForTimeout(500);
      await page.fill('input[name="password"], #TANGRAM__PSP_4__password', PASSWORD);
      await page.waitForTimeout(500);
      
      // 8. 截图检查
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_filled.png' });
      
      // 9. 点击登录
      console.log('🖱️ 点击登录...');
      await page.click('input[type="submit"], #TANGRAM__PSP_4__submit, .pass-button-submit');
      await page.waitForTimeout(5000);
      
      // 10. 检查是否需要验证码
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_after_submit.png', fullPage: true });
      
      const afterContent = await page.content();
      if (afterContent.includes('验证码')) {
        console.log('🔐 需要验证码！请查看截图并告知验证码');
      } else {
        console.log('✅ 登录成功！');
      }
    }
    
    // 保持浏览器打开
    console.log('⏳ 等待操作...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_error_v2.png' });
  }
}

loginBaidu();
