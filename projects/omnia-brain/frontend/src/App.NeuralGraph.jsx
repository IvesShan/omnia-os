import { NeuralGraph3D } from './components/canvas/NeuralGraph3D'
import './index.css'

/**
 * 神经图谱演示页面
 * 直接访问查看酷炫效果
 */
function App() {
    return (
        <div style={{ 
            width: '100vw', 
            height: '100vh', 
            background: 'linear-gradient(135deg, #000810 0%, #001520 100%)',
            overflow: 'hidden'
        }}>
            <NeuralGraph3D />
        </div>
    )
}

export default App
