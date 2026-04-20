const { chromium } = require('playwright');

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
    
    // 2. 截图初始状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step1_qrcode.png' });
    console.log('📸 当前是二维码界面');
    
    // 3. 点击"用户名登录"
    console.log('🖱️ 点击"用户名登录"...');
    
    // 查找并点击用户名登录链接
    await page.evaluate(() => {
      // 查找所有可能包含"用户名登录"的元素
      const allElements = document.querySelectorAll('*');
      for (const el of allElements) {
        if (el.textContent && el.textContent.trim() === '用户名登录') {
          el.click();
          console.log('找到并点击了用户名登录');
          return;
        }
      }
      
      // 如果没找到，尝试查找包含该文字的元素
      const links = document.querySelectorAll('a, span, p, div, li');
      for (const link of links) {
        if (link.textContent && link.textContent.includes('用户名登录')) {
          link.click();
          console.log('通过包含文字找到并点击');
          return;
        }
      }
    });
    
    await page.waitForTimeout(3000);
    
    // 4. 截图查看是否切换到账号登录
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step2_account_login.png' });
    console.log('📸 已切换到账号登录界面');
    
    // 5. 检查是否有账号输入框
    const hasUsernameField = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input');
      for (const input of inputs) {
        if (input.type === 'text' && (input.placeholder?.includes('手机号') || input.name === 'userName')) {
          return true;
        }
      }
      return false;
    });
    
    if (hasUsernameField) {
      console.log('✅ 成功显示账号密码输入框！');
      console.log('📱 现在可以输入：');
      console.log('   账号：18912958280');
      console.log('   密码：s46853622');
      
      // 6. 自动填写账号密码
      console.log('⌨️ 自动填写账号密码...');
      
      await page.evaluate((username, password) => {
        // 填写账号
        const usernameInputs = document.querySelectorAll('input[type="text"]');
        for (const input of usernameInputs) {
          if (input.placeholder?.includes('手机号') || input.name === 'userName' || input.id?.includes('userName')) {
            input.value = username;
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            console.log('已填写账号');
            break;
          }
        }
        
        // 填写密码
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        for (const input of passwordInputs) {
          input.value = password;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          console.log('已填写密码');
          break;
        }
      }, '18912958280', 's46853622');
      
      await page.waitForTimeout(1000);
      
      // 7. 截图显示已填写
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step3_filled_form.png' });
      console.log('📸 已填写账号密码');
      
      // 8. 查找登录按钮
      console.log('🔍 查找登录按钮...');
      const loginBtnInfo = await page.evaluate(() => {
        const btns = document.querySelectorAll('input[type="submit"], button[type="submit"], .pass-button-submit');
        const info = [];
        for (const btn of btns) {
          info.push({
            type: btn.type,
            class: btn.className,
            id: btn.id,
            value: btn.value,
            text: btn.textContent
          });
        }
        return info;
      });
      console.log('找到的登录按钮:', loginBtnInfo);
      
    } else {
      console.log('⚠️ 未找到账号输入框，可能需要手动点击');
    }
    
    console.log('✅ 账号密码登录界面已准备好！');
    console.log('🖱️ 你可以手动点击登录按钮，或告诉我让我点击');
    
    // 保持打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/error_account.png' });
  }
}

showAccountLogin();
