// 神经图谱可视化 - 真正的神经网络效果
const GraphViz = {
  graph: null,
  animationFrame: null,
  pulsePhase: 0,
  
  init() {
    console.log('[GraphViz] 初始化');
    this.loadStats();
    this.loadGraph();
  },
  
  async loadStats() {
    try {
      const res = await fetch('/api/graph/stats');
      const stats = await res.json();
      
      const nodesEl = document.getElementById('gs-nodes');
      const edgesEl = document.getElementById('gs-edges');
      
      if (nodesEl) nodesEl.textContent = stats.nodes || 0;
      if (edgesEl) edgesEl.textContent = stats.edges || 0;
      
      this.updateLegend(stats.nodes_by_type || {});
    } catch (err) {
      console.error('[GraphViz] 加载统计失败:', err);
    }
  },
  
  updateLegend(byType) {
    const legendItems = {
      'PERSON': byType.PERSON || 0,
      'PROJECT': byType.PROJECT || 0,
      'FILE': byType.FILE || 0,
      'CONCEPT': byType.CONCEPT || 0,
      'DATE': byType.DATE || 0,
      'ENTITY': byType.ENTITY || 0
    };
    
    Object.entries(legendItems).forEach(([type, count]) => {
      const el = document.querySelector(`.legend-item .legend-dot.${type.toLowerCase()}`);
      if (el) {
        const parent = el.closest('.legend-item');
        if (parent && count > 0) {
          const text = parent.textContent.trim();
          if (!text.includes('(')) {
            parent.childNodes[parent.childNodes.length - 1].textContent += ` (${count})`;
          }
        }
      }
    });
  },
  
  async loadGraph() {
    const canvas = document.getElementById('graph-canvas');
    if (!canvas) return;
    
    canvas.innerHTML = '<div class="graph-loading"><div class="loading-spinner"></div>正在唤醒记忆...</div>';
    
    try {
      // 加载 D3.js 和 force-graph
      if (typeof d3 === 'undefined') {
        await this.loadScript('https://d3js.org/d3.v7.min.js');
      }
      
      const res = await fetch('/api/graph?limit=200');
      const data = await res.json();
      
      if (!data.nodes || data.nodes.length === 0) {
        canvas.innerHTML = '<div class="graph-placeholder">暂无图谱数据</div>';
        return;
      }
      
      // 创建名称到节点的映射
      const nameToNode = {};
      data.nodes.forEach(n => {
        nameToNode[n.name] = n;
        if (n.canonical_name) nameToNode[n.canonical_name] = n;
      });
      
      // 转换数据
      const graphData = {
        nodes: data.nodes.map(n => ({
          id: n.id,
          name: n.name || n.label,
          type: n.type,
          access_count: n.access_count || 0,
          // 核心节点更大
          importance: this.calculateImportance(n)
        })),
        links: data.edges
          .filter(e => nameToNode[e.source] && nameToNode[e.target])
          .map(e => ({
            source: nameToNode[e.source].id,
            target: nameToNode[e.target].id,
            relation: e.relation
          }))
      };
      
      console.log('[GraphViz] 节点:', graphData.nodes.length, '连线:', graphData.links.length);
      
      // 清空画布
      canvas.innerHTML = '';
      
      // 创建 SVG
      const width = canvas.clientWidth || 400;
      const height = canvas.clientHeight || 300;
      
      const svg = d3.select(canvas)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'neural-svg');
      
      // 添加发光滤镜
      const defs = svg.append('defs');
      
      // 发光效果
      const glow = defs.append('filter')
        .attr('id', 'glow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');
      
      glow.append('feGaussianBlur')
        .attr('stdDeviation', '3')
        .attr('result', 'coloredBlur');
      
      const feMerge = glow.append('feMerge');
      feMerge.append('feMergeNode').attr('in', 'coloredBlur');
      feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
      
      // 创建力导向模拟
      const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(60))
        .force('charge', d3.forceManyBody().strength(-100))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => this.getNodeRadius(d) + 5));
      
      // 绘制连线
      const links = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(graphData.links)
        .enter()
        .append('line')
        .attr('class', 'neural-link')
        .attr('stroke', 'rgba(34, 211, 238, 0.2)')
        .attr('stroke-width', 1);
      
      // 绘制节点
      const nodes = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(graphData.nodes)
        .enter()
        .append('g')
        .attr('class', 'neural-node')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended));
      
      // 节点圆圈
      nodes.append('circle')
        .attr('r', d => this.getNodeRadius(d))
        .attr('fill', d => this.getNodeColor(d.type))
        .attr('fill-opacity', 0.3)
        .attr('stroke', d => this.getNodeColor(d.type))
        .attr('stroke-width', 2)
        .attr('filter', 'url(#glow)')
        .attr('class', 'node-circle');
      
      // 节点标签
      nodes.append('text')
        .text(d => this.truncateLabel(d.name))
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dy', d => this.getNodeRadius(d) + 12)
        .attr('fill', d => this.getNodeColor(d.type))
        .attr('font-size', '9px')
        .attr('font-weight', '600');
      
      // 节点交互
      nodes.on('mouseover', (event, d) => {
        this.highlightNode(d, nodes, links, true);
      }).on('mouseout', (event, d) => {
        this.highlightNode(d, nodes, links, false);
      });
      
      // 更新位置
      simulation.on('tick', () => {
        links
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);
        
        nodes.attr('transform', d => `translate(${d.x},${d.y})`);
      });
      
      // 呼吸动画
      this.startPulseAnimation(nodes);
      
      // 更新状态
      const statusEl = document.getElementById('neural-status');
      if (statusEl) {
        statusEl.textContent = `COGNITION ACTIVE · ${graphData.nodes.length} NODES`;
      }
      
      // 拖拽函数
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }
      
      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }
      
      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
      
    } catch (err) {
      console.error('[GraphViz] 加载失败:', err);
      canvas.innerHTML = `<div style="color: #ff453a; padding: 20px; text-align: center;">加载失败: ${err.message}</div>`;
    }
  },
  
  calculateImportance(node) {
    // 核心节点更重要
    const coreTypes = ['PERSON', 'PROJECT'];
    const isCore = coreTypes.includes(node.type);
    const accessBonus = Math.min(node.access_count || 0, 10);
    return isCore ? 2 + accessBonus * 0.1 : 1 + accessBonus * 0.05;
  },
  
  getNodeRadius(node) {
    const base = 8;
    return base * node.importance;
  },
  
  getNodeColor(type) {
    const colors = {
      'PROJECT': '#a855f7',
      'PERSON': '#22d3ee',
      'FILE': '#30d158',
      'CONCEPT': '#ff9f0a',
      'DATE': '#0a84ff',
      'LOCATION': '#ff453a',
      'ENTITY': '#8e8e93'
    };
    return colors[type] || '#8e8e93';
  },
  
  truncateLabel(name) {
    if (!name) return '';
    return name.length > 12 ? name.substring(0, 10) + '...' : name;
  },
  
  highlightNode(node, nodes, links, isHover) {
    if (isHover) {
      // 降低所有节点透明度
      nodes.selectAll('circle')
        .attr('fill-opacity', 0.1)
        .attr('stroke-opacity', 0.3);
      
      // 降低所有连线透明度
      links.attr('stroke-opacity', 0.1);
      
      // 高亮当前节点
      nodes.filter(d => d.id === node.id)
        .selectAll('circle')
        .attr('fill-opacity', 0.8)
        .attr('stroke-width', 3);
      
      // 高亮相关连线
      links.filter(d => d.source.id === node.id || d.target.id === node.id)
        .attr('stroke', '#22d3ee')
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 0.8);
      
      // 高亮连接的节点
      const connectedIds = new Set();
      links.each(d => {
        if (d.source.id === node.id) connectedIds.add(d.target.id);
        if (d.target.id === node.id) connectedIds.add(d.source.id);
      });
      
      nodes.filter(d => connectedIds.has(d.id))
        .selectAll('circle')
        .attr('fill-opacity', 0.6)
        .attr('stroke-opacity', 1);
      
    } else {
      // 恢复所有
      nodes.selectAll('circle')
        .attr('fill-opacity', 0.3)
        .attr('stroke-width', 2)
        .attr('stroke-opacity', 1);
      
      links
        .attr('stroke', 'rgba(34, 211, 238, 0.2)')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', 1);
    }
  },
  
  startPulseAnimation(nodes) {
    // 节点呼吸动画
    const animate = () => {
      this.pulsePhase += 0.02;
      const pulse = Math.sin(this.pulsePhase) * 0.1 + 0.3;
      
      nodes.selectAll('circle')
        .attr('fill-opacity', d => {
          const base = 0.3;
          const variation = Math.sin(this.pulsePhase + d.id * 0.1) * 0.1;
          return base + variation;
        });
      
      this.animationFrame = requestAnimationFrame(animate);
    };
    
    animate();
  },
  
  loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  },
  
  highlightNode(query) {
    // 搜索并高亮节点
    console.log('[GraphViz] 搜索节点:', query);
  },
  
  refresh() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    this.loadStats();
    this.loadGraph();
  }
};

// 初始化
(function() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => GraphViz.init());
  } else {
    GraphViz.init();
  }
})();

window.GraphViz = GraphViz;
