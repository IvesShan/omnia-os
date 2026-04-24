import { useMemo, useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Points, PointMaterial } from '@react-three/drei'
import * as THREE from 'three'

/**
 * 全息大脑粒子系统
 * 从 porweb 移植，适配 Omnia Brain 架构
 * 
 * 特性：
 * - 50,000+ 粒子渲染大脑形状
 * - 橙蓝配色（品牌橙 #ff8a00 + 青色 #00ffff）
 * - 鼠标跟随旋转 + 脉动效果
 */
export function Brain(props) {
    const ref = useRef()
    const { viewport, mouse } = useThree()

    // 生成球形粒子点（模拟大脑形状）
    const [positions, colors] = useMemo(() => {
        // 如果没有 GLTF 模型，使用球形粒子代替
        const pointsCount = 50000
        const positions = new Float32Array(pointsCount * 3)
        const colors = new Float32Array(pointsCount * 3)
        
        const color = new THREE.Color()

        for (let i = 0; i < pointsCount; i++) {
            // 生成球形分布的粒子
            const theta = Math.random() * Math.PI * 2
            const phi = Math.acos(2 * Math.random() - 1)
            const radius = 1.5 * Math.cbrt(Math.random()) // 使用立方根让粒子分布更均匀
            
            positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
            positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.8 // 稍微压扁，更像大脑
            positions[i * 3 + 2] = radius * Math.cos(phi)

            // 颜色逻辑（Omnia Brain 主题）
            const randomVal = Math.random()
            if (randomVal > 0.99) {
                color.set('#ffc266') // Spark
            } else if (randomVal > 0.90) {
                color.set('#ff8a00') // Brand Orange (Highlights)
            } else if (randomVal > 0.7) {
                color.set('#4a2000') // Dark Burnt Orange
            } else {
                color.set('#00151a') // Darker Void Teal
            }

            colors[i * 3] = color.r
            colors[i * 3 + 1] = color.g
            colors[i * 3 + 2] = color.b
        }

        return [positions, colors]
    }, [])

    useFrame((state, delta) => {
        const sensitivity = 0.5
        const lerpFactor = 0.1

        const targetX = (mouse.y * viewport.height / 100) * sensitivity
        const targetY = (mouse.x * viewport.width / 100) * sensitivity + (state.clock.elapsedTime / 20)

        ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, targetX, lerpFactor)
        ref.current.rotation.y = THREE.MathUtils.lerp(ref.current.rotation.y, targetY, lerpFactor)

        // Scale pulsation
        const pulse = 1.8 + Math.sin(state.clock.elapsedTime * 2) * 0.02
        ref.current.scale.set(pulse, pulse, pulse)
    })

    return (
        <group {...props}>
            <Points ref={ref} positions={positions} colors={colors} stride={3} frustumCulled={false}>
                <PointMaterial
                    transparent
                    vertexColors
                    size={viewport.width < 5.5 ? 0.012 : 0.006}
                    sizeAttenuation={true}
                    depthWrite={false}
                />
            </Points>
        </group>
    )
}
