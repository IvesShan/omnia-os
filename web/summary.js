// =========================================
// 对话摘要压缩模块
// =========================================

// 摘要压缩配置
const SUMMARY_CONFIG = {
  // 触发压缩的消息数量阈值
  COMPRESS_THRESHOLD: 50,
  // 保留最近的消息数量
  KEEP_RECENT: 20,
  // 摘要 API 端点
  API_ENDPOINT: '/api/chat/summarize/auto',
  // 是否启用自动压缩
  ENABLED: true,
};

// 估算 Token 数量（粗略估算）
function estimateTokenCount(text) {
  if (!text) return 0;
  // 中文大约 2 字符 = 1 token，英文大约 4 字符 = 1 token
  // 这里使用简化算法
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  const otherChars = text.length - chineseChars;
  return Math.ceil(chineseChars * 0.5 + otherChars * 0.25);
}

// 构建带压缩的历史消息
async function buildCompressedHistory(messages) {
  if (!SUMMARY_CONFIG.ENABLED || messages.length <= SUMMARY_CONFIG.COMPRESS_THRESHOLD) {
    return messages;
  }

  try {
    console.log(`[Summary] 触发自动压缩，当前 ${messages.length} 条消息`);
    
    // 显示压缩状态
    showTyping('正在压缩对话历史...');
    
    const response = await fetch(`${API_BASE}${SUMMARY_CONFIG.API_ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages })
    });

    if (!response.ok) {
      console.error('[Summary] 压缩请求失败:', response.status);
      removeTyping();
      return messages;
    }

    const result = await response.json();
    removeTyping();

    if (result.ok && result.messages) {
      console.log(`[Summary] 压缩完成，节省约 ${result.token_saved} tokens`);
      
      // 显示压缩提示
      if (result.token_saved > 0) {
        appendOmnia(`✅ 对话历史已自动压缩，节省约 ${result.token_saved} tokens`);
      }
      
      return result.messages;
    }
    
    return messages;
  } catch (err) {
    console.error('[Summary] 压缩失败:', err);
    removeTyping();
    return messages;
  }
}

// 手动触发摘要压缩
async function manualSummarize() {
  if (chatHistory.length <= 10) {
    appendOmnia('对话历史太短，无需压缩');
    return;
  }

  try {
    showTyping('正在生成对话摘要...');
    
    const messages = chatHistory.map(m => ({
      role: m.role,
      content: m.content
    }));

    const response = await fetch(`${API_BASE}/api/chat/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: messages })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();
    removeTyping();

    if (result.ok && result.summary) {
      appendOmnia(`📝 **对话摘要**\n\n${result.summary}\n\n---\n*节省约 ${result.token_saved} tokens*`);
    } else {
      appendOmnia(`[错误] 摘要生成失败: ${result.error || '未知错误'}`);
    }
  } catch (err) {
    removeTyping();
    appendOmnia(`[错误] 摘要生成失败: ${err.message}`);
  }
}
