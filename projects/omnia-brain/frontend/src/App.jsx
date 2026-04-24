import { Canvas } from '@react-three/fiber'
import { Experience } from './components/canvas/Experience'
import { Overlay } from './components/dom/Overlay'

function App() {
    return (
        <div className="relative w-full h-full bg-deep-black">
            {/* 3D Scene Layer */}
            <div className="absolute top-0 left-0 w-full h-full z-0">
                <Canvas camera={{ position: [0, 0, 5] }}>
                    <color attach="background" args={['#050505']} />
                    <Experience />
                </Canvas>
            </div>

            {/* UI Overlay Layer */}
            <Overlay />
        </div>
    )
}

export default App
