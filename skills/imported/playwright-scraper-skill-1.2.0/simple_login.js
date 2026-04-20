const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function simpleLogin() {
  console.log('🚀 开始简化版登录流程...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 300
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 直接访问登录页
    console.log('📱 访问百度登录页...');
    await page.goto('https://passport.baidu.com/v2/?login');
    await page.waitForTimeout(5000);
    
    // 2. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_page.png', fullPage: true });
    console.log('📸 已截图，请查看');
    
    // 3. 点击账号登录
    console.log('🖱️ 点击账号登录...');
    const tabs = await page.$$('li');
    for (const tab of tabs) {
      const text = await tab.textContent();
      if (text && text.includes('账号登录')) {
        await tab.click();
        console.log('✅ 点击了账号登录');
        break;
      }
    }
    await page.waitForTimeout(2000);
    
    // 4. 找到输入框
    console.log('🔍 查找输入框...');
    
    // 获取所有输入框信息
    const inputs = await page.$$('input');
    console.log(`找到 ${inputs.length} 个输入框`);
    
    for (let i = 0; i < inputs.length; i++) {
      const type = await inputs[i].getAttribute('type');
      const name = await inputs[i].getAttribute('name');
      const placeholder = await inputs[i].getAttribute('placeholder');
      const id = await inputs[i].getAttribute('id');
      console.log(`输入框 ${i}: type=${type}, name=${name}, placeholder=${placeholder}, id=${id}`);
    }
    
    // 5. 填写账号
    console.log('⌨️ 填写账号...');
    await page.locator('input[type="text"]').first().fill(USERNAME);
    await page.waitForTimeout(1000);
    
    // 6. 填写密码
    console.log('⌨️ 填写密码...');
    await page.locator('input[type="password"]').first().fill(PASSWORD);
    await page.waitForTimeout(1000);
    
    // 7. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_ready_to_submit.png', fullPage: true });
    console.log('📸 已保存准备提交截图');
    
    // 8. 点击登录
    console.log('🖱️ 点击登录...');
    await page.locator('input[type="submit"], button[type="submit"]').first().click();
    await page.waitForTimeout(5000);
    
    // 9. 检查结果
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_result.png', fullPage: true });
    console.log('📸 已保存登录结果');
    
    // 10. 获取页面文字检查是否需要验证码
    const bodyText = await page.locator('body').textContent();
    if (bodyText.includes('验证码') || bodyText.includes('验证')) {
      console.log('🔐 需要验证码！');
    } else {
      console.log('✅ 登录完成！');
      
      // 访问百度百科
      await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_wiki.png', fullPage: true });
    }
    
    // 保持打开
    console.log('⏳ 保持浏览器打开...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/error.png', fullPage: true });
  }
}

simpleLogin();
