"""
Omnia Neural Graph API - 神经图谱 API

提供记忆神经图谱的可视化数据
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import sqlite3
from typing import List, Dict, Any
import json

app = FastAPI(title="Omnia Neural Graph API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/home/shan/.omnia/memory_palace.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/memory/neural-graph")
async def get_neural_graph():
    """
    获取神经图谱数据
    
    Returns:
        {
            "nodes": [{ "id": "...", "label": "...", "type": "..." }],
            "links": [{ "source": "...", "target": "...", "type": "..." }]
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取节点 - 使用正确的列名
        cursor.execute("""
            SELECT id, entity_type, entity_name, canonical_name 
            FROM neural_nodes
            LIMIT 500
        """)
        nodes_rows = cursor.fetchall()
        
        # 获取边
        cursor.execute("""
            SELECT source_id, target_id, relation_type, weight,
                   source_name, target_name
            FROM neural_edges
            LIMIT 2000
        """)
        edges_rows = cursor.fetchall()
        
        conn.close()
        
        # 转换为前端格式
        nodes = []
        for row in nodes_rows:
            nodes.append({
                "id": row["id"],
                "label": row["entity_name"] or row["canonical_name"] or row["id"],
                "type": row["entity_type"] or "DEFAULT"
            })
        
        links = []
        for row in edges_rows:
            links.append({
                "source": row["source_id"],
                "target": row["target_id"],
                "type": row["relation_type"] or "related_to",
                "weight": row["weight"] or 1.0,
                "source_name": row["source_name"],
                "target_name": row["target_name"]
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(links)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/stats")
async def get_memory_stats():
    """获取记忆统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取各层级统计
        stats = {}
        
        for table in ["facts", "relations", "habits", "timeline"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        
        # 获取神经图谱统计
        cursor.execute("SELECT COUNT(*) FROM neural_nodes")
        stats["neural_nodes"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM neural_edges")
        stats["neural_edges"] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/search")
async def search_memory(query: str, limit: int = 10):
    """搜索记忆"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 在 facts 表中搜索
        cursor.execute("""
            SELECT key, value, category, created_at
            FROM facts
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "key": row["key"],
                "value": row["value"],
                "category": row["category"],
                "created_at": row["created_at"]
            })
        
        conn.close()
        
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ 内嵌前端页面 ============

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """返回神经图谱可视化页面"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omnia 神经图谱</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            overflow: hidden;
        }
        #container {
            width: 100vw;
            height: 100vh;
            position: relative;
        }
        #stats {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(20, 20, 20, 0.9);
            padding: 15px 20px;
            border-radius: 12px;
            border: 1px solid #333;
            z-index: 100;
        }
        #stats h2 {
            font-size: 18px;
            margin-bottom: 10px;
            color: #00ff88;
        }
        #stats p {
            font-size: 13px;
            color: #888;
            margin: 5px 0;
        }
        #loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 20px;
            color: #00ff88;
        }
        #tooltip {
            position: absolute;
            background: rgba(20, 20, 20, 0.95);
            border: 1px solid #00ff88;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 200;
            max-width: 300px;
        }
        #tooltip.visible { opacity: 1; }
        #tooltip .label { color: #00ff88; font-weight: bold; margin-bottom: 5px; }
        #tooltip .type { color: #888; font-size: 11px; }
        
        svg { width: 100%; height: 100%; }
        .node { cursor: pointer; }
        .node circle {
            stroke: #333;
            stroke-width: 1.5px;
            transition: all 0.3s;
        }
        .node:hover circle {
            stroke: #00ff88;
            stroke-width: 3px;
            filter: drop-shadow(0 0 8px rgba(0, 255, 136, 0.5));
        }
        .node text {
            font-size: 10px;
            fill: #aaa;
            pointer-events: none;
        }
        .link {
            stroke-opacity: 0.3;
            transition: stroke-opacity 0.3s;
        }
        .link:hover { stroke-opacity: 0.8; }
        
        /* 节点类型颜色 */
        .node-PERSON circle { fill: #ff6b6b; }
        .node-ORG circle { fill: #4ecdc4; }
        .node-LOCATION circle { fill: #ffe66d; }
        .node-CONCEPT circle { fill: #a855f7; }
        .node-EVENT circle { fill: #f97316; }
        .node-PROJECT circle { fill: #3b82f6; }
        .node-SKILL circle { fill: #10b981; }
        .node-DEFAULT circle { fill: #6366f1; }
    </style>
</head>
<body>
    <div id="container">
        <div id="stats">
            <h2>🧠 神经图谱</h2>
            <p>节点: <span id="node-count">-</span></p>
            <p>连接: <span id="edge-count">-</span></p>
            <p>加载中...</p>
        </div>
        <div id="loading">⏳ 正在加载图谱数据...</div>
        <div id="tooltip">
            <div class="label"></div>
            <div class="type"></div>
        </div>
    </div>
    
    <script>
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        // 创建 SVG
        const svg = d3.select('#container')
            .append('svg')
            .attr('viewBox', [0, 0, width, height]);
        
        // 创建容器组
        const g = svg.append('g');
        
        // 添加缩放功能
        svg.call(d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            }));
        
        // 提示框
        const tooltip = d3.select('#tooltip');
        
        // 加载数据
        d3.json('/api/memory/neural-graph').then(data => {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('node-count').textContent = data.stats.total_nodes;
            document.getElementById('edge-count').textContent = data.stats.total_edges;
            
            const nodes = data.nodes;
            const links = data.links;
            
            // 创建力模拟
            const simulation = d3.forceSimulation(nodes)
                .force('link', d3.forceLink(links).id(d => d.id).distance(80))
                .force('charge', d3.forceManyBody().strength(-200))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(25));
            
            // 绘制连线
            const link = g.append('g')
                .selectAll('line')
                .data(links)
                .join('line')
                .attr('class', 'link')
                .attr('stroke', '#333')
                .attr('stroke-width', d => Math.sqrt(d.weight) * 0.5);
            
            // 绘制节点
            const node = g.append('g')
                .selectAll('g')
                .data(nodes)
                .join('g')
                .attr('class', d => `node node-${d.type}`)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            // 节点圆形
            node.append('circle')
                .attr('r', 6); // 统一大小
            // 节点标签
            node.append('text')
                .text(d => d.label.length > 12 ? d.label.slice(0, 12) + '...' : d.label)
                .attr('x', 0)
                .attr('y', 25)
                .attr('text-anchor', 'middle');
            
            // 鼠标交互
            node.on('mouseover', function(event, d) {
                tooltip.select('.label').text(d.label);
                tooltip.select('.type').text(`类型: ${d.type} | ID: ${d.id.slice(0, 8)}...`);
                tooltip.classed('visible', true);
            })
            .on('mousemove', function(event) {
                tooltip
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseout', function() {
                tooltip.classed('visible', false);
            });
            
            // 更新位置
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });
            
        }).catch(err => {
            document.getElementById('loading').innerHTML = '❌ 加载失败: ' + err.message;
            console.error(err);
        });
        
        // 拖拽函数
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    </script>
</body>
</html>"""
