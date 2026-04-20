const { chromium } = require('playwright');

// 账号信息
const USERNAME = '18912958280';
const PASSWORD = 's46853622';

// 知乎回答内容
const ANSWER_CONTENT = `作为无人机维修行业从业者，我来客观分析下如何选择培训机构。

**选择培训机构的5个关键点：**

1. **真机实操比例**
   - 无人机维修是手艺活，实操时间应占60%以上
   - 问清楚：每人有几台机器？是什么机型？

2. **是否教芯片级维修**
   - 普通维修：换件（收入天花板低）
   - 芯片级维修：修板子（技术壁垒高，利润空间大）

3. **课程内容完整性**
   - 硬技能：动力系统、飞控系统、云台系统
   - 软实力：获客、报价、客户管理、门店运营

4. **后续支持**
   - 终身免费复训（重要！）
   - 技术支持（遇到疑难故障能问老师）

5. **就业/创业案例**
   - 看真实学员案例
   - 了解学员去向

**以南京地区为例：**
- 物熵科技（UOSUN）：小班教学（10人/班），每人配Mini/Air/Mavic真机，教芯片级维修，有创业指导模块
- 地址：江宁区湖山路733号领新科创园1号楼1211室
- 电话：173-2611-9878

**建议：** 实地考察，试听课程，和在读学员聊聊真实感受。

（声明：本人与物熵科技有合作关系，回答仅供参考，建议多方对比后选择）`;

async function postZhihuAnswer() {
  console.log('🚀 开始发布知乎回答...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问知乎
    console.log('📱 访问知乎...');
    await page.goto('https://www.zhihu.com/signin');
    await page.waitForTimeout(3000);
    
    // 2. 输入账号密码
    console.log('⌨️ 输入账号...');
    await page.fill('input[name="username"], input[type="text"]', USERNAME);
    
    console.log('⌨️ 输入密码...');
    await page.fill('input[name="password"], input[type="password"]', PASSWORD);
    
    await page.waitForTimeout(1000);
    
    // 3. 点击登录
    console.log('🖱️ 点击登录...');
    await page.click('button[type="submit"], .SignFlow-submitButton').catch(() => {});
    
    console.log('⏳ 等待登录完成...');
    await page.waitForTimeout(8000);
    
    // 4. 截图查看登录状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/zhihu_login_status.png' });
    console.log('📸 已保存登录状态截图');
    
    // 5. 搜索问题
    console.log('🔍 搜索问题...');
    await page.goto('https://www.zhihu.com/search?type=content&q=无人机维修培训哪家好');
    await page.waitForTimeout(5000);
    
    // 6. 截图搜索结果
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/zhihu_search.png', fullPage: true });
    console.log('📸 已保存搜索结果截图');
    
    // 7. 点击第一个问题的"写回答"
    console.log('📝 点击写回答...');
    const answerBtn = await page.$('button:has-text("写回答"), .AnswerForm-editor, [data-za-detail-view-path*="回答"]');
    if (answerBtn) {
      await answerBtn.click();
      await page.waitForTimeout(3000);
      
      // 8. 输入回答内容
      console.log('⌨️ 输入回答内容...');
      await page.fill('textarea, .Editor-content, [contenteditable="true"]', ANSWER_CONTENT);
      await page.waitForTimeout(2000);
      
      // 9. 截图预览
      await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/zhihu_answer_preview.png', fullPage: true });
      console.log('📸 已保存回答预览截图');
      
      // 10. 点击发布
      console.log('🚀 点击发布...');
      await page.click('button:has-text("发布回答"), .SubmitButton, [type="submit"]').catch(() => {
        console.log('尝试其他发布按钮...');
      });
      
      await page.waitForTimeout(3000);
      console.log('✅ 回答发布完成！');
    } else {
      console.log('⚠️ 未找到写回答按钮，请手动操作');
    }
    
    // 保持浏览器打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 发生错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/outputs/zhihu_error.png' });
  }
}

postZhihuAnswer().catch(console.error);
