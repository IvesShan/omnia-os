import { useMemo, useRef, useState, useEffect, useCallback } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import ForceGraph3D from '3d-force-graph'

/**
 * Omnia 神经图谱 3D (重构版)
 * 
 * 基于 3d-force-graph 库，支持 10万+ 节点的高性能渲染
 * 
 * 特性：
 * - 真实的 3D 力导向布局
 * - 高性能 WebGL 渲染（自动 LOD、视口裁剪）
 * - 节点悬停/点击交互
 * - 自动旋转
 * - 连线粒子流动动画
 */
export function NeuralGraph3D() {
    const containerRef = useRef()
    const graphRef = useRef()
    const [hoveredNode, setHoveredNode] = useState(null)
    const [selectedNode, setSelectedNode] = useState(null)
    const [graphData, setGraphData] = useState({ nodes: [], links: [] })

    // 从 Memory Palace API 加载数据
    useEffect(() => {
        fetchGraphData()
    }, [])

    const fetchGraphData = async () => {
        try {
            const response = await fetch('/api/memory/graph')
            const data = await response.json()
            setGraphData(data)
        } catch (error) {
            console.log('Using demo data for neural graph...')
            // 使用 Omnia Memory Palace 演示数据
            setGraphData({
                nodes: [
                    { id: 'omnia', label: 'Omnia', type: 'core', val: 2 },
                    { id: 'memory', label: 'Memory Palace', type: 'module', val: 1.5 },
                    { id: 'gateway', label: 'Gateway', type: 'module', val: 1.5 },
                    { id: 'persona', label: 'Persona', type: 'module', val: 1.5 },
                    { id: 'infinite', label: '无限', type: 'persona', val: 1.8 },
                    { id: 'user', label: '原点', type: 'user', val: 1.8 },
                    { id: 'neo4j', label: 'Neo4j', type: 'database', val: 1.2 },
                    { id: 'qdrant', label: 'Qdrant', type: 'database', val: 1.2 },
                    { id: 'miaoxiujiang', label: '喵修匠', type: 'project', val: 1.6 },
                    { id: 'dongjidi', label: '懂机帝', type: 'project', val: 1.6 },
                    { id: 'dji', label: 'DJI 维修', type: 'skill', val: 1.4 },
                    { id: 'drone', label: '无人机', type: 'knowledge', val: 1.3 },
                ],
                links: [
                    { source: 'omnia', target: 'memory' },
                    { source: 'omnia', target: 'gateway' },
                    { source: 'omnia', target: 'persona' },
                    { source: 'persona', target: 'infinite' },
                    { source: 'memory', target: 'neo4j' },
                    { source: 'memory', target: 'qdrant' },
                    { source: 'infinite', target: 'user' },
                    { source: 'user', target: 'miaoxiujiang' },
                    { source: 'user', target: 'dongjidi' },
                    { source: 'miaoxiujiang', target: 'dji' },
                    { source: 'dji', target: 'drone' },
                    { source: 'dongjidi', target: 'drone' },
                ]
            })
        }
    }

    // 根据节点类型返回颜色
    const getNodeColor = useCallback((type) => {
        const colors = {
            core: '#ff8a00',      // 品牌橙
            module: '#00ffff',    // 青色
            persona: '#ff00ff',   // 紫色
            user: '#00ff00',      // 绿色
            database: '#ffc266',  // 浅橙
            project: '#ff6600',   // 橙红
            skill: '#ffcc00',     // 金色
            knowledge: '#66ccff'  // 浅蓝
        }
        return colors[type] || '#ffffff'
    }, [])

    // 初始化 3d-force-graph
    useEffect(() => {
        if (!containerRef.current || !graphData.nodes.length) return

        // 清理旧实例
        if (graphRef.current) {
            graphRef.current = null
        }

        const container = containerRef.current

        // 创建 3d-force-graph 实例
        const Graph = ForceGraph3D({ controlType: 'orbit' })(container)
            .graphData(graphData)
            .nodeLabel('label')
            .nodeColor(node => getNodeColor(node.type))
            .nodeRelSize(8)
            .nodeVal(node => node.val * 2)
            .linkColor(() => '#ffffff')
            .linkWidth(1)
            .linkOpacity(0.6)
            .linkDirectionalParticles(2)
            .linkDirectionalParticleWidth(2)
            .linkDirectionalParticleColor(() => '#ff8a00')
            .linkDirectionalParticleSpeed(0.005)
            .backgroundColor('#00000000')
            .width(container.clientWidth)
            .height(container.clientHeight)
            .onNodeHover(node => {
                setHoveredNode(node?.id || null)
                container.style.cursor = node ? 'pointer' : 'auto'
            })
            .onNodeClick(node => {
                setSelectedNode(prev => prev === node.id ? null : node.id)
                // 聚焦到节点
                Graph.cameraPosition(
                    { x: node.x + 50, y: node.y + 50, z: node.z + 50 },
                    node,
                    2000
                )
            })

        // 设置力导向参数
        Graph.d3Force('charge').strength(-200)
        Graph.d3Force('link').distance(100)

        // 自动旋转
        let angle = 0
        const rotationInterval = setInterval(() => {
            if (!Graph.cameraPosition) return
            const distance = 300
            angle += 0.3
            Graph.cameraPosition({
                x: distance * Math.sin(angle * Math.PI / 180),
                y: distance * Math.cos(angle * Math.PI / 180) * 0.5,
                z: distance * Math.cos(angle * Math.PI / 180)
            })
        }, 50)

        graphRef.current = Graph

        // 响应窗口大小变化
        const handleResize = () => {
            if (Graph && container) {
                Graph.width(container.clientWidth)
                    .height(container.clientHeight)
            }
        }
        window.addEventListener('resize', handleResize)

        return () => {
            clearInterval(rotationInterval)
            window.removeEventListener('resize', handleResize)
            if (graphRef.current) {
                graphRef.current = null
            }
        }
    }, [graphData, getNodeColor])

    return (
        <div 
            ref={containerRef} 
            style={{ 
                width: '100%', 
                height: '100%',
                position: 'absolute',
                top: 0,
                left: 0
            }} 
        />
    )
}

export default NeuralGraph3D
