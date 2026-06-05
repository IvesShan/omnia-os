/**
 * 收敛检测算法
 * 检测力导向模拟是否真正收敛（所有节点速度 < 阈值）
 */

class ConvergenceDetector {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.5; // 速度阈值（像素/帧）
    this.requiredFrames = options.requiredFrames || 60; // 连续帧数
    this.frameCount = 0;
    this.isConverged = false;
    this.history = [];
  }

  /**
   * 检查节点是否收敛
   * @param {Array} nodes - 节点数组，每个节点有 vx, vy
   * @returns {boolean} 是否收敛
   */
  check(nodes) {
    if (nodes.length === 0) return false;

    // 计算平均速度
    const avgVelocity = this.calculateAverageVelocity(nodes);
    
    // 记录历史
    this.history.push(avgVelocity);
    if (this.history.length > this.requiredFrames) {
      this.history.shift();
    }

    // 检查是否连续 N 帧低于阈值
    if (avgVelocity < this.threshold) {
      this.frameCount++;
      if (this.frameCount >= this.requiredFrames) {
        this.isConverged = true;
        return true;
      }
    } else {
      this.frameCount = 0;
      this.isConverged = false;
    }

    return false;
  }

  /**
   * 计算平均速度
   */
  calculateAverageVelocity(nodes) {
    let totalSpeed = 0;
    
    for (const node of nodes) {
      const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
      totalSpeed += speed;
    }
    
    return totalSpeed / nodes.length;
  }

  /**
   * 获取收敛状态
   */
  getStatus() {
    return {
      isConverged: this.isConverged,
      frameCount: this.frameCount,
      requiredFrames: this.requiredFrames,
      currentVelocity: this.history.length > 0 ? this.history[this.history.length - 1] : 0,
      threshold: this.threshold
    };
  }

  /**
   * 重置检测器
   */
  reset() {
    this.frameCount = 0;
    this.isConverged = false;
    this.history = [];
  }

  /**
   * 调整阈值
   */
  setThreshold(threshold) {
    this.threshold = threshold;
    this.reset();
  }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ConvergenceDetector;
} else {
  window.ConvergenceDetector = ConvergenceDetector;
}
