/**
 * Omnia Frontend Health Check
 * 
 * 功能：
 * 1. 定期检查后端健康状态
 * 2. 显示连接状态
 * 3. 自动重连
 */

class HealthChecker {
    constructor() {
        this.checkInterval = 30000; // 30秒检查一次
        this.timeout = 5000; // 5秒超时
        this.failures = 0;
        this.maxFailures = 3;
        this.isHealthy = true;
        this.timer = null;
    }
    
    start() {
        console.log('[HealthCheck] 启动健康检查');
        // 不立即检查，等待定时器触发
        this.timer = setInterval(() => this.check(), this.checkInterval);
        
        // 页面可见性变化时立即检查
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                console.log('[HealthCheck] 页面恢复可见，立即检查');
                this.check();
            }
        });
    }
    
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    async check() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            const response = await fetch(`${API_BASE}/api/status`, {
                signal: controller.signal,
                cache: 'no-store',
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                this.onSuccess();
            } else {
                this.onFailure(`HTTP ${response.status}`);
            }
        } catch (error) {
            // 忽略 abort 错误
            if (error.name === 'AbortError') {
                this.onFailure('请求超时');
            } else {
                this.onFailure(error.message);
            }
        }
    }
    
    onSuccess() {
        if (!this.isHealthy) {
            console.log('[HealthCheck] ✅ 连接恢复');
            this.showStatus('已连接', 'success');
        }
        
        this.failures = 0;
        this.isHealthy = true;
        this.updateUI(true);
    }
    
    onFailure(reason) {
        this.failures++;
        console.warn(`[HealthCheck] ⚠️ 检查失败 (${this.failures}/${this.maxFailures}): ${reason}`);
        
        if (this.failures >= this.maxFailures) {
            this.isHealthy = false;
            this.updateUI(false);
            this.showStatus('连接中断', 'error');
            
            // 尝试重新加载状态
            if (this.failures === this.maxFailures) {
                console.log('[HealthCheck] 尝试重新连接...');
            }
        }
    }
    
    updateUI(healthy) {
        // 更新连接状态指示器
        const daemonEl = document.querySelector('#link-daemon .link-value');
        const apiEl = document.querySelector('#link-api .link-value');
        const daemonDot = document.querySelector('#link-daemon .link-dot');
        const apiDot = document.querySelector('#link-api .link-dot');
        
        if (daemonEl) {
            daemonEl.textContent = healthy ? '运行中' : '已断开';
        }
        if (apiEl) {
            apiEl.textContent = healthy ? '正常' : '无响应';
        }
        if (daemonDot) {
            daemonDot.className = `link-dot ${healthy ? 'online' : 'offline'}`;
        }
        if (apiDot) {
            apiDot.className = `link-dot ${healthy ? 'online' : 'offline'}`;
        }
    }
    
    showStatus(message, type) {
        // 可以添加一个状态提示
        console.log(`[HealthCheck] 状态: ${message} (${type})`);
    }
}

// 全局实例
window.healthChecker = new HealthChecker();

// 页面完全加载后再启动健康检查（避免竞态条件）
window.addEventListener('load', () => {
    // 延迟 500ms 启动，确保所有资源加载完成
    setTimeout(() => {
        window.healthChecker.start();
    }, 500);
});
