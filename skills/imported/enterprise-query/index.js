#!/usr/bin/env node
/**
 * 企业工商信息查询技能
 * 使用极速数据 API 查询企业信息
 */

const https = require('https');
const querystring = require('querystring');

// 极速数据 API 配置
const API_BASE = 'https://api.jisuapi.com';
// 注意：实际使用时需要在 OpenClaw 配置中设置 JISU_API_KEY
const API_KEY = process.env.JISU_API_KEY || '';

/**
 * 发送 HTTP 请求
 */
function httpRequest(url, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'OpenClaw-Enterprise-Query/1.0'
      }
    };

    const req = https.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          resolve(data);
        }
      });
    });

    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

/**
 * 搜索企业
 */
async function enterpriseSearch(companyName) {
  if (!API_KEY) {
    return {
      error: '未配置 API Key',
      message: '请在 OpenClaw 配置中设置 JISU_API_KEY，或访问 https://www.jisuapi.com 申请'
    };
  }

  try {
    const params = querystring.stringify({
      keyword: companyName,
      appkey: API_KEY
    });
    const url = `${API_BASE}/enterprise/search?${params}`;
    const result = await httpRequest(url);
    return result;
  } catch (error) {
    return { error: error.message };
  }
}

/**
 * 获取企业详细信息
 */
async function enterpriseDetail(companyName) {
  if (!API_KEY) {
    return {
      error: '未配置 API Key',
      message: '请在 OpenClaw 配置中设置 JISU_API_KEY，或访问 https://www.jisuapi.com 申请'
    };
  }

  try {
    const params = querystring.stringify({
      keyword: companyName,
      appkey: API_KEY
    });
    const url = `${API_BASE}/enterprise/detail?${params}`;
    const result = await httpRequest(url);
    return result;
  } catch (error) {
    return { error: error.message };
  }
}

/**
 * 获取股东高管信息
 */
async function enterpriseShareholders(companyName) {
  const detail = await enterpriseDetail(companyName);
  if (detail.error) return detail;
  
  // 从详情中提取股东信息
  if (detail.result && detail.result.partners) {
    return {
      status: 0,
      msg: 'ok',
      result: {
        company: detail.result.company,
        shareholders: detail.result.partners,
        executives: detail.result.employees || []
      }
    };
  }
  
  return detail;
}

/**
 * 格式化输出企业信息
 */
function formatEnterpriseInfo(data) {
  if (data.error) {
    return `❌ 查询失败: ${data.error}\n${data.message || ''}`;
  }

  if (!data.result) {
    return '❌ 未找到企业信息';
  }

  const r = data.result;
  let output = `\n📋 **${r.company || r.name || '企业信息'}**\n\n`;
  
  output += `| 项目 | 内容 |\n`;
  output += `|------|------|\n`;
  output += `| 统一社会信用代码 | ${r.creditno || r.regno || '-'} |\n`;
  output += `| 法定代表人 | ${r.legal || '-'} |\n`;
  output += `| 注册资本 | ${r.capital || '-'} |\n`;
  output += `| 成立日期 | ${r.establish || r.startdate || '-'} |\n`;
  output += `| 企业状态 | ${r.status || '-'} |\n`;
  output += `| 注册地址 | ${r.address || '-'} |\n`;
  output += `| 经营范围 | ${r.scope ? r.scope.substring(0, 100) + '...' : '-'} |\n`;
  
  // 股东信息
  if (r.partners && r.partners.length > 0) {
    output += `\n👥 **股东信息**\n\n`;
    output += `| 股东名称 | 出资比例 | 出资额 |\n`;
    output += `|----------|----------|--------|\n`;
    r.partners.forEach(p => {
      output += `| ${p.name || '-'} | ${p.percent || '-'} | ${p.capital || '-'} |\n`;
    });
  }
  
  return output;
}

// 主入口
async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  const companyName = args[1];

  if (!command || !companyName) {
    console.log(`
Usage: enterprise-query <command> <company-name>

Commands:
  search <name>      搜索企业
  detail <name>      获取企业详情
  shareholders <name> 获取股东信息

Examples:
  enterprise-query search 南京物熵科技有限公司
  enterprise-query shareholders 南京物熵科技有限公司
`);
    process.exit(0);
  }

  let result;
  switch (command) {
    case 'search':
      result = await enterpriseSearch(companyName);
      break;
    case 'detail':
      result = await enterpriseDetail(companyName);
      break;
    case 'shareholders':
      result = await enterpriseShareholders(companyName);
      break;
    default:
      console.log('Unknown command:', command);
      process.exit(1);
  }

  console.log(formatEnterpriseInfo(result));
}

// 导出供其他模块使用
module.exports = {
  enterpriseSearch,
  enterpriseDetail,
  enterpriseShareholders,
  formatEnterpriseInfo
};

// 直接运行
if (require.main === module) {
  main().catch(console.error);
}