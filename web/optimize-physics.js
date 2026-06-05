/**
 * 自动参数优化器
 * 根据图谱特征自动调整物理参数
 */

class PhysicsOptimizer {
  constructor() {
    this.presets = this.initPresets();
  }

  /**
   * 初始化预设配置
   */
  initPresets() {
    return {
      // 小型图谱（< 50 节点）
      small: {
        repulsion: -80,
        springStrength: 0.04,
        idealLinkLength: 80,
        damping: 0.90,
        centerForce: 0.02,
        maxVelocity: 6,
        coolingFactor: 0.990,
        convergenceThreshold: 0.3,
        convergenceFrames: 45
      },
      // 中型图谱（50-200 节点）
      medium: {
        repulsion: -120,
        springStrength: 0.03,
        idealLinkLength: 100,
        damping: 0.92,
        centerForce: 0.01,
        maxVelocity: 8,
        coolingFactor: 0.995,
        convergenceThreshold: 0.5,
        convergenceFrames: 60
      },
      // 大型图谱（200-500 节点）
      large: {
        repulsion: -150,
        springStrength: 0.02,
        idealLinkLength: 120,
        damping: 0.94,
        centerForce: 0.008,
        maxVelocity: 10,
        coolingFactor: 0.997,
        convergenceThreshold: 0.8,
        convergenceFrames: 90
      },
      // 超大型图谱（> 500 节点）
      xlarge: {
        repulsion: -200,
        springStrength: 0.015,
        idealLinkLength: 150,
        damping: 0.96,
        centerForce: 0.005,
        maxVelocity: 12,
        coolingFactor: 0.998,
        convergenceThreshold: 1.0,
        convergenceFrames: 120
      }
    };
  }

  /**
   * 根据节点数量选择预设
   * @param {number} nodeCount - 节点数量
   * @returns {object} 物理参数
   */
  getPresetForSize(nodeCount) {
    if (nodeCount < 50) {
      return this.presets.small;
    } else if (nodeCount < 200) {
      return this.presets.medium;
    } else if (nodeCount < 500) {
      return this.presets.large;
    } else {
      return this.presets.xlarge;
    }
  }

  /**
   * 自动优化参数
   * @param {object} graphViz - GraphViz 实例
   * @returns {object} 优化后的参数
   */
  optimize(graphViz) {
    const nodeCount = graphViz.nodes.length;
    const linkCount = graphViz.links.length;

    // 获取基础预设
    const basePreset = this.getPresetForSize(nodeCount);

    // 根据图谱密度调整
    const density = linkCount / Math.max(nodeCount, 1);
    const adjustments = this.calculateAdjustments(nodeCount, linkCount, density);

    // 合并参数
    const optimizedParams = {
      ...basePreset,
      ...adjustments
    };

    console.log(`[PhysicsOptimizer] 优化参数:
      节点数: ${nodeCount}
      边数: ${linkCount}
      密度: ${density.toFixed(2)}
      预设: ${this.getPresetName(nodeCount)}`);

    return optimizedParams;
  }

  /**
   * 计算参数调整
   */
  calculateAdjustments(nodeCount, linkCount, density) {
    const adjustments = {};

    // 密度调整
    if (density > 3) {
      // 高密度图谱：增加斥力，减少弹簧强度
      adjustments.repulsion = -180;
      adjustments.springStrength = 0.02;
      adjustments.idealLinkLength = 130;
    } else if (density < 1.5) {
      // 低密度图谱：减少斥力，增加弹簧强度
      adjustments.repulsion = -100;
      adjustments.springStrength = 0.04;
      adjustments.idealLinkLength = 90;
    }

    // 节点数量调整
    if (nodeCount > 300) {
      // 大型图谱需要更慢的冷却
      adjustments.coolingFactor = 0.997;
      adjustments.convergenceFrames = 90;
    }

    return adjustments;
  }

  /**
   * 获取预设名称
   */
  getPresetName(nodeCount) {
    if (nodeCount < 50) return 'small';
    if (nodeCount < 200) return 'medium';
    if (nodeCount < 500) return 'large';
    return 'xlarge';
  }

  /**
   * 应用优化参数到 GraphViz
   * @param {object} graphViz - GraphViz 实例
   */
  applyTo(graphViz) {
    const optimizedParams = this.optimize(graphViz);

    // 更新物理参数
    Object.assign(graphViz.physics, optimizedParams);

    console.log('[PhysicsOptimizer] 参数已应用');
    return optimizedParams;
  }

  /**
   * 获取所有预设
   */
  getPresets() {
    return this.presets;
  }

  /**
   * 添加自定义预设
   * @param {string} name - 预设名称
   * @param {object} params - 预设参数
   */
  addPreset(name, params) {
    this.presets[name] = params;
    console.log(`[PhysicsOptimizer] 添加自定义预设: ${name}`);
  }

  /**
   * 根据当前状态微调参数
   * @param {object} graphViz - GraphViz 实例
   * @param {object} convergenceStatus - 收敛状态
   */
  fineTune(graphViz, convergenceStatus) {
    const { currentVelocity, isConverged } = convergenceStatus;

    if (isConverged) {
      // 已收敛，不需要调整
      return;
    }

    // 如果速度过高，增加阻尼
    if (currentVelocity > 2.0) {
      graphViz.physics.damping = Math.min(0.98, graphViz.physics.damping + 0.01);
      console.log('[PhysicsOptimizer] 速度过高，增加阻尼:', graphViz.physics.damping);
    }

    // 如果速度过低但未收敛，减少阻尼
    if (currentVelocity < 0.2 && !isConverged) {
      graphViz.physics.damping = Math.max(0.85, graphViz.physics.damping - 0.01);
      console.log('[PhysicsOptimizer] 速度过低，减少阻尼:', graphViz.physics.damping);
    }
  }

  /**
   * 重置为默认参数
   */
  resetToDefaults(graphViz) {
    const defaultParams = this.getPresetForSize(graphViz.nodes.length);
    Object.assign(graphViz.physics, defaultParams);
    console.log('[PhysicsOptimizer] 重置为默认参数');
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PhysicsOptimizer;
} else {
  window.PhysicsOptimizer = PhysicsOptimizer;
}
