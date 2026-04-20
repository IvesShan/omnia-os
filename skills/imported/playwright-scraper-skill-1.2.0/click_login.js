const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

async function clickAndLogin() {
  console.log('🚀 尝试点击用户名登录...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 300
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问登录页
    console.log('📱 访问登录页...');
    await page.goto('https://passport.baidu.com/v2/?login');
    await page.waitForTimeout(3000);
    
    // 2. 截图查看初始状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step1_initial.png' });
    
    // 3. 查找并点击"用户名登录"
    console.log('🖱️ 点击用户名登录...');
    
    // 尝试多种方式
    const clicked = await page.evaluate(() => {
      // 方法1: 查找包含"用户名登录"文本的元素
      const elements = document.querySelectorAll('a, span, p, div');
      for (const el of elements) {
        if (el.textContent.includes('用户名登录')) {
          el.click();
          return 'clicked via text';
        }
      }
      
      // 方法2: 查找特定的class或id
      const loginLink = document.querySelector('.tang-pass-footerBarULogin, .pass-login-switch, [data-type="normal"]');
      if (loginLink) {
        loginLink.click();
        return 'clicked via selector';
      }
      
      return 'not found';
    });
    
    console.log('点击结果:', clicked);
    await page.waitForTimeout(3000);
    
    // 4. 截图查看是否切换成功
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step2_after_click.png' });
    
    // 5. 检查是否有账号输入框
    const hasForm = await page.evaluate(() => {
      const usernameInput = document.getElementById('TANGRAM__PSP_3__userName') || 
                            document.getElementById('TANGRAM__PSP_4__userName');
      return usernameInput !== null;
    });
    
    console.log('是否有账号输入框:', hasForm);
    
    if (hasForm) {
      console.log('✅ 找到账号输入框，准备填写...');
      
      // 6. 填写账号
      await page.evaluate((username) => {
        const input = document.getElementById('TANGRAM__PSP_3__userName') || 
                      document.getElementById('TANGRAM__PSP_4__userName');
        if (input) {
          input.value = username;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, USERNAME);
      
      await page.waitForTimeout(1000);
      
      // 7. 填写密码
      await page.evaluate((password) => {
        const input = document.getElementById('TANGRAM__PSP_3__password') || 
                      document.getElementById('TANGRAM__PSP_4__password');
        if (input) {
          input.value = password;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, PASSWORD);
      
      await page.waitForTimeout(1000);
      
      // 8. 截图
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step3_filled.png' });
      console.log('📸 已填写账号密码');
      
      // 9. 点击登录
      await page.evaluate(() => {
        const btn = document.getElementById('TANGRAM__PSP_3__submit') || 
                    document.getElementById('TANGRAM__PSP_4__submit');
        if (btn) btn.click();
      });
      
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step4_result.png' });
      console.log('📸 已点击登录');
      
      // 10. 访问百度百科
      await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
      await page.waitForTimeout(5000);
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/step5_baidu.png', fullPage: true });
      console.log('📸 已访问百度百科');
      
    } else {
      console.log('⚠️ 未找到账号输入框，可能需要其他操作');
    }
    
    // 保持打开
    console.log('⏳ 完成，保持浏览器打开...');
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/error_click.png' });
  }
}

clickAndLogin();
