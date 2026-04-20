---
name: miaoxiujiang-merchant
description: 喵修匠商家后台开发专用Skill。包含问题诊断、修复方案、代码模板和优化建议，避免重复加载大文件到上下文。
---

# 喵修匠商家后台开发指南

## 当前状态（2026-04-08）

### 已知问题清单
- [ ] 订单列表不显示（API正常返回9条，前端显示"暂无订单"）
- [ ] 可能原因：CORS跨域、字段映射、渲染逻辑

### 修复记录
1. ✅ 数据库迁移 - 添加repair_mode等字段
2. ✅ API路径修复 - /api/merchant/orders
3. ✅ 前端字段兼容 - repair_type vs repair_mode
4. ✅ 页面重写 - merchant.html v2带调试日志

## 快速诊断

### 检查API是否正常
```bash
curl http://192.168.31.62:5000/api/merchant/orders | python3 -c "import sys,json; d=json.load(sys.stdin); print('订单数:', len(d.get('orders',[])))"
```

### 检查前端控制台
让用户按F12查看Console标签页的日志输出

## 代码模板

### 订单列表渲染（简化版）
```javascript
async function loadOrders() {
    try {
        console.log('Loading orders...');
        const res = await fetch(`${API_BASE}/merchant/orders`);
        const data = await res.json();
        console.log('Response:', data);
        
        if (data.success && data.orders) {
            renderOrders(data.orders);
        }
    } catch (e) {
        console.error('Error:', e);
    }
}
```

### 状态映射
```javascript
const STATUS_MAP = {
    'pending': { text: '待接单', class: 'status-pending' },
    'accepted': { text: '已接单', class: 'status-accepted' },
    'repairing': { text: '维修中', class: 'status-repairing' },
    'completed': { text: '已完成', class: 'status-completed' }
};
```

## 优化建议

### 减少API调用
- 合并多个小修改为一次大修改
- 使用本地缓存避免重复请求

### 减少文件操作
- 先用技能文件分析问题
- 确认方案后再执行修改

## 下一步行动

1. 让用户检查浏览器控制台日志
2. 根据日志确定具体问题
3. 一次性修复所有问题
4. 测试验证
