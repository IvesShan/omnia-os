// 神经图谱可视化 - 极简静态版本
// 无动画、无 Canvas、纯 CSS - 性能最优

const GraphViz = {
  nodes: [],
  edges: [],
  
  init() {
    console.log('[GraphViz] 极简静态模式');
    this.loadStats();
    
    const canvas = document.getElementById('graph-canvas');
    const placeholder = canvas?.querySelector('.graph-placeholder');
    if (placeholder) {
      placeholder.addEventListener('click', () => this.loadGraph());
      placeholder.style.cursor = 'pointer';
    }
    
    this.bindSearch();
  },
  
  async loadStats() {
    try {
      const res = await fetch('/api/graph/stats');
      const stats = await res.json();
      
      document.getElementById('gs-nodes').textContent = stats.total_nodes || 0;
      document.getElementById('gs-edges').textContent = stats.total_edges || 0;
    } catch (err) {
      console.error('[GraphViz] 加载统计失败:', err);
    }
  },
  
  async loadGraph() {
    const canvas = document.getElementById('graph-canvas');
    if (!canvas) return;
    
    canvas.innerHTML = '<div class="graph-loading">加载中...</div>';
    
    try {
      const res = await fetch('/api/graph?limit=50');
      const data = await res.json();
      
      this.nodes = data.nodes || [];
      this.edges = data.edges || [];
      
      // 构建节点索引
      const nodeMap = {};
      this.nodes.forEach(n => nodeMap[n.id] = n);
      
      // 计算圆形布局
      const layout = this.calculateLayout(canvas.offsetWidth, canvas.offsetHeight);
      
      // 渲染图谱
      let html = '<div class="graph-simple-container">';
      
      // 先画连线（SVG）
      html += '<svg class="graph-edges-svg">';
      this.edges.forEach(edge => {
        const source = nodeMap[edge.source];
        const target = nodeMap[edge.target];
        if (source && target && layout[source.id] && layout[target.id]) {
          const s = layout[source.id];
          const t = layout[target.id];
          html += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" 
                        stroke="rgba(34, 211, 238, 0.2)" stroke-width="1"/>`;
        }
      });
      html += '</svg>';
      
      // 再画节点（DOM）
      this.nodes.forEach(node => {
        const pos = layout[node.id];
        if (pos) {
          const type = (node.type || 'UNKNOWN').toLowerCase();
          const size = Math.max(20, Math.min(40, 15 + (node.access_count || 0) * 0.5));
          html += `
            <div class="graph-node-simple ${type}" 
                 style="left: ${pos.x - size/2}px; top: ${pos.y - size/2}px; width: ${size}px; height: ${size}px;"
                 title="${node.name}\n类型: ${node.type}\n访问: ${node.access_count || 0}"
                 data-id="${node.id}">
              <span class="node-label">${this.shorten(node.name, 6)}</span>
            </div>
          `;
        }
      });
      
      html += '</div>';
      canvas.innerHTML = html;
      
      // 绑定节点点击
      canvas.querySelectorAll('.graph-node-simple').forEach(el => {
        el.onclick = () => this.showNodeInfo(el.dataset.id);
      });
      
    } catch (err) {
      console.error('[GraphViz] 加载失败:', err);
      canvas.innerHTML = '<div class="graph-error">加载失败</div>';
    }
  },
  
  calculateLayout(width, height) {
    const layout = {};
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 30;
    
    this.nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / this.nodes.length;
      layout[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
    
    return layout;
  },
  
  shorten(text, maxLen) {
    if (!text) return '';
    return text.length > maxLen ? text.substring(0, maxLen - 1) + '…' : text;
  },
  
  bindSearch() {
    const searchBtn = document.getElementById('graph-search-btn');
    const searchInput = document.getElementById('graph-search-input');
    
    if (searchBtn && searchInput) {
      searchBtn.onclick = () => this.highlightNode(searchInput.value);
      searchInput.onkeypress = (e) => {
        if (e.key === 'Enter') this.highlightNode(searchInput.value);
      };
    }
  },
  
  highlightNode(query) {
    if (!query) return;
    
    const nodes = document.querySelectorAll('.graph-node-simple');
    nodes.forEach(n => n.classList.remove('highlighted'));
    
    const found = Array.from(nodes).find(n => 
      (n.title || '').toLowerCase().includes(query.toLowerCase())
    );
    
    if (found) {
      found.classList.add('highlighted');
    }
  },
  
  showNodeInfo(nodeId) {
    const node = this.nodes.find(n => n.id === nodeId);
    if (!node) return;
    
    const edges = this.edges.filter(e => e.source === nodeId || e.target === nodeId);
    
    alert(`${node.name}\n\n类型: ${node.type}\n访问次数: ${node.access_count || 0}\n关联数: ${edges.length}`);
  }
};

document.addEventListener('DOMContentLoaded', () => GraphViz.init());
window.GraphViz = GraphViz;
