// 改进的剪贴板粘贴图片功能
// 这个文件包含修复后的粘贴事件处理代码

// 将此代码放在 app.js 的 DOMContentLoaded 事件监听器内

composer.addEventListener('paste', (e) => {
  console.log('[Paste] Event triggered'); // 调试日志
  
  const items = e.clipboardData?.items;
  if (!items) {
    console.log('[Paste] No clipboard items');
    return;
  }
  
  console.log('[Paste] Items count:', items.length);
  
  for (const item of items) {
    console.log('[Paste] Item type:', item.type);
    
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      console.log('[Paste] Image detected, preventing default');
      
      const file = item.getAsFile();
      if (!file) {
        console.log('[Paste] Failed to get file');
        continue;
      }
      
      console.log('[Paste] File size:', file.size, 'bytes');
      
      // 验证文件大小（最大 5MB）
      if (file.size > 5 * 1024 * 1024) {
        alert('图片大小不能超过 5MB');
        return;
      }
      
      // 读取图片为 base64
      const reader = new FileReader();
      reader.onload = (event) => {
        console.log('[Paste] Image loaded successfully');
        selectedImage = event.target.result;
        previewImg.src = selectedImage;
        imagePreview.style.display = 'flex';
        
        // 添加视觉反馈
        attachBtn.style.color = 'var(--cyan)';
        setTimeout(() => {
          attachBtn.style.color = '';
        }, 1000);
      };
      reader.onerror = (err) => {
        console.error('[Paste] FileReader error:', err);
        alert('图片读取失败，请重试');
      };
      reader.readAsDataURL(file);
      break;  // 只处理第一个图片
    }
  }
});

// 同时支持在整个输入区域粘贴
document.addEventListener('paste', (e) => {
  // 如果焦点不在 composer 上，但粘贴的是图片，也处理
  if (document.activeElement !== composer) {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        // 聚焦到 composer 并处理
        composer.focus();
        break;
      }
    }
  }
});
