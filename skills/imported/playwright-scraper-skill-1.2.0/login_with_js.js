const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function solveWithJS() {
  console.log('🚀 使用JavaScript注入方式登录...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 100
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问百度百科
    console.log('📱 访问百度百科...');
    await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
    await page.waitForTimeout(5000);
    
    // 2. 截图查看
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/step1_initial.png', fullPage: true });
    console.log('📸 已保存初始页面');
    
    // 3. 查找登录按钮并点击
    console.log('🔍 查找登录按钮...');
    
    // 尝试多种方式找到登录按钮
    const loginSelectors = [
      'a[href*="login"]',
      '.login',
      '[name="tj_login"]',
      'text=登录',
      '.user-login',
      '#login'
    ];
    
    let loginClicked = false;
    for (const selector of loginSelectors) {
      try {
        const btn = await page.$(selector);
        if (btn) {
          await btn.click({ timeout: 5000 });
          console.log(`✅ 使用选择器点击登录: ${selector}`);
          loginClicked = true;
          break;
        }
      } catch (e) {}
    }
    
    if (!loginClicked) {
      console.log('⚠️ 未找到登录按钮，尝试JavaScript点击...');
      await page.evaluate(() => {
        // 查找包含"登录"文本的元素
        const links = document.querySelectorAll('a');
        for (const link of links) {
          if (link.textContent.includes('登录') || link.textContent.includes('Login')) {
            link.click();
            return true;
          }
        }
        return false;
      });
    }
    
    await page.waitForTimeout(5000);
    
    // 4. 截图登录弹窗
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/step2_login_popup.png', fullPage: true });
    console.log('📸 已保存登录弹窗');
    
    // 5. 使用JavaScript直接操作DOM
    console.log('🔧 使用JavaScript直接填写表单...');
    
    await page.evaluate((username, password) => {
      // 先点击账号登录标签
      const tabs = document.querySelectorAll('li, .tab-item, [role="tab"]');
      for (const tab of tabs) {
        if (tab.textContent && tab.textContent.includes('账号登录')) {
          tab.click();
          break;
        }
      }
      
      // 等待一下
      return new Promise(resolve => setTimeout(resolve, 1000));
    }, USERNAME, PASSWORD);
    
    await page.waitForTimeout(2000);
    
    // 6. 填写账号密码
    console.log('⌨️ 填写账号密码...');
    
    await page.evaluate((username, password) => {
      // 查找所有输入框
      const inputs = document.querySelectorAll('input');
      
      inputs.forEach(input => {
        // 账号输入框
        if (input.type === 'text' && (input.name === 'userName' || input.placeholder && input.placeholder.includes('手机号'))) {
          input.value = username;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          console.log('已填写账号');
        }
        
        // 密码输入框
        if (input.type === 'password') {
          input.value = password;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          console.log('已填写密码');
        }
      });
    }, USERNAME, PASSWORD);
    
    await page.waitForTimeout(2000);
    
    // 7. 截图检查
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/step3_filled.png', fullPage: true });
    console.log('📸 已保存填写后截图');
    
    // 8. 点击登录按钮
    console.log('🖱️ 点击登录...');
    await page.evaluate(() => {
      const submitBtn = document.querySelector('input[type="submit"], .pass-button-submit, button[type="submit"]');
      if (submitBtn) {
        submitBtn.click();
        return true;
      }
      return false;
    });
    
    await page.waitForTimeout(5000);
    
    // 9. 检查登录结果
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/step4_after_login.png', fullPage: true });
    console.log('📸 已保存登录后截图');
    
    // 10. 检查是否需要验证码
    const content = await page.content();
    if (content.includes('验证码') || content.includes('captcha') || content.includes('验证')) {
      console.log('🔐 需要验证码！请查看 step4_after_login.png');
      
      // 等待用户输入
      console.log('⏳ 等待验证码...');
      // 这里会暂停
    } else {
      console.log('✅ 登录流程完成！');
    }
    
    // 保持浏览器打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/error_final.png', fullPage: true });
  }
}

solveWithJS();
