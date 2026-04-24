import { useState } from 'react'

/**
 * 玻璃拟态 UI 覆盖层
 * 提供搜索、控制面板等交互功能
 */
export function Overlay() {
    const [searchQuery, setSearchQuery] = useState('')
    const [showPanel, setShowPanel] = useState(true)

    const handleSearch = (e) => {
        e.preventDefault()
        if (searchQuery.trim()) {
            console.log('Searching:', searchQuery)
            // TODO: 调用后端 API 搜索知识图谱
        }
    }

    return (
        <div className="absolute top-0 left-0 w-full h-full pointer-events-none z-10">
            {/* 顶部导航栏 */}
            <div className="absolute top-0 left-0 w-full p-4 pointer-events-auto">
                <div className="flex items-center justify-between max-w-7xl mx-auto">
                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-orange to-void-teal flex items-center justify-center">
                            <span className="text-2xl">🧠</span>
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-brand-orange neon-glow">Omnia Brain</h1>
                            <p className="text-xs text-gray-400">全息知识图谱</p>
                        </div>
                    </div>

                    {/* 搜索栏 */}
                    <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-8">
                        <div className="glass-panel flex items-center px-4 py-2">
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="搜索知识节点..."
                                className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500"
                            />
                            <button
                                type="submit"
                                className="glass-button px-4 py-1 rounded text-brand-orange font-semibold"
                            >
                                搜索
                            </button>
                        </div>
                    </form>

                    {/* 控制按钮 */}
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowPanel(!showPanel)}
                            className="glass-button px-4 py-2 rounded text-sm"
                        >
                            {showPanel ? '隐藏' : '显示'}面板
                        </button>
                        <button className="glass-button px-4 py-2 rounded text-sm text-brand-orange">
                            ⚙️ 设置
                        </button>
                    </div>
                </div>
            </div>

            {/* 左侧信息面板 */}
            {showPanel && (
                <div className="absolute left-4 top-20 bottom-4 w-80 pointer-events-auto">
                    <div className="glass-panel h-full p-4 overflow-y-auto">
                        <h2 className="text-lg font-bold text-brand-orange mb-4">📊 知识图谱统计</h2>
                        
                        <div className="space-y-4">
                            <div className="glass-panel p-3">
                                <div className="text-sm text-gray-400">节点总数</div>
                                <div className="text-2xl font-bold text-neon-cyan">1,247</div>
                            </div>
                            
                            <div className="glass-panel p-3">
                                <div className="text-sm text-gray-400">连接总数</div>
                                <div className="text-2xl font-bold text-brand-orange">3,891</div>
                            </div>

                            <div className="glass-panel p-3">
                                <div className="text-sm text-gray-400">向量维度</div>
                                <div className="text-2xl font-bold text-purple-400">768</div>
                            </div>

                            <div className="glass-panel p-3">
                                <div className="text-sm text-gray-400">数据库状态</div>
                                <div className="flex gap-2 mt-2">
                                    <span className="px-2 py-1 rounded bg-green-900/50 text-green-400 text-xs">
                                        Neo4j ✓
                                    </span>
                                    <span className="px-2 py-1 rounded bg-green-900/50 text-green-400 text-xs">
                                        Qdrant ✓
                                    </span>
                                    <span className="px-2 py-1 rounded bg-green-900/50 text-green-400 text-xs">
                                        Ollama ✓
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6">
                            <h3 className="text-sm font-semibold text-gray-400 mb-2">最近添加的节点</h3>
                            <div className="space-y-2">
                                {['Memory Palace', 'Gateway', 'Persona', 'Infinite'].map((node, i) => (
                                    <div key={i} className="glass-panel p-2 flex items-center justify-between">
                                        <span className="text-sm">{node}</span>
                                        <span className="text-xs text-gray-500">{i + 1}h ago</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="mt-6">
                            <h3 className="text-sm font-semibold text-gray-400 mb-2">快速操作</h3>
                            <div className="grid grid-cols-2 gap-2">
                                <button className="glass-button p-2 rounded text-sm">
                                    📥 导入数据
                                </button>
                                <button className="glass-button p-2 rounded text-sm">
                                    📤 导出图谱
                                </button>
                                <button className="glass-button p-2 rounded text-sm">
                                    🔄 刷新
                                </button>
                                <button className="glass-button p-2 rounded text-sm text-brand-orange">
                                    ➕ 新建节点
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 底部状态栏 */}
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 pointer-events-auto">
                <div className="glass-panel px-6 py-2 flex items-center gap-4 text-sm">
                    <span className="text-gray-400">GPU: <span className="text-green-400">Active</span></span>
                    <span className="text-gray-400">FPS: <span className="text-neon-cyan">60</span></span>
                    <span className="text-gray-400">粒子: <span className="text-brand-orange">55,000</span></span>
                    <span className="text-gray-400">后端: <span className="text-green-400">Connected</span></span>
                </div>
            </div>
        </div>
    )
}
