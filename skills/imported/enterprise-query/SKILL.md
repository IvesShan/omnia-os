# Enterprise Query Skill

查询中国企业工商信息、股东结构、变更记录等。

## 功能

- 搜索企业基本信息
- 查询企业详细信息（法人、注册资本、地址、经营范围等）
- 查询股东及高管信息

## 使用方式

### 命令行

```bash
# 搜索企业
node skills/enterprise-query/index.js search 南京物熵科技有限公司

# 获取企业详情
node skills/enterprise-query/index.js detail 南京物熵科技有限公司

# 查询股东信息
node skills/enterprise-query/index.js shareholders 南京物熵科技有限公司
```

### 作为模块调用

```javascript
const { enterpriseSearch, enterpriseDetail, enterpriseShareholders } = require('./skills/enterprise-query');

// 查询企业详情
const result = await enterpriseDetail('南京物熵科技有限公司');
console.log(result);
```

## 配置

需要设置极速数据 API Key：

```bash
export JISU_API_KEY=your_api_key_here
```

或在 OpenClaw 配置中添加：

```yaml
skills:
  enterprise-query:
    apiKey: your_api_key_here
```

## API Key 申请

访问 [极速数据](https://www.jisuapi.com) 注册并申请企业工商信息查询 API。

## 数据来源

- 极速数据 (jisuapi.com)
- 数据来源于国家企业信用信息公示系统

## 注意事项

1. 需要有效的 API Key 才能查询
2. 免费额度有限，大量查询需要购买套餐
3. 数据可能有延迟，以工商登记为准