/**
 * 视觉风格切换器
 * 支持多种视觉风格：Data Drift, Obsidian, Swiss Pulse, Shadow Cut
 */

class StyleSwitcher {
  constructor(graphViz) {
    this.graphViz = graphViz;
    this.currentStyle = 'data-drift';
    this.styles = this.initStyles();
  }

  /**
   * 初始化视觉风格
   */
  initStyles() {
    return {
      'data-drift': {
        name: 'Data Drift',
        description: 'Futuristic, immersive - AI/ML 知识图谱',
        colors: {
          bg: '#0f1117',
          grid: 'rgba(100, 116, 139, 0.08)',
          nodeDefault: '#64748b',
          nodeHighlight: '#ff8a00',
          linkDefault: 'rgba(100, 116, 139, 0.2)',
          linkHighlight: 'rgba(255, 138, 0, 0.6)',
          particle: '#22d3ee',
          text: '#e2e8f0'
        }
      },
      'obsidian': {
        name: 'Obsidian',
        description: '经典 Obsidian 风格 - 知识管理和笔记图谱',
        colors: {
          bg: '#1e1e1e',
          grid: 'rgba(100, 116, 139, 0.1)',
          nodeDefault: '#8b949e',
          nodeHighlight: '#58a6ff',
          linkDefault: 'rgba(139, 148, 158, 0.3)',
          linkHighlight: 'rgba(88, 166, 255, 0.6)',
          particle: '#f0883e',
          text: '#c9d1d9'
        }
      },
      'swiss-pulse': {
        name: 'Swiss Pulse',
        description: 'Clinical, precise - SaaS 和数据仪表板',
        colors: {
          bg: '#ffffff',
          grid: 'rgba(0, 0, 0, 0.05)',
          nodeDefault: '#6b7280',
          nodeHighlight: '#3b82f6',
          linkDefault: 'rgba(107, 114, 128, 0.2)',
          linkHighlight: 'rgba(59, 130, 246, 0.6)',
          particle: '#10b981',
          text: '#1f2937'
        }
      },
      'shadow-cut': {
        name: 'Shadow Cut',
        description: 'Dark, cinematic - 安全和调查内容',
        colors: {
          bg: '#000000',
          grid: 'rgba(255, 255, 255, 0.03)',
          nodeDefault: '#4b5563',
          nodeHighlight: '#ef4444',
          linkDefault: 'rgba(75, 85, 99, 0.3)',
          linkHighlight: 'rgba(239, 68, 68, 0.6)',
          particle: '#f97316',
          text: '#f3f4f6'
        }
      }
    };
  }

  /**
   * 切换到指定风格
   * @param {string} styleName - 风格名称
   * @returns {boolean} 是否成功
   */
  switchTo(styleName) {
    const style = this.styles[styleName];
    if (!style) {
      console.error(`[StyleSwitcher] 未知风格: ${styleName}`);
      return false;
    }

    // 更新当前风格
    this.currentStyle = styleName;

    // 更新 GraphViz 颜色
    this.graphViz.colors = { ...style.colors };

    console.log(`[StyleSwitcher] 切换到风格: ${style.name}`);
    return true;
  }

  /**
   * 获取当前风格
   */
  getCurrentStyle() {
    return {
      id: this.currentStyle,
      ...this.styles[this.currentStyle]
    };
  }

  /**
   * 获取所有可用风格
   */
  getAvailableStyles() {
    return Object.entries(this.styles).map(([id, style]) => ({
      id,
      ...style
    }));
  }

  /**
   * 添加自定义风格
   * @param {string} id - 风格 ID
   * @param {object} style - 风格配置
   */
  addStyle(id, style) {
    this.styles[id] = style;
    console.log(`[StyleSwitcher] 添加自定义风格: ${id}`);
  }

  /**
   * 移除风格
   * @param {string} id - 风格 ID
   */
  removeStyle(id) {
    if (id === 'data-drift') {
      console.warn('[StyleSwitcher] 不能移除默认风格');
      return;
    }

    delete this.styles[id];
    console.log(`[StyleSwitcher] 移除风格: ${id}`);
  }

  /**
   * 随机切换风格
   */
  randomSwitch() {
    const styleIds = Object.keys(this.styles);
    const randomIndex = Math.floor(Math.random() * styleIds.length);
    const randomStyle = styleIds[randomIndex];
    return this.switchTo(randomStyle);
  }

  /**
   * 获取风格预览（用于 UI 显示）
   */
  getStylePreview(styleName) {
    const style = this.styles[styleName];
    if (!style) return null;

    return {
      name: style.name,
      description: style.description,
      previewColors: [
        style.colors.nodeHighlight,
        style.colors.particle,
        style.colors.bg
      ]
    };
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StyleSwitcher;
} else {
  window.StyleSwitcher = StyleSwitcher;
}
