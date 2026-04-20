const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function loginBaidu() {
  console.log('🚀 重新启动百度百科登录...');
  
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
    
    // 2. 点击"账号登录"标签
    console.log('🖱️ 点击账号登录...');
    await page.click('.account-login, [data-type="account"], .tang-pass-footerBarULogin, text=账号登录');
    await page.waitForTimeout(2000);
    
    // 3. 输入账号
    console.log('⌨️ 输入账号...');
    await page.fill('#TANGRAM__PSP_4__userName, input[name="userName"]', USERNAME);
    await page.waitForTimeout(500);
    
    // 4. 输入密码
    console.log('⌨️ 输入密码...');
    await page.fill('#TANGRAM__PSP_4__password, input[name="password"]', PASSWORD);
    await page.waitForTimeout(500);
    
    // 5. 截图查看
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_form.png' });
    console.log('📸 已保存登录表单截图');
    
    // 6. 点击登录
    console.log('🖱️ 点击登录按钮...');
    await page.click('#TANGRAM__PSP_4__submit, .pass-button-submit');
    await page.waitForTimeout(5000);
    
    // 7. 检查是否需要验证码
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_after_login.png', fullPage: true });
    
    const pageContent = await page.content();
    if (pageContent.includes('验证码') || pageContent.includes('captcha')) {
      console.log('🔐 需要验证码！');
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_need_captcha.png' });
      console.log('📸 已保存验证码截图，请查看并告知验证码');
      
      // 等待用户输入验证码
      console.log('⏳ 等待验证码（请在飞书回复）...');
      // 这里会暂停等待
    } else {
      console.log('✅ 登录成功！');
      
      // 8. 访问百度百科创建词条
      await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_wiki_page.png', fullPage: true });
    }
    
    // 保持浏览器打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_error.png' });
  }
}

loginBaidu();
