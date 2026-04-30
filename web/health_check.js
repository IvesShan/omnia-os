/**
 * Omnia Frontend Health Check v3
 * 
 * 修复：
 * 1. 使用轻量 /health 端点（不触发 git/psutil）
 * 2. 失败计数器正确重置
 * 3. 不直接调用 loadStatus（由 app.js 防抖机制处理）
 * 4. 自动刷新阈值提高到 10 次
 */

class HealthChecker {
    constructor() {
        this.checkInterval = 30000; // 30秒检查一次
        this.timeout = 10000; // 10秒超时（轻量端点应该很快）
        this.failures = 0;
        this.maxFailures = 3;       // 连续失败 3 次显示横幅
        this.autoReloadAt = 10;     // 连续失败 10 次才自动刷新
        this.isHealthy = true;
        this.timer = null;
        this.banner = null;
        this.lastCheckTime = 0;
        this._checking = false;     // 防止并发检查
    }
    
    start() {
        console.log('[HealthCheck] 启动健康检查 v3');
        this.timer = setInterval(() => this.check(), this.checkInterval);
        
        // 页面恢复可见时立即检查（加防抖）
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                const elapsed = Date.now() - this.lastCheckTime;
                // 离线超过 60 秒才检查，避免频繁切换标签页时重复检查
                if (elapsed > 60000) {
                    console.log(`[HealthCheck] 页面恢复可见 (离线 ${Math.round(elapsed/1000)}s)，立即检查`);
                    this.check();
                }
            }
        });
        
        // 网络恢复时立即检查
        window.addEventListener('online', () => {
            console.log('[HealthCheck] 网络恢复，立即检查');
            this.check();
        });
        
        // 网络断开时立即标记
        window.addEventListener('offline', () => {
            console.log('[HealthCheck] 网络断开');
            this.onFailure('网络断开');
        });
    }
    
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    async check() {
        // 防止并发检查
        if (this._checking) return;
        this._checking = true;
        this.lastCheckTime = Date.now();
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);
            
            // 用轻量 /health 端点，不触发 git/psutil 等重操作
            const response = await fetch(`/health`, {
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
            if (error.name === 'AbortError') {
                this.onFailure('请求超时');
            } else {
                this.onFailure(error.message);
            }
        } finally {
            this._checking = false;
        }
    }
    
    onSuccess() {
        if (!this.isHealthy) {
            console.log('[HealthCheck] ✅ 连接恢复');
            this.showBanner('连接已恢复', 'success');
            // 3秒后自动隐藏成功横幅
            setTimeout(() => this.hideBanner(), 3000);
        }
        // 关键：成功时重置计数器
        this.failures = 0;
        this.isHealthy = true;
    }
    
    onFailure(reason) {
        this.failures++;
        console.warn(`[HealthCheck] ⚠️ 检查失败 (${this.failures}/${this.maxFailures}): ${reason}`);
        
        if (this.failures >= this.maxFailures) {
            this.isHealthy = false;
            this.showBanner(`连接中断 (${reason}) · 已重试 ${this.failures} 次`, 'error');
            
            // 连续失败过多，自动刷新页面
            if (this.failures >= this.autoReloadAt) {
                console.log('[HealthCheck] 🔄 连续失败过多，自动刷新页面');
                this.showBanner('连接长时间中断，正在刷新页面...', 'error');
                setTimeout(() => location.reload(), 2000);
            }
        }
    }
    
    showBanner(message, type) {
        if (!this.banner) {
            this.banner = document.createElement('div');
            this.banner.id = 'health-banner';
            this.banner.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; z-index: 99999;
                padding: 8px 16px; text-align: center; font-size: 13px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                transition: all 0.3s ease; cursor: pointer;
                backdrop-filter: blur(10px);
            `;
            this.banner.onclick = () => {
                this.failures = 0;
                this.check();
            };
            document.body.appendChild(this.banner);
        }
        
        if (type === 'error') {
            this.banner.style.background = 'rgba(248,113,113,0.15)';
            this.banner.style.color = '#f87171';
            this.banner.style.borderBottom = '1px solid rgba(248,113,113,0.3)';
        } else {
            this.banner.style.background = 'rgba(52,211,153,0.15)';
            this.banner.style.color = '#34d399';
            this.banner.style.borderBottom = '1px solid rgba(52,211,153,0.3)';
        }
        
        this.banner.textContent = message;
        this.banner.style.display = 'block';
    }
    
    hideBanner() {
        if (this.banner) {
            this.banner.style.display = 'none';
        }
    }
}

// 全局实例
window.healthChecker = new HealthChecker();

// 页面完全加载后再启动
window.addEventListener('load', () => {
    setTimeout(() => {
        window.healthChecker.start();
    }, 500);
});
