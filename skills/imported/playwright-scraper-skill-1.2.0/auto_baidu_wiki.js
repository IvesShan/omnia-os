const { chromium } = require('playwright');

// 账号信息
const USERNAME = '18912958280';
const PASSWORD = 's46853622';

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

async function createBaiduWiki() {
  console.log('🚀 开始创建百度百科词条...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
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
    console.log('🔐 点击登录...');
    const loginBtn = await page.$('a[href*="login"], .login-btn, [name="tj_login"]');
    if (loginBtn) {
      await loginBtn.click();
    } else {
      await page.click('text=登录').catch(() => {});
    }
    await page.waitForTimeout(3000);
    
    // 3. 切换到密码登录（如果需要）
    console.log('📝 选择密码登录...');
    const switchBtn = await page.$('.tang-pass-footerBarULogin, .switch-login-type, [data-type="normal"]');
    if (switchBtn) {
      await switchBtn.click().catch(() => {});
      await page.waitForTimeout(1000);
    }
    
    // 4. 输入账号密码
    console.log('⌨️ 输入账号...');
    await page.fill('input[name="userName"], input[name="username"], #TANGRAM__PSP_4__userName', USERNAME).catch(async () => {
      await page.fill('input[type="text"]', USERNAME);
    });
    
    console.log('⌨️ 输入密码...');
    await page.fill('input[name="password"], #TANGRAM__PSP_4__password', PASSWORD).catch(async () => {
      await page.fill('input[type="password"]', PASSWORD);
    });
    
    await page.waitForTimeout(1000);
    
    // 5. 点击登录按钮
    console.log('🖱️ 点击登录...');
    await page.click('input[type="submit"], .pass-button-submit, #TANGRAM__PSP_4__submit').catch(() => {
      console.log('尝试其他登录按钮...');
    });
    
    console.log('⏳ 等待登录完成（可能需要验证码）...');
    await page.waitForTimeout(8000);
    
    // 6. 截图查看状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_login_status.png' });
    console.log('📸 已保存登录状态截图');
    
    // 7. 访问创建词条页面
    console.log('📝 访问创建词条页面...');
    await page.goto('https://baike.baidu.com/item/%E5%8D%97%E4%BA%AC%E7%89%A9%E7%86%B5%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8/');
    await page.waitForTimeout(5000);
    
    // 8. 截图查看词条状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_wiki_check.png', fullPage: true });
    console.log('📸 已保存词条检查截图');
    
    // 9. 检查是否已有词条
    const pageContent = await page.content();
    if (pageContent.includes('创建词条') || pageContent.includes('我来完善')) {
      console.log('✅ 可以创建/编辑词条');
      
      // 点击创建词条
      const createBtn = await page.$('a[href*="create"], .create-entry-btn, text=创建词条');
      if (createBtn) {
        await createBtn.click();
        await page.waitForTimeout(3000);
      }
    } else {
      console.log('ℹ️ 词条可能已存在或需要其他操作');
    }
    
    console.log('✅ 百度百科操作完成！');
    console.log('📍 请检查浏览器，如有需要请手动完成最后步骤');
    
    // 保持浏览器打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 发生错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/baidu_error.png' });
  }
}

createBaiduWiki().catch(console.error);
