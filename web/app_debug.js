// 调试补丁：在 app.js 开头添加这些日志
// 在浏览器控制台执行，或者直接粘贴到 app.js

console.log('[Chat History Debug] 页面加载');
console.log('[Chat History Debug] localStorage key:', CHAT_KEY);
console.log('[Chat History Debug] localStorage 内容:', localStorage.getItem(CHAT_KEY));

// 检查 chatHistory 数组
setTimeout(() => {
  console.log('[Chat History Debug] chatHistory 数组长度:', chatHistory.length);
  console.log('[Chat History Debug] chatHistory 内容:', chatHistory.slice(0, 3));
}, 1000);

// 监听 saveChatHistory 调用
const originalSave = saveChatHistory;
saveChatHistory = function() {
  console.log('[Chat History Debug] saveChatHistory 被调用');
  console.log('[Chat History Debug] 保存的 chatHistory 长度:', chatHistory.length);
  originalSave();
  console.log('[Chat History Debug] localStorage 已更新');
};
