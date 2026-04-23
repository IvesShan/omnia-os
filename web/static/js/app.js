/**
 * Omnia 管理面板 - 前端逻辑
 */

// API 基础路径
const API_BASE = '/api';

// 状态
let currentTab = 'dashboard';
let logsEventSource = null;

// ============ 工具函数 ============

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 仪表盘 ============

async function loadDashboard() {
    // 加载系统状态
    const status = await fetchAPI('/status');
    if (status) {
        document.getElementById('system-status').textContent = status.status === 'running' ? '运行中' : '已停止';
        document.getElementById('memory-count').textContent = status.memory_count;
        document.getElementById('skills-count').textContent = status.skills_count;
        document.getElementById('last-activity').textContent = formatTime(status.last_activity);
        
        // 更新环境信息
        if (status.env) {
            const env = status.env;
            document.getElementById('env-host').textContent = env.hostname || '—';
            document.getElementById('env-model').textContent = (env.provider && env.model) 
                ? `${env.provider} / ${env.model}` 
                : (env.model || '—');
            document.getElementById('env-shell').textContent = env.shell || '—';
            document.getElementById('env-os').textContent = env.os || '—';
        }
    }
    
    // 加载记忆统计
    const stats = await fetchAPI('/memory/stats');
    if (stats) {
        document.getElementById('facts-count').textContent = stats.facts || 0;
        document.getElementById('relations-count').textContent = stats.relations || 0;
        document.getElementById('habits-count').textContent = stats.habits || 0;
        document.getElementById('timeline-count').textContent = stats.timeline || 0;
    }
}
}

// ============ 记忆管理 ============

async function searchMemory() {
    const query = document.getElementById('memory-search-input').value.trim();
    const layer = document.getElementById('memory-layer-filter').value;
    
    if (!query) {
        document.getElementById('memory-results').innerHTML = '<p class="text-gray-500 text-center">请输入搜索关键词</p>';
        return;
    }
    
    const params = new URLSearchParams({ q: query });
    if (layer) params.append('layer', layer);
    
    const result = await fetchAPI(`/memory/search?${params}`);
    
    if (result && result.results) {
        if (result.results.length === 0) {
            document.getElementById('memory-results').innerHTML = '<p class="text-gray-500 text-center">未找到匹配的记忆</p>';
            return;
        }
        
        const html = result.results.map(entry => `
            <div class="memory-entry p-4 mb-3 bg-gray-50 rounded-lg border-l-4 border-indigo-500">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <span class="inline-block px-2 py-1 text-xs font-medium bg-indigo-100 text-indigo-800 rounded mb-2">${entry.category}</span>
                        <h4 class="font-medium text-gray-900">${escapeHtml(entry.key)}</h4>
                        <p class="text-sm text-gray-600 mt-1">${escapeHtml(typeof entry.value === 'object' ? JSON.stringify(entry.value, null, 2) : entry.value)}</p>
                    </div>
                    <span class="text-xs text-gray-400">${entry.source}</span>
                </div>
            </div>
        `).join('');
        
        document.getElementById('memory-results').innerHTML = `
            <p class="text-sm text-gray-500 mb-4">找到 ${result.count} 条记忆</p>
            ${html}
        `;
    }
}

// ============ 技能管理 ============

async function loadSkills() {
    const result = await fetchAPI('/skills');
    
    if (result && result.skills) {
        if (result.skills.length === 0) {
            document.getElementById('skills-list').innerHTML = '<p class="p-6 text-gray-500 text-center">暂无已安装技能</p>';
            return;
        }
        
        const html = result.skills.map(skill => `
            <div class="skill-card p-4 flex items-center justify-between">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                            <span class="text-white font-bold">${skill.name.charAt(0).toUpperCase()}</span>
                        </div>
                    </div>
                    <div class="ml-4">
                        <h4 class="font-medium text-gray-900">${skill.name}</h4>
                        <p class="text-sm text-gray-500">${skill.type}</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="px-2 py-1 text-xs font-medium ${skill.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'} rounded">
                        ${skill.enabled ? '已启用' : '已禁用'}
                    </span>
                </div>
            </div>
        `).join('');
        
        document.getElementById('skills-list').innerHTML = html;
    }
}

// ============ 日志监控 ============

async function loadLogs() {
    const result = await fetchAPI('/logs?lines=200');
    const container = document.getElementById('logs-container');
    
    if (result && result.logs) {
        if (result.logs.length === 0) {
            container.innerHTML = '<p class="text-gray-400">暂无日志</p>';
            return;
        }
        
        const html = result.logs.map(line => {
            let className = 'log-line';
            if (line.includes('ERROR') || line.includes('error')) className += ' error';
            else if (line.includes('WARNING') || line.includes('warning')) className += ' warning';
            else if (line.includes('INFO') || line.includes('info')) className += ' info';
            else className += ' debug';
            
            return `<div class="${className}">${escapeHtml(line)}</div>`;
        }).join('');
        
        container.innerHTML = html;
        
        if (document.getElementById('auto-scroll').checked) {
            container.scrollTop = container.scrollHeight;
        }
    }
}

function startLogStream() {
    if (logsEventSource) {
        logsEventSource.close();
    }
    
    logsEventSource = new EventSource('/api/logs/stream');
    const container = document.getElementById('logs-container');
    
    logsEventSource.onmessage = (event) => {
        const line = event.data;
        let className = 'log-line';
        if (line.includes('ERROR') || line.includes('error')) className += ' error';
        else if (line.includes('WARNING') || line.includes('warning')) className += ' warning';
        else if (line.includes('INFO') || line.includes('info')) className += ' info';
        else className += ' debug';
        
        const div = document.createElement('div');
        div.className = className;
        div.textContent = line;
        container.appendChild(div);
        
        // 限制显示行数
        while (container.children.length > 500) {
            container.removeChild(container.firstChild);
        }
        
        if (document.getElementById('auto-scroll').checked) {
            container.scrollTop = container.scrollHeight;
        }
    };
}

// ============ 神经图谱 ============

async function loadGraph() {
    const container = document.getElementById('graph-container');
    
    // 简单的图谱可视化（使用 Canvas）
    const canvas = document.createElement('canvas');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    container.innerHTML = '';
    container.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    // 获取记忆数据
    const facts = await fetchAPI('/memory/facts');
    const relations = await fetchAPI('/memory/relations');
    
    if (!facts && !relations) {
        container.innerHTML = '<p class="text-gray-500">无法加载图谱数据</p>';
        return;
    }
    
    // 简单的节点布局
    const nodes = [];
    const allData = { ...(facts?.data || {}), ...(relations?.data || {}) };
    
    Object.keys(allData).forEach((key, i) => {
        const angle = (i / Object.keys(allData).length) * Math.PI * 2;
        const radius = Math.min(canvas.width, canvas.height) * 0.35;
        nodes.push({
            x: canvas.width / 2 + Math.cos(angle) * radius,
            y: canvas.height / 2 + Math.sin(angle) * radius,
            label: key.length > 10 ? key.substring(0, 10) + '...' : key
        });
    });
    
    // 绘制
    ctx.fillStyle = '#f9fafb';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 绘制连线
    ctx.strokeStyle = 'rgba(99, 102, 241, 0.2)';
    ctx.lineWidth = 1;
    nodes.forEach((node, i) => {
        nodes.forEach((other, j) => {
            if (i < j && Math.random() > 0.7) {
                ctx.beginPath();
                ctx.moveTo(node.x, node.y);
                ctx.lineTo(other.x, other.y);
                ctx.stroke();
            }
        });
    });
    
    // 绘制节点
    nodes.forEach(node => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = '#6366f1';
        ctx.fill();
        
        ctx.fillStyle = '#374151';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + 16);
    });
    
    // 中心节点
    ctx.beginPath();
    ctx.arc(canvas.width / 2, canvas.height / 2, 20, 0, Math.PI * 2);
    ctx.fillStyle = '#8b5cf6';
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Omnia', canvas.width / 2, canvas.height / 2 + 4);
}

// ============ Tab 切换 ============

function switchTab(tabName) {
    // 隐藏所有 tab
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    
    // 显示当前 tab
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');
    
    // 更新导航样式
    document.querySelectorAll('.tab-link').forEach(el => {
        el.classList.remove('border-indigo-500', 'text-gray-900');
        el.classList.add('border-transparent', 'text-gray-500');
    });
    
    const activeLink = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeLink) {
        activeLink.classList.remove('border-transparent', 'text-gray-500');
        activeLink.classList.add('border-indigo-500', 'text-gray-900');
    }
    
    currentTab = tabName;
    
    // 加载对应内容
    switch (tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'memory':
            // 清空搜索结果
            break;
        case 'graph':
            loadGraph();
            break;
        case 'skills':
            loadSkills();
            break;
        case 'logs':
            loadLogs();
            startLogStream();
            break;
    }
}

// ============ 事件绑定 ============

document.addEventListener('DOMContentLoaded', () => {
    // Tab 切换
    document.querySelectorAll('.tab-link').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(el.dataset.tab);
        });
    });
    
    // 记忆搜索
    document.getElementById('memory-search-btn').addEventListener('click', searchMemory);
    document.getElementById('memory-search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMemory();
    });
    
    // 清空日志
    document.getElementById('clear-logs-btn').addEventListener('click', () => {
        document.getElementById('logs-container').innerHTML = '';
    });
    
    // 初始加载
    loadDashboard();
    
    // 定时刷新仪表盘
    setInterval(() => {
        if (currentTab === 'dashboard') {
            loadDashboard();
        }
    }, 30000);
});

// 页面卸载时关闭日志流
window.addEventListener('beforeunload', () => {
    if (logsEventSource) {
        logsEventSource.close();
    }
});
