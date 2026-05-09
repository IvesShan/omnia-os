// 喵修匠商户工作台 v1.0 (固化版本)
// 最后更新: 2026-04-18
// 商户配置 - 固化版本
const MERCHANTS_V1 = {
  'merch_001': {
    id: 'merch_001',
    name: '物熵科技',
    access_code: '3613',
    contact_name: '吴主任',
    phone: '15796313613',
    address: '江苏省苏州市虎丘区滨河路588号赛格三期',
    business_hours: '周一至周五 09:00-18:00'
  },
  'merch_002': {
    id: 'merch_002',
    name: '南京物熵',
    access_code: '8280',
    contact_name: '张经理',
    phone: '18912958280',
    address: '江苏省南京市鼓楼区',
    business_hours: '周一至周六 09:00-18:00'
  }
};

console.log('[喵修匠 v1.0] 商户配置已加载:', Object.keys(MERCHANTS_V1).length, '个商户');
