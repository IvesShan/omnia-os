import { useMemo, useRef, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { Sphere, Line, Text, Html } from '@react-three/drei'
import * as THREE from 'three'

/**
 * 知识图谱节点可视化
 * 结合 VowVector 的 Neo4j + Qdrant 架构
 * 
 * 特性：
 * - 节点表示知识实体
 * - 连线表示关系
 * - 悬浮高亮 + 信息展示
 */
export function KnowledgeGraph({ nodes = [], connections = [] }) {
    const [hoveredNode, setHoveredNode] = useState(null)
    const [data, setData] = useState({
        nodes: [],
        connections: []
    })

    // 从后端 API 加载知识图谱数据
    useEffect(() => {
        fetchKnowledgeGraph()
    }, [])

    const fetchKnowledgeGraph = async () => {
        try {
            const response = await fetch('/api/knowledge-graph')
            const result = await response.json()
            setData(result)
        } catch (error) {
            console.log('Using demo data...')
            // 使用演示数据
            setData({
                nodes: [
                    { id: '1', label: 'Omnia', position: [0, 0, 0], type: 'core' },
                    { id: '2', label: 'Memory Palace', position: [2, 1, 0], type: 'module' },
                    { id: '3', label: 'Gateway', position: [-2, 1, 0], type: 'module' },
                    { id: '4', label: 'Persona', position: [0, 2, 1], type: 'module' },
                    { id: '5', label: 'Neo4j', position: [3, -1, 0], type: 'database' },
                    { id: '6', label: 'Qdrant', position: [-3, -1, 0], type: 'database' },
                    { id: '7', label: '无限', position: [0, -2, -1], type: 'persona' },
                ],
                connections: [
                    { from: '1', to: '2' },
                    { from: '1', to: '3' },
                    { from: '1', to: '4' },
                    { from: '2', to: '5' },
                    { from: '2', to: '6' },
                    { from: '4', to: '7' },
                ]
            })
        }
    }

    // 根据节点类型返回颜色
    const getNodeColor = (type) => {
        switch (type) {
            case 'core': return '#ff8a00'      // 品牌橙
            case 'module': return '#00ffff'    // 青色
            case 'database': return '#ffc266'  // 浅橙
            case 'persona': return '#ff00ff'   // 紫色
            default: return '#ffffff'
        }
    }

    return (
        <group>
            {/* 渲染连接线 */}
            {data.connections.map((conn, index) => {
                const fromNode = data.nodes.find(n => n.id === conn.from)
                const toNode = data.nodes.find(n => n.id === conn.to)
                
                if (!fromNode || !toNode) return null

                return (
                    <Line
                        key={index}
                        points={[fromNode.position, toNode.position]}
                        color={hoveredNode === conn.from || hoveredNode === conn.to ? '#ff8a00' : '#00151a'}
                        lineWidth={hoveredNode === conn.from || hoveredNode === conn.to ? 2 : 1}
                        transparent
                        opacity={0.6}
                    />
                )
            })}

            {/* 渲染节点 */}
            {data.nodes.map((node) => (
                <KnowledgeNode
                    key={node.id}
                    node={node}
                    color={getNodeColor(node.type)}
                    isHovered={hoveredNode === node.id}
                    onHover={() => setHoveredNode(node.id)}
                    onUnhover={() => setHoveredNode(null)}
                />
            ))}
        </group>
    )
}

function KnowledgeNode({ node, color, isHovered, onHover, onUnhover }) {
    const ref = useRef()
    const scale = isHovered ? 1.5 : 1

    useFrame((state) => {
        // 悬浮动画
        if (ref.current) {
            ref.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1)
            // 轻微浮动
            ref.current.position.y = node.position[1] + Math.sin(state.clock.elapsedTime + node.id) * 0.05
        }
    })

    return (
        <group
            ref={ref}
            position={node.position}
            onPointerOver={onHover}
            onPointerOut={onUnhover}
        >
            {/* 节点球体 */}
            <Sphere args={[0.15, 16, 16]}>
                <meshStandardMaterial
                    color={color}
                    emissive={color}
                    emissiveIntensity={isHovered ? 0.8 : 0.3}
                    transparent
                    opacity={0.9}
                />
            </Sphere>

            {/* 节点标签 */}
            {isHovered && (
                <Html center position={[0, 0.4, 0]}>
                    <div className="glass-panel px-3 py-2 text-sm">
                        <div className="font-bold text-brand-orange">{node.label}</div>
                        <div className="text-xs text-gray-400">{node.type}</div>
                    </div>
                </Html>
            )}

            {/* 节点文字 */}
            <Text
                position={[0, -0.25, 0]}
                fontSize={0.1}
                color={isHovered ? '#ffffff' : '#888888'}
                anchorX="center"
                anchorY="top"
            >
                {node.label}
            </Text>
        </group>
    )
}
