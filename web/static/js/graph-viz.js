/**
 * Omnia 神经图谱可视化 - vis-network
 */

let network = null;
let nodes = null;
let edges = null;

// 节点类型颜色
const typeColors = {
    'PERSON': { background: '#06b6d4', border: '#0891b2', highlight: '#22d3ee' },
    'PROJECT': { background: '#8b5cf6', border: '#7c3aed', highlight: '#a78bfa' },
    'FILE': { background: '#10b981', border: '#059669', highlight: '#34d399' },
    'CONCEPT': { background: '#f59e0b', border: '#d97706', highlight: '#fbbf24' },
    'EVENT': { background: '#ef4444', border: '#dc2626', highlight: '#f87171' },
    'default': { background: '#6366f1', border: '#4f46e5', highlight: '#818cf8' }
};

// 节点类型图标
const typeIcons = {
    'PERSON': '👤',
    'PROJECT': '📁',
    'FILE': '📄',
    'CONCEPT': '💡',
    'EVENT': '⚡',
    'default': '🔵'
};

// 初始化图谱
async function initGraph() {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    console.log('[GraphViz] vis-network 初始化...');
    
    try {
        // 加载数据
        const response = await fetch('/api/graph');
        const data = await response.json();
        
        if (!data || !data.nodes || data.nodes.length === 0) {
            showEmptyGraph();
            return;
        }
        
        console.log(`[GraphViz] 获取到节点: ${data.nodes.length} 边: ${data.edges?.length || 0}`);
        
        // 创建节点数据集
        const nodeArray = data.nodes.map(n => {
            const type = n.type || 'default';
            const colors = typeColors[type] || typeColors.default;
            const accessCount = n.access_count || 0;
            const size = Math.max(20, Math.min(40, 20 + accessCount * 2));
            
            return {
                id: n.name || n.id,
                label: n.name || n.canonical_name || n.id,
                type: type,
                value: accessCount,
                size: size,
                color: colors,
                font: {
                    color: '#e2e8f0',
                    size: 14,
                    face: 'Inter, sans-serif',
                    strokeWidth: 2,
                    strokeColor: '#0f172a'
                },
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    color: 'rgba(99, 102, 241, 0.4)',
                    size: 15,
                    x: 0,
                    y: 0
                },
                shape: 'dot',
                mass: 1 + accessCount * 0.1,
                title: `<b>${n.name || n.id}</b><br>类型: ${type}<br>访问: ${accessCount}次`
            };
        });
        
        // 创建边数据集
        const edgeArray = (data.edges || []).map((e, i) => {
            return {
                id: i,
                from: e.source,
                to: e.target,
                label: e.relation || '',
                color: {
                    color: 'rgba(99, 102, 241, 0.3)',
                    highlight: '#6366f1',
                    hover: '#818cf8'
                },
                width: 1.5,
                smooth: {
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.5
                },
                font: {
                    color: '#94a3b8',
                    size: 11,
                    face: 'Inter, sans-serif',
                    strokeWidth: 2,
                    strokeColor: '#0f172a',
                    align: 'middle'
                },
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: 0.5,
                        type: 'arrow'
                    }
                },
                dashes: false
            };
        });
        
        nodes = new vis.DataSet(nodeArray);
        edges = new vis.DataSet(edgeArray);
        
        // 网络配置
        const options = {
            nodes: {
                borderWidth: 2,
                borderWidthSelected: 3,
                shape: 'dot',
                size: 25,
                font: {
                    color: '#e2e8f0',
                    size: 14,
                    face: 'Inter, sans-serif',
                    strokeWidth: 2,
                    strokeColor: '#0f172a'
                },
                shadow: {
                    enabled: true,
                    color: 'rgba(99, 102, 241, 0.4)',
                    size: 15
                }
            },
            edges: {
                width: 1.5,
                selectionWidth: 2,
                hoverWidth: 2,
                smooth: {
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.5
                },
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: 0.5
                    }
                },
                color: {
                    color: 'rgba(99, 102, 241, 0.3)',
                    highlight: '#6366f1',
                    hover: '#818cf8'
                },
                font: {
                    color: '#94a3b8',
                    size: 11,
                    strokeWidth: 2,
                    strokeColor: '#0f172a'
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.05,
                    damping: 0.09,
                    avoidOverlap: 0.5
                },
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true,
                dragNodes: true,
                navigationButtons: true,
                keyboard: {
                    enabled: true,
                    speed: { x: 10, y: 10, zoom: 0.02 }
                }
            },
            layout: {
                improvedLayout: true,
                clusterThreshold: 150
            }
        };
        
        // 创建网络
        network = new vis.Network(container, { nodes, edges }, options);
        
        // 事件监听
        network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                console.log('[GraphViz] 点击节点:', nodeId);
                // 可以触发详情面板
            }
        });
        
        network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                console.log('[GraphViz] 双击节点:', nodeId);
                // 可以触发搜索或展开
            }
        });
        
        network.on('stabilizationProgress', (params) => {
            const progress = Math.round((params.iterations / params.total) * 100);
            console.log(`[GraphViz] 布局进度: ${progress}%`);
        });
        
        network.on('stabilizationIterationsDone', () => {
            console.log('[GraphViz] 布局完成');
            // 自动适配视图
            network.fit({
                animation: {
                    duration: 500,
                    easingFunction: 'easeInOutQuad'
                }
            });
        });
        
        console.log('[GraphViz] vis-network 初始化完成');
        
    } catch (error) {
        console.error('[GraphViz] 加载失败:', error);
        showEmptyGraph();
    }
}

// 显示空图谱
function showEmptyGraph() {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    container.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #64748b;">
            <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">🕸️</div>
            <div style="font-size: 18px; font-weight: 500;">神经图谱为空</div>
            <div style="font-size: 14px; margin-top: 8px; opacity: 0.7;">开始与 Omnia 对话，构建记忆网络</div>
        </div>
    `;
}

// 刷新图谱
async function refreshGraph() {
    if (network) {
        network.destroy();
        network = null;
    }
    await initGraph();
}

// 适配视图
function fitGraph() {
    if (network) {
        network.fit({
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });
    }
}

// 搜索节点
function focusNode(nodeId) {
    if (network && nodes) {
        const node = nodes.get(nodeId);
        if (node) {
            network.focus(nodeId, {
                scale: 1.5,
                animation: {
                    duration: 500,
                    easingFunction: 'easeInOutQuad'
                }
            });
            network.selectNodes([nodeId]);
        }
    }
}

// 导出为图片
function exportAsImage() {
    if (network) {
        // vis-network 不直接支持导出，可以用 html2canvas
        console.log('[GraphViz] 导出功能待实现');
    }
}

// 页面加载后初始化
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initGraph, 500);
});
