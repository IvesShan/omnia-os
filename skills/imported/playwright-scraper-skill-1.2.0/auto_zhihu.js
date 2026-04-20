const { chromium } = require('playwright');

const USERNAME = '18912958280';
const PASSWORD = 's46853622';

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

---
*声明：本人与物熵科技有合作关系，回答仅供参考*`;

async function postZhihu() {
  console.log('🚀 开始知乎自动化发布...');
  
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 200
  });
  
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    // 1. 访问知乎登录页
    console.log('📱 访问知乎...');
    await page.goto('https://www.zhihu.com/signin');
    await page.waitForTimeout(3000);
    
    // 2. 截图检查
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/zhihu_login.png' });
    console.log('📸 已保存知乎登录页');
    
    // 3. 填写账号密码（使用evaluate避免元素定位问题）
    console.log('⌨️ 填写账号密码...');
    await page.evaluate((u, p) => {
      const inputs = document.querySelectorAll('input');
      inputs.forEach(input => {
        if (input.type === 'text' || input.name === 'username') {
          input.value = u;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (input.type === 'password') {
          input.value = p;
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
      });
    }, USERNAME, PASSWORD);
    
    await page.waitForTimeout(1000);
    
    // 4. 点击登录
    console.log('🖱️ 点击登录...');
    await page.evaluate(() => {
      const btn = document.querySelector('button[type="submit"]');
      if (btn) btn.click();
    });
    
    await page.waitForTimeout(5000);
    
    // 5. 截图检查登录状态
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/zhihu_after_login.png', fullPage: true });
    console.log('📸 已保存登录后页面');
    
    // 6. 搜索问题
    console.log('🔍 搜索问题...');
    await page.goto('https://www.zhihu.com/search?type=content&q=无人机维修培训哪家好');
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/zhihu_search.png', fullPage: true });
    console.log('📸 已保存搜索结果');
    
    // 7. 尝试点击第一个问题的"写回答"
    console.log('📝 尝试点击写回答...');
    await page.evaluate(() => {
      const btns = document.querySelectorAll('button');
      for (const btn of btns) {
        if (btn.textContent.includes('写回答')) {
          btn.click();
          return true;
        }
      }
      return false;
    });
    
    await page.waitForTimeout(3000);
    
    // 8. 截图
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/zhihu_answer_form.png', fullPage: true });
    console.log('📸 已保存回答表单');
    
    console.log('✅ 知乎流程完成！');
    
    // 保持打开
    await new Promise(() => {});
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    await page.screenshot({ path: '/home/uosun-shan/.openclaw/workspace/inputs/zhihu_error.png' });
  }
}

postZhihu();
