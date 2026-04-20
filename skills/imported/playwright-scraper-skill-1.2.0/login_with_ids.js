const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function loginWithIDs() {
  console.log('🚀 使用精确ID定位登录...');
  
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
    
    // 2. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/login_start.png' });
    
    // 3. 点击账号登录标签
    console.log('🖱️ 点击账号登录...');
    await page.evaluate(() => {
      const tabs = document.querySelectorAll('li');
      for (const tab of tabs) {
        if (tab.textContent && tab.textContent.includes('账号登录')) {
          tab.click();
          return 'clicked';
        }
      }
      return 'not found';
    });
    await page.waitForTimeout(2000);
    
    // 4. 使用ID填写账号 - 强制填写
    console.log('⌨️ 填写账号...');
    await page.evaluate((username) => {
      const input = document.getElementById('TANGRAM__PSP_3__userName');
      if (input) {
        input.value = username;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'username filled';
      }
      return 'username not found';
    }, USERNAME);
    
    await page.waitForTimeout(1000);
    
    // 5. 使用ID填写密码
    console.log('⌨️ 填写密码...');
    await page.evaluate((password) => {
      const input = document.getElementById('TANGRAM__PSP_3__password');
      if (input) {
        input.value = password;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'password filled';
      }
      return 'password not found';
    }, PASSWORD);
    
    await page.waitForTimeout(1000);
    
    // 6. 截图检查
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/login_filled.png' });
    console.log('📸 已截图，请检查是否填写成功');
    
    // 7. 检查是否需要验证码
    const hasVerifyCode = await page.evaluate(() => {
      const input = document.getElementById('TANGRAM__PSP_3__verifyCode');
      return input && input.offsetParent !== null; // 检查是否可见
    });
    
    if (hasVerifyCode) {
      console.log('🔐 需要验证码！请查看截图并提供验证码');
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/login_captcha.png' });
      // 这里等待用户输入
    } else {
      console.log('✅ 无需验证码，准备提交...');
      
      // 8. 点击登录
      await page.evaluate(() => {
        const btn = document.getElementById('TANGRAM__PSP_3__submit');
        if (btn) {
          btn.click();
          return 'submitted';
        }
        return 'button not found';
      });
      
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/login_result.png' });
      console.log('📸 已保存登录结果');
      
      // 9. 访问百度百科
      await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/baidu_wiki.png', fullPage: true });
      console.log('📸 已保存百度百科页面');
    }
    
    // 保持打开
    console.log('⏳ 保持浏览器打开，等待操作...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/error.png' });
  }
}

loginWithIDs();
