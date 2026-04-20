# 喵修匠维修平台 - 项目需求文档

**创建时间**: 2026-04-08  
**版本**: v1.0  
**状态**: 已确认

---

## 一、项目概述

### 1.1 项目定位
无人机维修服务平台，连接客户与维修商，提供从下单到完成的完整维修流程管理。

### 1.2 核心目标
- 客户：便捷下单、实时跟踪、在线支付
- 商家：AI驱动的高效维修工作台
- 平台：可扩展的多商户架构（预留）

---

## 二、系统架构

### 2.1 整体架构
```
┌──────────────────────────────────────────────────────────────┐
│                      喵修匠平台                               │
├──────────────────────────────────────────────────────────────┤
│  客户小程序          │  商家后台            │  平台管理后台    │
│  (微信生态)          │  (AI工作台)          │  (多商户配置)   │
├──────────────────────┼──────────────────────┼────────────────┤
│  • 下单              │  • AI助手            │  • 商户管理     │
│  • 微信支付          │  • 工单处理          │  • 派单配置     │
│  • 查看进度          │  • 库存管理          │  • 权重调整     │
│  • 订阅通知          │  • 财务统计          │  • 数据统计     │
└──────────────────────┴──────────────────────┴────────────────┘
```

### 2.2 技术栈
- **后端**: Python + FastAPI + SQLite
- **客户小程序**: 微信小程序原生
- **商家后台**: HTML5 + Vanilla JS + Web Speech API
- **AI解析**: 本地规则引擎
- **支付**: 微信支付（预留支付宝接口）
- **通知**: 微信订阅消息 + WebSocket

---

## 三、实施策略

### 3.1 分阶段开发

#### Phase 1: MVP核心（1-2周）
- [ ] 客户小程序：下单、支付、查看进度
- [ ] 商家后台workbench.html：AI工作台、工单处理
- [ ] 微信支付集成
- [ ] 微信通知集成
- [ ] 单商户模式（南京物熵）

#### Phase 2: 平台化准备（1周）
- [ ] 多商户数据结构
- [ ] 简单派单（手动分配）
- [ ] 基础权限系统

#### Phase 3: 平台化完善（1-2周）
- [ ] 自动派单算法
- [ ] 权重配置界面
- [ ] 平台管理后台
- [ ] 硬件对接（打印机等）

### 3.2 渐进式重构策略
- ✅ **保留**: 后端API (server_v2.py)、数据库 (repair.db)、客户前端 (chat.html)
- ⚠️ **重构**: 商家后台 → 新建 workbench.html（AI驱动工作台）
- 🆕 **新增**: AI解析接口、支付接口、通知接口

---

## 四、UI/UX设计规范

### 4.1 设计语言
- **风格**: Apple-like 深色主题
- **背景**: #000000 (纯黑)
- **主强调色**: #FF9500 (iOS橙)
- **次强调色**: #0A84FF (iOS蓝)
- **字体**: -apple-system, SF Pro, Inter
- **圆角**: 12-16px
- **间距**: 4px基准 (4/8/12/16/24/32/48)

### 4.2 交互原则
- 减少点击步骤，AI语音优先
- 手势操作：左滑删除、下拉刷新
- 即时反馈：Toast提示、骨架屏
- 无障碍：大触摸区域（最小44px）

### 4.3 组件规范
- 按钮：圆角12px，主按钮橙色，次按钮灰色
- 卡片：圆角16px，背景#1C1C1E
- 输入框：圆角10px，聚焦时蓝色边框
- 标签：圆角6px，小号字体

---

## 五、功能模块详情

### 5.1 客户小程序

#### 首页
- 机型选择（图标网格）
- 故障描述（AI引导）
- 快速下单按钮

#### 订单页
- 订单列表（卡片式）
- 订单详情（时间轴）
- 支付按钮

#### 我的
- 个人信息
- 地址管理
- 历史订单

### 5.2 商家后台 (AI工作台)

#### 仪表盘
- 今日统计（待接单、待检测、维修中）
- 收入统计（今日、本周、本月）
- 待办事项列表
- 快捷入口

#### AI工作台（核心）
- 悬浮AI助手球
- 语音/文字输入
- 快捷指令按钮
- 对话历史

#### 工单管理
- 工单列表（状态筛选）
- 工单详情（完整信息）
- 状态流转操作
- 搜索功能

#### 库存管理
- 配件列表（AI编码显示）
- 库存预警
- 出入库记录
- 扫码功能（预留）

#### 财务统计
- 收入分析
- 成本核算
- 利润报表
- 结算状态

### 5.3 AI能力矩阵

| 场景 | 输入示例 | AI输出 |
|------|----------|--------|
| 新建工单 | "闲鱼客户李先生，Mini3云台故障" | 自动提取客户、来源、机型、问题 |
| 配件查询 | "查Mini3云台电机库存" | 显示库存、编码、建议 |
| 智能报价 | "Mini3换云台电机和信号线" | 成本计算、建议售价、利润率 |
| 快速入库 | "入库10个Air3电机" | 确认入库、更新库存 |
| 快速出库 | "工单718943用了1个电机" | 确认出库、扣减库存 |
| 生成报告 | "检测发现云台损坏、信号线断裂" | 分类整理、生成PDF |

---

## 六、数据模型

### 6.1 核心表结构

```sql
-- 商户表
merchants (
    id TEXT PRIMARY KEY,
    name TEXT,
    phone TEXT,
    address TEXT,
    status TEXT,           -- active/pending/blocked
    rating REAL,
    weight INTEGER,        -- 派单权重
    max_orders INTEGER,
    created_at TIMESTAMP
);

-- 订单表
orders (
    id TEXT PRIMARY KEY,
    case_no TEXT UNIQUE,
    merchant_id TEXT,
    customer_name TEXT,
    customer_phone TEXT,
    customer_openid TEXT,  -- 微信openid
    source_channel TEXT,   -- 来源：闲鱼/抖音/微信/上门
    drone_model TEXT,
    drone_sn TEXT,
    problem_desc TEXT,
    status TEXT,           -- 11个状态
    items JSON,            -- 配件清单
    inspect_result TEXT,
    inspect_photos JSON,
    quote_items JSON,
    quote_total REAL,
    cost REAL,
    profit REAL,
    tracking_in TEXT,
    tracking_out TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 配件表
parts (
    code TEXT PRIMARY KEY, -- P-M3P-YT-DJZ-001
    merchant_id TEXT,
    drone_model TEXT,
    category TEXT,
    name TEXT,
    cost_price REAL,
    sale_price REAL,
    stock INTEGER,
    min_stock INTEGER,
    created_at TIMESTAMP
);

-- 支付表
payments (
    id TEXT PRIMARY KEY,
    order_id TEXT,
    channel TEXT,          -- wechat/alipay
    amount REAL,
    status TEXT,           -- pending/paid/failed
    transaction_id TEXT,
    paid_at TIMESTAMP
);

-- AI指令日志
ai_commands (
    id INTEGER PRIMARY KEY,
    merchant_id TEXT,
    raw_input TEXT,
    parsed_intent TEXT,
    parsed_params JSON,
    success BOOLEAN,
    created_at TIMESTAMP
);
```

---

## 七、API设计

### 7.1 现有接口（保留）
- `GET /api/merchant/orders` - 获取订单列表
- `POST /api/order/accept` - 接单
- `POST /api/order/detect` - 检测
- `POST /api/order/quote` - 报价
- `POST /api/order/repair` - 维修状态
- `POST /api/order/ship` - 发货

### 7.2 新增接口
- `POST /api/ai/parse` - AI解析自然语言
- `POST /api/payment/create` - 创建支付订单
- `POST /api/payment/notify` - 支付回调
- `POST /api/notify/send` - 发送微信通知
- `GET /api/parts/search` - 搜索配件
- `POST /api/parts/stock` - 出入库操作
- `WS /ws/orders` - WebSocket实时推送

---

## 八、业务流程

### 8.1 标准维修流程
```
客户下单 → 商家接单 → 客户寄件 → 商家收件 → 
外观检测 → 生成报价 → 客户付款 → 开始维修 → 
维修完成 → 质检发货 → 客户收货 → 财务结算
```

### 8.2 状态流转
```
pending → accepted → received → inspected → quoted → 
confirmed → repairing → repaired → shipped → delivered → completed
```

### 8.3 AI交互流程
```
用户语音输入 → AI解析意图 → 提取实体 → 
执行操作 → 返回结果 → 确认/修改
```

---

## 九、关键业务规则

1. **配件编码**: P-{机型代码}-{类别代码}-{序号}
2. **案例号**: CAS-{日期}-{随机4位}
3. **订单号**: WR{年月日时分秒}
4. **报价计算**: 毛利率 = (售价 - 成本) / 售价，目标12-15%
5. **库存预警**: 库存 < min_stock 时提醒
6. **派单权重**: 手动配置40% + 评分30% + 空闲度20% + 随机10%

---

## 十、验收标准

### 10.1 功能验收
- [ ] 客户可完成完整下单流程
- [ ] 商家可通过AI助手处理工单
- [ ] 微信支付正常
- [ ] 微信通知正常送达
- [ ] 库存自动更新
- [ ] 财务报表准确

### 10.2 性能验收
- [ ] 页面加载 < 3秒
- [ ] AI响应 < 1秒
- [ ] 支付流程 < 5秒
- [ ] 支持并发10单

### 10.3 设计验收
- [ ] 符合iOS设计风格
- [ ] 深色主题统一
- [ ] 交互流畅自然
- [ ] 移动端适配良好

---

## 十一、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| API限流 | 开发受阻 | 使用Skill文件缓存，减少重复调用 |
| 微信支付审核 | 上线延迟 | 先用测试模式，同步申请正式号 |
| 语音识别不准 | 体验差 | 提供文字输入备选，持续优化 |
| 多商户复杂度 | 开发延期 | Phase 1只做单商户，后续迭代 |

---

## 十二、相关文件

- 业务分析: `business-analysis.md`
- UI设计规范: `design-system.css` (待创建)
- 后端API: `../miaoxiujiang-api/server_v2.py`
- 客户前端: `../miaoxiujiang/chat.html`
- 商家后台: `../miaoxiujiang/workbench.html` (待创建)

---

**确认人**: 用户 + AI助手无限  
**确认时间**: 2026-04-08
