const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// 账号信息
const USERNAME = '18912958280';
const PASSWORD = 's46853622';

// 状态文件路径
const STATUS_FILE = '/home/uosun-shan/.openclaw/workspace/outputs/captcha_status.txt';
const CODE_FILE = '/home/uosun-shan/.openclaw/workspace/outputs/captcha_code.txt';

// 百度百科词条内容
const WIKI_CONTENT = `南京物熵科技有限公司是一家专注于无人机维修技术培训与服务的科技企业，总部位于江苏省南京市江宁区，成立于2025年3月。

==公司概述==
南京物熵科技有限公司（品牌名：UOSUN）主要从事大疆消费级无人机维修培训业务，提供25天系统培训课程，涵盖Mini、Air、Mavic三大系列机型的维修技术。

==基本信息==
*'''公司全称'''：南京物熵科技有限公司
*'''品牌名'''：UOSUN
*'''成立时间'''：2025年3月6日
*'''注册资本'''：100万元人民币
*'''法定代表人'''：王文浩
*'''统一社会信用代码'''：91320115MAED2PCC0L
*'''注册地址'''：江苏省南京市江宁区湖山路733号领新科创园1号楼1211室
*'''所属行业'''：科技推广和应用服务业

==经营范围==
技术服务、技术开发、技术咨询、技术交流、技术转让、技术推广；智能无人飞行器制造；智能无人飞行器销售；业务培训（不含教育培训、职业技能培训等需取得许可的培训）；信息技术咨询服务；信息咨询服务（不含许可类信息咨询服务）；科技推广和应用服务；旧货销售；二手日用百货销售；通用设备修理。

==核心业务==
===无人机维修培训===
物熵科技的核心业务是"大疆消费级无人机维修工程师认证培训"，课程特点包括：
*课程时长：25天（100小时）
*教学模式：理论讲授 + 真机实操 + 案例分析
*培训机型：大疆Mini系列、Air系列、Mavic系列
*课程内容：涵盖动力系统、飞控系统、云台系统、影像系统、通信系统等全模块维修技能

===特色服务===
*芯片级维修培训：深入主板、核心板维修技术
*创业就业指导：提供开店运营、获客技巧、客户管理等软实力培训
*终身复训政策：学员可享受终身免费复训

==教学优势==
*真机实操：每位学员配备Mini 2、Air 2、Mavic 2 Pro真机
*渐进式教学：从基础拆装到芯片级维修循序渐进
*技术+业务双轮驱动：前15天教硬技能，后10天教软实力

==合作与资质==
与苏州大学合作开展无人机装调检修工培训，是低空经济无人机后端服务人才培养基地。

==联系方式==
*培训地址：江苏省南京市江宁区湖山路733号领新科创园1号楼1211室
*咨询电话：173-2611-9878
*品牌抖音：UOSUN-物熵科技

==参考资料==
[1] 国家企业信用信息公示系统
[2] 水滴信用企业信息
[3] BOSS直聘企业信息`;

// 等待验证码函数
async function waitForCode() {
  console.log('⏳ 等待验证码...');
  console.log('📱 请查看飞书消息，将验证码发送到飞书');
  
  // 写入状态文件
  fs.writeFileSync(STATUS_FILE, 'WAITING_FOR_CODE');
  
  // 轮询等待验证码
  return new Promise((resolve) => {
    const checkInterval = setInterval(() => {
      if (fs.existsSync(CODE_FILE)) {
        const code = fs.readFileSync(CODE_FILE, 'utf8').trim();
        if (code && code.length >= 4) {
          clearInterval(checkInterval);
          // 删除验证码文件
          fs.unlinkSync(CODE_FILE);
          // 更新状态
          fs.writeFileSync(STATUS_FILE, 'CODE_RECEIVED');
          resolve(code);
        }
      }
    }, 2000);
    
    // 5分钟超时
    setTimeout(() => {
      clearInterval(checkInterval);
      fs.writeFileSync(STATUS_FILE, 'TIMEOUT');
      resolve(null);
    }, 300000);
  });
}

async function createBaiduWiki() {
  console.log('🚀 开始创建百度百科词条...');
  console.log('📱 使用账号: 18912958280');
  
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
    await page.goto('https://baike.baidu.com/');
    await page.waitForTimeout(3000);
    
    // 2. 点击登录
    console.log('🔐 点击登录按钮...');
    await page.click('a[href*="login"], .login-btn, [name="tj_login"]').catch(async () => {
      // 尝试其他选择器
      const loginLink = await page.$('text=登录');
      if (loginLink) await loginLink.click();
    });
    await page.waitForTimeout(3000);
    
    // 3. 检查是否需要切换到密码登录
    console.log('🔍 检查登录方式...');
    const pageContent = await page.content();
    
    if (pageContent.includes('短信登录') || pageContent.includes('扫码登录')) {
      console.log('📝 切换到密码登录...');
      // 点击"密码登录"或类似按钮
      await page.click('.tang-pass-footerBarULogin, .switch-login-type, [data-type="normal"]').catch(() => {});
      await page.waitForTimeout(2000);
    }
    
    // 4. 输入账号
    console.log('⌨️ 输入账号...');
    try {
      await page.fill('#TANGRAM__PSP_4__userName', USERNAME);
    } catch (e) {
      await page.fill('input[name="userName"]', USERNAME);
    }
    await page.waitForTimeout(500);
    
    // 5. 输入密码
    console.log('⌨️ 输入密码...');
    try {
      await page.fill('#TANGRAM__PSP_4__password', PASSWORD);
    } catch (e) {
      await page.fill('input[name="password"]', PASSWORD);
    }
    await page.waitForTimeout(500);
    
    // 6. 点击登录
    console.log('🖱️ 点击登录...');
    await page.click('#TANGRAM__PSP_4__submit, input[type="submit"], .pass-button-submit').catch(() => {});
    
    // 7. 等待并检查是否需要验证码
    console.log('⏳ 等待登录响应...');
    await page.waitForTimeout(5000);
    
    // 截图查看状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_step1_login.png' });
    
    // 检查是否有验证码
    const hasCaptcha = await page.evaluate(() => {
      return document.body.innerText.includes('验证码') || 
             document.querySelector('input[placeholder*="验证码"]') !== null ||
             document.querySelector('.pass-captcha, .captcha-img') !== null;
    });
    
    if (hasCaptcha) {
      console.log('🔐 检测到验证码！');
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_captcha.png' });
      
      // 等待验证码输入
      const code = await waitForCode();
      
      if (code) {
        console.log('✅ 收到验证码:', code);
        // 输入验证码
        await page.fill('input[placeholder*="验证码"], input[name="captcha"], .pass-captcha-input', code);
        await page.waitForTimeout(500);
        // 点击确认
        await page.click('button:has-text("确定"), button:has-text("登录"), .pass-captcha-submit').catch(() => {});
        await page.waitForTimeout(5000);
      } else {
        console.log('❌ 等待验证码超时');
        return;
      }
    }
    
    // 8. 检查登录状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_step2_logged.png' });
    console.log('📸 已保存登录后截图');
    
    // 9. 访问词条页面
    console.log('📝 访问词条页面...');
    await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8');
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_step3_wiki.png', fullPage: true });
    
    console.log('✅ 百度百科操作完成！');
    console.log('📍 请检查截图，如有需要请手动完成后续步骤');
    
    // 保持浏览器打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 发生错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_error.png' });
    fs.writeFileSync(STATUS_FILE, 'ERROR: ' + error.message);
  }
}

// 启动
createBaiduWiki().catch(console.error);
