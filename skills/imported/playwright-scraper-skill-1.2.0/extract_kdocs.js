const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    viewport: { width: 1600, height: 900 }
  });

  // Inject user's cookies
  const cookies = [
    {name:'swi_acc_redirect_limit',value:'0',domain:'.kdocs.cn',path:'/'},
    {name:'weboffice_device_id',value:'1a059626cd8c4db868ab91b935accdb3',domain:'.kdocs.cn',path:'/'},
    {name:'visitorid',value:'1401612644',domain:'.kdocs.cn',path:'/'},
    {name:'weboffice_cdn',value:'20',domain:'.kdocs.cn',path:'/'},
    {name:'region',value:'yxy',domain:'.kdocs.cn',path:'/'},
    {name:'csrf',value:'nQy6b7jzZbiW5eK5wdGFnkHGnykaxE75',domain:'.kdocs.cn',path:'/'},
    {name:'wps_endcloud',value:'1',domain:'.kdocs.cn',path:'/'},
    {name:'_ku',value:'1',domain:'.kdocs.cn',path:'/'},
    {name:'cid',value:'0',domain:'.kdocs.cn',path:'/'},
    {name:'coa_id',value:'0',domain:'.kdocs.cn',path:'/'},
    {name:'cv',value:'fGKGSCsJi3jGkeWiM7d1Nv_5jGbg3G1BjZEI4yDZ4L_jZB8qwWXc3snxNYOrCo2RYRTut7gm.5skOa2fagmS',domain:'.kdocs.cn',path:'/'},
    {name:'exp',value:'259200',domain:'.kdocs.cn',path:'/'},
    {name:'kso_sid',value:'TKS-f0fpeN_8Kx7wFteO0poTTKS7fKoAKQKSZ7Fq9wTqIyodTN9PzjR8IpNw_8jlsajzdXRFAzrCA7oqR9rwR7NFIQoU2izs92owp3F7PySTrQvwiLcXXLD-T2KwY2IxRfIDRUf9v4FHTSrfWrIIKQ.JKusEFPjO8Ao7pw3FwzL8yBFHCuYfr9CpAxZIB_JcnN9xJWDtSefPk1dH45fvpTHJGBBIi44zc0WVo2W753gwr',domain:'.kdocs.cn',path:'/'},
    {name:'nexp',value:'129600',domain:'.kdocs.cn',path:'/'},
    {name:'uid',value:'1785980888',domain:'.kdocs.cn',path:'/'},
    {name:'wps_sid',value:'V02ST7zZjTowhe6iPyECgQvw7L1XXL400a210281006a73e7d8',domain:'.kdocs.cn',path:'/'}
  ];
  await context.addCookies(cookies);

  const page = await context.newPage();
  await page.goto('https://www.kdocs.cn/l/cn6S4ZvbWTf7', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(8000);

  // Try to dismiss login dialog if present by pressing Escape
  await page.keyboard.press('Escape');
  await page.waitForTimeout(2000);

  // Extract all text content from the page
  const bodyText = await page.evaluate(() => document.body.innerText);

  // Try to find visible table/cell data
  const cellTexts = await page.evaluate(() => {
    const cells = Array.from(document.querySelectorAll('div[role="cell"], div[role="gridcell"], td, .cell, .table-cell'));
    return cells.map(c => c.innerText).filter(t => t.trim().length > 0);
  });

  await page.screenshot({ path: '/home/shan/.openclaw/workspace/miaoxiujiang/repair_cases/kdocs_screenshot2.png', fullPage: true });

  const result = {
    bodyTextLength: bodyText.length,
    cellCount: cellTexts.length,
    cellsPreview: cellTexts.slice(0, 200),
    url: page.url()
  };

  require('fs').writeFileSync('/tmp/kdocs_extract.json', JSON.stringify(result, null, 2), 'utf-8');
  console.log(JSON.stringify({status:'ok', bodyTextLength: bodyText.length, cellCount: cellTexts.length}));
  await browser.close();
})();
