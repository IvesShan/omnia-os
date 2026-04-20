const { chromium } = require('playwright');

(async () => {
  const phoneNumber = process.env.PHONE || '18955054293';
  
  console.log('🚀 启动 DeepSeek 注册流程...');
  console.log(`📱 手机号: ${phoneNumber}`);
  
  const browser = await chromium.launch({ 
    headless: true,  // 无头模式
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-web-security',
      '--disable-features=IsolateOrigins,site-per-process',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ]
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  });
  
  // 注入反检测脚本
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
  });
  
  const page = await context.newPage();
  
  // 存储所有 API 请求信息
  const apiRequests = [];
  
  // 监听所有网络请求
  page.on('request', request => {
    const url = request.url();
    if (url.includes('deepseek.com') && (request.method() === 'POST' || url.includes('api'))) {
      const info = {
        url: url,
        method: request.method(),
        headers: request.headers(),
        postData: request.postData()
      };
      apiRequests.push(info);
      console.log(`📡 [请求] ${request.method()} ${url}`);
      if (request.postData()) {
        console.log(`   数据: ${request.postData()}`);
      }
    }
  });
  
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('deepseek.com') && (response.request().method() === 'POST' || url.includes('api'))) {
      console.log(`📡 [响应] ${response.status()} ${url}`);
      try {
        const body = await response.text();
        console.log(`   结果: ${body.substring(0, 300)}`);
      } catch (e) {}
    }
  });
  
  try {
    // 访问登录页面
    console.log('🌐 访问 DeepSeek 平台...');
    await page.goto('https://platform.deepseek.com/sign_in', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    console.log('✅ 页面加载完成');
    await page.waitForTimeout(2000);
    
    // 截图
    await page.screenshot({ path: './deepseek-step1.png' });
    console.log('📸 截图已保存: deepseek-step1.png');
    
    // 填写手机号
    console.log(`📝 填写手机号: ${phoneNumber}`);
    const phoneInput = await page.locator('input[placeholder*="手机号"]').first();
    await phoneInput.fill(phoneNumber);
    await page.waitForTimeout(1000);
    
    // 截图
    await page.screenshot({ path: './deepseek-step2.png' });
    console.log('📸 截图已保存: deepseek-step2.png');
    
    // 点击发送验证码按钮
    console.log('📨 点击"发送验证码"按钮...');
    const sendCodeBtn = await page.locator('text=发送验证码').first();
    await sendCodeBtn.click();
    
    // 等待响应
    await page.waitForTimeout(5000);
    
    // 截图
    await page.screenshot({ path: './deepseek-step3.png' });
    console.log('📸 截图已保存: deepseek-step3.png');
    
    // 输出所有捕获的 API 请求
    console.log('\n📋 捕获的 API 请求:');
    apiRequests.forEach((req, i) => {
      console.log(`\n${i + 1}. ${req.method} ${req.url}`);
      if (req.postData) {
        console.log(`   请求体: ${req.postData}`);
      }
    });
    
    // 保存 API 信息到文件
    const fs = require('fs');
    fs.writeFileSync('./deepseek-api-requests.json', JSON.stringify(apiRequests, null, 2));
    console.log('\n💾 API 请求已保存到: deepseek-api-requests.json');
    
    console.log('\n⏸️ 注册流程已暂停');
    console.log('📝 验证码已发送到手机号:', phoneNumber);
    console.log('💡 请向用户获取验证码后继续');
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: './deepseek-error.png' });
  }
  
  await browser.close();
  console.log('\n🔚 浏览器已关闭');
})();
