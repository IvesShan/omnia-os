/**
 * Omnia 神经图谱可视化 - D3.js 力导向图
 */

// 全局变量
let svg, g, simulation, zoom;
let nodes = [], links = [];
let nodeElements, linkElements, labelElements;

// 节点类型颜色
const typeColors = {
    'PERSON': '#06b6d4',      // 青色
    'PROJECT': '#8b5cf6',     // 紫色
    'FILE': '#10b981',        // 绿色
    'CONCEPT': '#f59e0b',     // 橙色
    'EVENT': '#ef4444',       // 红色
    'default': '#6366f1'      // 默认靛蓝
};

// 初始化图谱
async function initGraph() {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // 清空容器
    container.innerHTML = '';
    
    // 创建 SVG
    svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height]);
    
    // 添加发光滤镜
    const defs = svg.append('defs');
    const filter = defs.append('filter')
        .attr('id', 'glow')
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');
    
    filter.append('feGaussianBlur')
        .attr('stdDeviation', '3')
        .attr('result', 'coloredBlur');
    
    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');
    
    // 创建主容器（用于缩放和平移）
    g = svg.append('g');
    
    // 设置缩放行为
    zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // 加载数据
    await loadGraphData();
    
    // 启动呼吸动画
    startBreathingAnimation();
}

// 加载图谱数据
async function loadGraphData() {
    try {
        // 获取图谱数据
        const response = await fetch('/api/graph');
        const data = await response.json();
        
        if (!data || !data.nodes || data.nodes.length === 0) {
            showEmptyGraph();
            return;
        }
        
        // 转换节点数据格式
        nodes = data.nodes.map(n => ({
            id: n.name || n.id,
            label: n.name || n.canonical_name || n.id,
            type: n.type || 'default',
            size: Math.max(8, Math.min(25, (n.access_count || 0) * 2 + 8))
        }));
        
        // 转换边数据格式
        links = (data.edges || []).map(e => ({
            source: e.source,
            target: e.target,
            relation: e.relation,
            weight: e.weight || 1
        }));
        
        createSimulation();
        renderGraph();
    } catch (error) {
        console.error('加载图谱数据失败:', error);
        showEmptyGraph();
    }
}

// 创建力导向模拟
function createSimulation() {
    const container = document.getElementById('graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => d.size + 10));
    
    simulation.on('tick', ticked);
}

// 渲染图谱
function renderGraph() {
    // 绘制连线
    linkElements = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('stroke', 'rgba(99, 102, 241, 0.3)')
        .attr('stroke-width', d => Math.max(1, d.weight * 2));
    
    // 绘制节点组
    nodeElements = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node-group')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded))
        .on('mouseover', highlightConnected)
        .on('mouseout', unhighlight);
    
    // 绘制节点圆形
    nodeElements.append('circle')
        .attr('r', d => d.size || 10)
        .attr('fill', d => typeColors[d.type] || typeColors.default)
        .attr('filter', 'url(#glow)')
        .attr('opacity', 0.9);
    
    // 绘制标签
    labelElements = nodeElements.append('text')
        .text(d => d.label || d.id)
        .attr('text-anchor', 'middle')
        .attr('dy', d => (d.size || 10) + 14)
        .attr('font-size', '10px')
        .attr('fill', '#374151')
        .attr('pointer-events', 'none');
}

// 更新位置
function ticked() {
    linkElements
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
    
    nodeElements
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
}

// 拖拽事件
function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// 高亮连接的节点
function highlightConnected(event, d) {
    const connectedIds = new Set();
    links.forEach(link => {
        if (link.source.id === d.id) connectedIds.add(link.target.id);
        if (link.target.id === d.id) connectedIds.add(link.source.id);
    });
    
    nodeElements.selectAll('circle')
        .attr('opacity', n => (n.id === d.id || connectedIds.has(n.id)) ? 1 : 0.3);
    
    linkElements
        .attr('stroke', l => (l.source.id === d.id || l.target.id === d.id) 
            ? 'rgba(99, 102, 241, 0.8)' 
            : 'rgba(99, 102, 241, 0.1)')
        .attr('stroke-width', l => (l.source.id === d.id || l.target.id === d.id) ? 2 : 1);
}

// 取消高亮
function unhighlight() {
    nodeElements.selectAll('circle').attr('opacity', 0.9);
    linkElements
        .attr('stroke', 'rgba(99, 102, 241, 0.3)')
        .attr('stroke-width', d => Math.max(1, d.weight * 2));
}

// 呼吸动画
function startBreathingAnimation() {
    function breathe() {
        nodeElements.selectAll('circle')
            .transition()
            .duration(2000)
            .attr('opacity', 0.7)
            .transition()
            .duration(2000)
            .attr('opacity', 0.9)
            .on('end', breathe);
    }
    breathe();
}

// 显示空图谱
function showEmptyGraph() {
    const container = document.getElementById('graph-container');
    container.innerHTML = '<p class="text-gray-500 text-center">暂无图谱数据</p>';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否有 D3.js
    if (typeof d3 === 'undefined') {
        // 动态加载 D3.js
        const script = document.createElement('script');
        script.src = 'https://d3js.org/d3.v7.min.js';
        script.onload = () => {
            initGraph();
        };
        document.head.appendChild(script);
    } else {
        initGraph();
    }
});
