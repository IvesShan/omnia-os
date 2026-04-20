const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function showAccountLogin() {
  console.log('🚀 启动账号密码登录界面...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问百度登录页
    console.log('📱 访问百度登录页...');
    await page.goto('https://passport.baidu.com/v2/?login');
    await page.waitForTimeout(3000);
    
    // 2. 点击"用户名登录"
    console.log('🖱️ 点击"用户名登录"...');
    await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const el of elements) {
        if (el.textContent && el.textContent.trim() === '用户名登录') {
          el.click();
          return;
        }
      }
    });
    
    await page.waitForTimeout(3000);
    
    // 3. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/account_login_form.png' });
    console.log('📸 已显示账号登录界面');
    
    // 4. 填写账号
    console.log('⌨️ 填写账号...');
    await page.evaluate((username) => {
      const inputs = document.querySelectorAll('input[type="text"]');
      for (const input of inputs) {
        if (input.placeholder?.includes('手机号') || input.id?.includes('userName')) {
          input.value = username;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          break;
        }
      }
    }, USERNAME);
    
    await page.waitForTimeout(500);
    
    // 5. 填写密码
    console.log('⌨️ 填写密码...');
    await page.evaluate((password) => {
      const inputs = document.querySelectorAll('input[type="password"]');
      for (const input of inputs) {
        input.value = password;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        break;
      }
    }, PASSWORD);
    
    await page.waitForTimeout(500);
    
    // 6. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/account_filled.png' });
    console.log('📸 已填写账号密码');
    console.log('✅ 现在你可以：');
    console.log('   1. 检查是否需要验证码');
    console.log('   2. 点击登录按钮');
    console.log('   3. 告诉我登录结果');
    
    // 保持打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
  }
}

showAccountLogin();
