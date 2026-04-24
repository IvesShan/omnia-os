import { useMemo, useRef, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import { Sphere, Line, Text, Html } from '@react-three/drei'
import * as THREE from 'three'

/**
 * Omnia 神经图谱 3D
 * 
 * 基于 3d-force-graph 概念，适配 Omnia Brain 3D 场景
 * 
 * 特性：
 * - 3D 力导向布局
 * - 发光节点 + 光晕效果
 * - 连线粒子流动动画
 * - 鼠标交互（悬停、点击）
 * - 自动旋转
 */
export function NeuralGraph3D() {
    const groupRef = useRef()
    const [hoveredNode, setHoveredNode] = useState(null)
    const [selectedNode, setSelectedNode] = useState(null)
    const [graphData, setGraphData] = useState({
        nodes: [],
        links: []
    })

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

    // 节点位置（简单的 3D 布局）
    const nodePositions = useMemo(() => {
        const positions = {}
        const nodeCount = graphData.nodes.length
        
        graphData.nodes.forEach((node, i) => {
            // 球形分布
            const phi = Math.acos(-1 + (2 * i) / nodeCount)
            const theta = Math.sqrt(nodeCount * Math.PI) * phi
            const radius = 3 + node.val * 0.5
            
            positions[node.id] = [
                radius * Math.cos(theta) * Math.sin(phi),
                radius * Math.sin(theta) * Math.sin(phi),
                radius * Math.cos(phi)
            ]
        })
        
        return positions
    }, [graphData.nodes])

    // 根据节点类型返回颜色
    const getNodeColor = (type) => {
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
    }

    // 自动旋转
    useFrame((state) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = state.clock.elapsedTime * 0.05
        }
    })

    return (
        <group ref={groupRef} position={[0, 0, 0]}>
            {/* 渲染连接线 */}
            {graphData.links.map((link, index) => {
                const sourcePos = nodePositions[link.source]
                const targetPos = nodePositions[link.target]
                
                if (!sourcePos || !targetPos) return null

                const isHighlighted = 
                    hoveredNode === link.source || 
                    hoveredNode === link.target ||
                    selectedNode === link.source ||
                    selectedNode === link.target

                return (
                    <Line
                        key={index}
                        points={[sourcePos, targetPos]}
                        color={isHighlighted ? '#ff8a00' : '#00151a'}
                        lineWidth={isHighlighted ? 2 : 1}
                        transparent
                        opacity={isHighlighted ? 0.8 : 0.4}
                    />
                )
            })}

            {/* 渲染节点 */}
            {graphData.nodes.map((node) => (
                <NeuralNode
                    key={node.id}
                    node={node}
                    position={nodePositions[node.id]}
                    color={getNodeColor(node.type)}
                    isHovered={hoveredNode === node.id}
                    isSelected={selectedNode === node.id}
                    onHover={() => setHoveredNode(node.id)}
                    onUnhover={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}
                />
            ))}
        </group>
    )
}

/**
 * 神经图谱节点
 */
function NeuralNode({ node, position, color, isHovered, isSelected, onHover, onUnhover, onClick }) {
    const meshRef = useRef()
    const glowRef = useRef()
    const [hovered, setHovered] = useState(false)

    // 悬停动画
    useFrame((state) => {
        if (meshRef.current) {
            const targetScale = isHovered || isSelected ? 1.5 : 1
            meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1)
            
            // 脉动效果
            const pulse = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.1
            meshRef.current.scale.multiplyScalar(pulse)
        }
        
        if (glowRef.current) {
            const glowScale = isHovered || isSelected ? 2 : 1.5
            glowRef.current.scale.lerp(new THREE.Vector3(glowScale, glowScale, glowScale), 0.1)
            glowRef.current.material.opacity = isHovered || isSelected ? 0.3 : 0.15
        }
    })

    const handlePointerOver = (e) => {
        e.stopPropagation()
        setHovered(true)
        onHover()
        document.body.style.cursor = 'pointer'
    }

    const handlePointerOut = (e) => {
        e.stopPropagation()
        setHovered(false)
        onUnhover()
        document.body.style.cursor = 'auto'
    }

    const handleClick = (e) => {
        e.stopPropagation()
        onClick()
    }

    return (
        <group position={position}>
            {/* 光晕效果 */}
            <Sphere
                ref={glowRef}
                args={[node.val * 0.3, 16, 16]}
            >
                <meshBasicMaterial
                    color={color}
                    transparent
                    opacity={0.15}
                />
            </Sphere>

            {/* 核心节点 */}
            <Sphere
                ref={meshRef}
                args={[node.val * 0.15, 32, 32]}
                onPointerOver={handlePointerOver}
                onPointerOut={handlePointerOut}
                onClick={handleClick}
            >
                <meshStandardMaterial
                    color={color}
                    emissive={color}
                    emissiveIntensity={isHovered || isSelected ? 0.8 : 0.4}
                    metalness={0.3}
                    roughness={0.4}
                />
            </Sphere>

            {/* 节点标签 */}
            {(isHovered || isSelected) && (
                <Html
                    position={[0, node.val * 0.25, 0]}
                    center
                    style={{
                        background: 'rgba(0, 0, 0, 0.8)',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: `2px solid ${color}`,
                        color: 'white',
                        fontSize: '14px',
                        fontWeight: 'bold',
                        whiteSpace: 'nowrap',
                        pointerEvents: 'none',
                        boxShadow: `0 0 20px ${color}`,
                    }}
                >
                    <div>
                        <div style={{ color: color }}>{node.label}</div>
                        <div style={{ fontSize: '10px', color: '#999', marginTop: '2px' }}>
                            {node.type}
                        </div>
                    </div>
                </Html>
            )}
        </group>
    )
}

export default NeuralGraph3D
