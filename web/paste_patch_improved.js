// 改进的剪贴板粘贴图片功能 - 带调试日志和视觉反馈
// 将此代码替换 app.js 中的粘贴事件处理部分

console.log('[Paste] 初始化粘贴图片功能...');

// --- 剪贴板粘贴图片（改进版）---
composer.addEventListener('paste', (e) => {
  console.log('[Paste] 粘贴事件触发');
  console.log('[Paste] clipboardData:', e.clipboardData);
  
  const items = e.clipboardData?.items;
  if (!items) {
    console.log('[Paste] 没有 clipboardData.items');
    return;
  }
  
  console.log('[Paste] items 数量:', items.length);
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    console.log(`[Paste] Item ${i}:`, item.type, item.kind);
    
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      console.log('[Paste] 检测到图片，阻止默认行为');
      
      const file = item.getAsFile();
      if (!file) {
        console.log('[Paste] 无法获取文件');
        continue;
      }
      
      console.log('[Paste] 文件信息:', file.name, file.type, file.size, 'bytes');
      
      // 验证文件大小（最大 5MB）
      if (file.size > 5 * 1024 * 1024) {
        alert('图片大小不能超过 5MB');
        return;
      }
      
      // 读取图片为 base64
      const reader = new FileReader();
      reader.onload = (event) => {
        console.log('[Paste] 图片读取成功');
        selectedImage = event.target.result;
        previewImg.src = selectedImage;
        imagePreview.style.display = 'flex';
        
        // 添加视觉反馈 - 按钮闪烁
        attachBtn.style.color = 'var(--cyan)';
        attachBtn.style.transform = 'scale(1.2)';
        setTimeout(() => {
          attachBtn.style.color = '';
          attachBtn.style.transform = '';
        }, 800);
        
        console.log('[Paste] 图片预览已显示');
      };
      reader.onerror = (err) => {
        console.error('[Paste] FileReader 错误:', err);
        alert('图片读取失败，请重试');
      };
      reader.readAsDataURL(file);
      break;  // 只处理第一个图片
    }
  }
});

// --- 全局粘贴监听（当焦点不在 composer 时）---
document.addEventListener('paste', (e) => {
  // 如果焦点不在 composer 上，但粘贴的是图片，聚焦到 composer
  if (document.activeElement !== composer) {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        console.log('[Paste] 全局监听检测到图片粘贴，聚焦到 composer');
        composer.focus();
        break;
      }
    }
  }
});

console.log('[Paste] 粘贴图片功能初始化完成');
