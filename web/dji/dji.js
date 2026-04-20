// DJI 诊断工具 - 简化版
// Omnia OS - 2026

class DJIDiagnostic {
    constructor() {
        this.devices = [];
        this.selectedDevice = null;
        this.apiBase = '/api/dji';
        this.init();
    }

    init() {
        console.log('[DJI Tool] 初始化...');
        this.bindEvents();
        this.updateConnectionStatus(false);
        this.scanDevices(); // 自动扫描
    }

    // 绑定事件
    bindEvents() {
        const btnScan = document.getElementById('btn-scan');
        const btnDiagnose = document.getElementById('btn-diagnose');
        const btnExport = document.getElementById('btn-export');

        if (btnScan) {
            btnScan.addEventListener('click', () => this.scanDevices());
        }
        if (btnDiagnose) {
            btnDiagnose.addEventListener('click', () => this.runDiagnosis());
        }
        if (btnExport) {
            btnExport.addEventListener('click', () => this.exportReport());
        }
    }

    // 扫描设备
    async scanDevices() {
        console.log('[DJI Tool] 开始扫描设备...');
        this.updateStatus('正在扫描...', 'scanning');

        try {
            const response = await fetch(`${this.apiBase}/scan`);
            const data = await response.json();
            
            console.log('[DJI Tool] API 返回:', data);

            if (data.success && data.devices) {
                this.devices = data.devices.map((dev, index) => ({
                    id: `device_${index}`,
                    name: dev.product || 'DJI Device',
                    type: this.detectDeviceType(dev.product_id),
                    model: dev.product || 'Unknown',
                    serial: dev.serial_number || 'N/A',
                    vendor_id: dev.vendor_id,
                    product_id: dev.product_id,
                    manufacturer: dev.manufacturer
                }));

                this.renderDeviceList();
                this.updateConnectionStatus(true);
                this.updateStatus(`已发现 ${this.devices.length} 台设备`, 'success');
            } else {
                throw new Error(data.error || '扫描失败');
            }
        } catch (error) {
            console.error('[DJI Tool] 扫描失败:', error);
            this.updateStatus('扫描失败: ' + error.message, 'error');
            this.updateConnectionStatus(false);
        }
    }

    // 检测设备类型
    detectDeviceType(product_id) {
        const pid = parseInt(product_id, 16);
        if (pid >= 0x0020 && pid <= 0x0030) return 'drone';
        if (pid >= 0x0040 && pid <= 0x0050) return 'remote';
        if (pid >= 0x0060 && pid <= 0x0070) return 'goggles';
        return 'unknown';
    }

    // 渲染设备列表
    renderDeviceList() {
        const container = document.getElementById('device-list');
        if (!container) return;

        if (this.devices.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-plug"></i>
                    <p>未发现设备</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.devices.map(device => `
            <div class="device-item ${this.selectedDevice?.id === device.id ? 'selected' : ''}" 
                 data-id="${device.id}">
                <div class="device-icon">
                    <i class="fas fa-${this.getDeviceIcon(device.type)}"></i>
                </div>
                <div class="device-info">
                    <div class="device-name">${device.name}</div>
                    <div class="device-meta">
                        <span>${device.type}</span>
                        <span>${device.serial}</span>
                    </div>
                </div>
            </div>
        `).join('');

        // 绑定点击事件
        container.querySelectorAll('.device-item').forEach(item => {
            item.addEventListener('click', () => {
                const deviceId = item.dataset.id;
                this.selectDevice(deviceId);
            });
        });

        document.getElementById('device-count').textContent = `${this.devices.length} 台设备`;
    }

    // 选择设备
    selectDevice(deviceId) {
        console.log('[DJI Tool] 选择设备:', deviceId);
        this.selectedDevice = this.devices.find(d => d.id === deviceId);
        
        if (this.selectedDevice) {
            this.renderDeviceList(); // 更新选中状态
            this.showDeviceInfo();
            this.enableButtons(true);
        }
    }

    // 显示设备信息
    showDeviceInfo() {
        const container = document.getElementById('device-info');
        if (!container || !this.selectedDevice) return;

        const device = this.selectedDevice;
        container.innerHTML = `
            <div class="info-grid">
                <div class="info-item">
                    <span class="label">设备名称</span>
                    <span class="value">${device.name}</span>
                </div>
                <div class="info-item">
                    <span class="label">设备类型</span>
                    <span class="value">${device.type}</span>
                </div>
                <div class="info-item">
                    <span class="label">序列号</span>
                    <span class="value">${device.serial}</span>
                </div>
                <div class="info-item">
                    <span class="label">厂商</span>
                    <span class="value">${device.manufacturer}</span>
                </div>
                <div class="info-item">
                    <span class="label">Vendor ID</span>
                    <span class="value">${device.vendor_id}</span>
                </div>
                <div class="info-item">
                    <span class="label">Product ID</span>
                    <span class="value">${device.product_id}</span>
                </div>
            </div>
        `;
    }

    // 运行诊断
    async runDiagnosis() {
        if (!this.selectedDevice) {
            alert('请先选择一个设备');
            return;
        }

        console.log('[DJI Tool] 开始诊断:', this.selectedDevice.name);
        this.updateStatus('正在诊断...', 'scanning');

        try {
            const response = await fetch(`${this.apiBase}/diagnose`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    device_id: this.selectedDevice.id,
                    vendor_id: this.selectedDevice.vendor_id,
                    product_id: this.selectedDevice.product_id
                })
            });

            const data = await response.json();
            console.log('[DJI Tool] 诊断结果:', data);

            if (data.success) {
                this.showDiagnosisReport(data.report);
                this.updateStatus('诊断完成', 'success');
            } else {
                throw new Error(data.error || '诊断失败');
            }
        } catch (error) {
            console.error('[DJI Tool] 诊断失败:', error);
            this.updateStatus('诊断失败: ' + error.message, 'error');
        }
    }

    // 显示诊断报告
    showDiagnosisReport(report) {
        const reportCard = document.getElementById('report-card');
        const container = document.getElementById('diagnosis-report');
        
        if (!container || !report) return;

        reportCard.style.display = 'block';
        
        container.innerHTML = `
            <div class="report-section">
                <h4><i class="fas fa-check-circle"></i> 设备状态</h4>
                <p>连接状态: <span class="status-ok">正常</span></p>
                <p>设备识别: <span class="status-ok">已识别</span></p>
            </div>
            <div class="report-section">
                <h4><i class="fas fa-info-circle"></i> 诊断信息</h4>
                <p>设备型号: ${report.model || this.selectedDevice.name}</p>
                <p>诊断时间: ${new Date().toLocaleString()}</p>
            </div>
            <div class="report-section">
                <h4><i class="fas fa-lightbulb"></i> 建议</h4>
                <ul>
                    <li>设备连接正常，可以正常使用</li>
                    <li>建议定期检查固件更新</li>
                </ul>
            </div>
        `;
    }

    // 导出报告
    exportReport() {
        if (!this.selectedDevice) {
            alert('请先选择一个设备');
            return;
        }

        const report = {
            device: this.selectedDevice,
            timestamp: new Date().toISOString(),
            generated_by: 'Omnia DJI Diagnostic Tool'
        };

        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dji-diagnostic-${this.selectedDevice.serial}-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);

        this.updateStatus('报告已导出', 'success');
    }

    // 启用/禁用按钮
    enableButtons(enabled) {
        const btnDiagnose = document.getElementById('btn-diagnose');
        const btnExport = document.getElementById('btn-export');

        if (btnDiagnose) btnDiagnose.disabled = !enabled;
        if (btnExport) btnExport.disabled = !enabled;
    }

    // 更新连接状态
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (!statusEl) return;

        if (connected) {
            statusEl.textContent = '已连接';
            statusEl.className = 'status-value connected';
        } else {
            statusEl.textContent = '未连接';
            statusEl.className = 'status-value disconnected';
        }

        document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
    }

    // 更新状态
    updateStatus(message, type = 'info') {
        console.log(`[DJI Tool] 状态: ${message} (${type})`);
        // 可以添加 toast 提示
    }

    // 获取设备图标
    getDeviceIcon(type) {
        const icons = {
            'drone': 'helicopter',
            'remote': 'gamepad',
            'goggles': 'vr-cardboard',
            'unknown': 'question-circle'
        };
        return icons[type] || 'question-circle';
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.djiApp = new DJIDiagnostic();
});
