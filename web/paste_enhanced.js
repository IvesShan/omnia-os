// =========================================
// 增强版图片粘贴功能
// 支持多种来源：截图工具、右键复制、拖拽等
// =========================================

console.log('[Paste Enhanced] 初始化增强粘贴功能...');

// 检测是否支持 Clipboard API
const hasClipboardAPI = 'ClipboardItem' in window;
const hasClipboardData = 'clipboardData' in window || 'clipboardData' in document;

console.log('[Paste Enhanced] Clipboard API 支持:', hasClipboardAPI);
console.log('[Paste Enhanced] ClipboardData 支持:', hasClipboardData);

// 处理粘贴的图片文件
async function handleImagePaste(file) {
  if (!file) {
    console.log('[Paste Enhanced] 无文件');
    return false;
  }
  
  console.log('[Paste Enhanced] 文件信息:', file.name || 'unnamed', file.type, file.size, 'bytes');
  
  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    console.log('[Paste Enhanced] 不是图片类型:', file.type);
    return false;
  }
  
  // 验证文件大小（最大 5MB）
  if (file.size > 5 * 1024 * 1024) {
    alert('图片大小不能超过 5MB');
    return false;
  }
  
  // 读取图片为 base64
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      console.log('[Paste Enhanced] 图片读取成功');
      selectedImage = event.target.result;
      previewImg.src = selectedImage;
      imagePreview.style.display = 'flex';
      
      // 视觉反馈
      attachBtn.style.color = 'var(--cyan)';
      attachBtn.style.transform = 'scale(1.2)';
      setTimeout(() => {
        attachBtn.style.color = '';
        attachBtn.style.transform = '';
      }, 800);
      
      // 聚焦到输入框
      composer.focus();
      
      resolve(true);
    };
    reader.onerror = (err) => {
      console.error('[Paste Enhanced] FileReader 错误:', err);
      alert('图片读取失败，请重试');
      resolve(false);
    };
    reader.readAsDataURL(file);
  });
}

// 方法 1: 传统 paste 事件（兼容性最好）
composer.addEventListener('paste', async (e) => {
  console.log('[Paste Enhanced] composer paste 事件触发');
  
  const items = e.clipboardData?.items;
  if (!items) {
    console.log('[Paste Enhanced] 没有 clipboardData.items');
    return;
  }
  
  console.log('[Paste Enhanced] items 数量:', items.length);
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    console.log(`[Paste Enhanced] Item ${i}: type=${item.type}, kind=${item.kind}`);
    
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      console.log('[Paste Enhanced] 检测到图片，阻止默认行为');
      
      const file = item.getAsFile();
      await handleImagePaste(file);
      break;
    }
  }
});

// 方法 2: 全局粘贴监听（当焦点不在输入框时）
document.addEventListener('paste', async (e) => {
  // 如果焦点在 composer 上，让方法 1 处理
  if (document.activeElement === composer) {
    return;
  }
  
  console.log('[Paste Enhanced] 全局 paste 事件触发，焦点:', document.activeElement?.tagName);
  
  const items = e.clipboardData?.items;
  if (!items) return;
  
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      console.log('[Paste Enhanced] 全局监听检测到图片');
      
      const file = item.getAsFile();
      await handleImagePaste(file);
      break;
    }
  }
});

// 方法 3: 现代 Clipboard API（异步读取）
// 某些浏览器在 paste 事件中不提供 clipboardData.items
// 但支持 navigator.clipboard.read()
if (hasClipboardAPI && navigator.clipboard?.read) {
  document.addEventListener('paste', async (e) => {
    // 如果已经处理过，跳过
    if (e.defaultPrevented) return;
    
    // 如果焦点在 composer 上，让方法 1 处理
    if (document.activeElement === composer) return;
    
    console.log('[Paste Enhanced] 尝试使用 Clipboard API');
    
    try {
      const clipboardItems = await navigator.clipboard.read();
      
      for (const clipboardItem of clipboardItems) {
        const types = clipboardItem.types;
        console.log('[Paste Enhanced] Clipboard API types:', types);
        
        for (const type of types) {
          if (type.startsWith('image/')) {
            e.preventDefault();
            const blob = await clipboardItem.getType(type);
            const file = new File([blob], 'pasted-image.png', { type });
            await handleImagePaste(file);
            return;
          }
        }
      }
    } catch (err) {
      console.log('[Paste Enhanced] Clipboard API 失败:', err.message);
      // 可能是权限问题，静默失败
    }
  });
}

// 方法 4: 拖拽上传支持
const dropZone = document.querySelector('.input-area') || composer.parentElement;

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
  dropZone.style.borderColor = 'var(--cyan)';
  dropZone.style.boxShadow = '0 0 12px rgba(34, 211, 238, 0.3)';
});

dropZone.addEventListener('dragleave', (e) => {
  e.preventDefault();
  e.stopPropagation();
  dropZone.style.borderColor = '';
  dropZone.style.boxShadow = '';
});

dropZone.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  dropZone.style.borderColor = '';
  dropZone.style.boxShadow = '';
  
  console.log('[Paste Enhanced] drop 事件触发');
  
  const files = e.dataTransfer?.files;
  if (!files || files.length === 0) return;
  
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      await handleImagePaste(file);
      break;
    }
  }
});

// 方法 5: 右键粘贴按钮（备选方案）
// 在输入区域添加提示
const hint = document.querySelector('.composer-hint');
if (hint) {
  hint.innerHTML = `
    <kbd>Enter</kbd> 发送 · <kbd>Shift + Enter</kbd> 换行 · 
    <kbd>Ctrl+V</kbd> 粘贴图片 · 拖拽图片到此处
  `;
}

console.log('[Paste Enhanced] 增强粘贴功能初始化完成');

// 导出函数供调试使用
window.debugPasteImage = handleImagePaste;
