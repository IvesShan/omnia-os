import { useState, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Points, PointMaterial } from '@react-three/drei'
import * as random from 'maath/random/dist/maath-random.esm'

export function Particles(props) {
    const ref = useRef()
    const [sphere] = useState(() => random.inSphere(new Float32Array(5000 * 3), { radius: 10 }))

    useFrame((state, delta) => {
        ref.current.rotation.x -= delta / 30
        ref.current.rotation.y -= delta / 35
    })

    return (
        <group rotation={[0, 0, Math.PI / 4]}>
            <Points ref={ref} positions={sphere} stride={3} frustumCulled={false} {...props}>
                <PointMaterial
                    transparent
                    color="#00ffff"
                    size={0.035}
                    sizeAttenuation={true}
                    depthWrite={false}
                    opacity={0.9}
                />
            </Points>
        </group>
    )
}
