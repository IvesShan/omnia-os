"""
Omnia Memory Manager V2 - 改进版
支持：智能压缩、过期清理、冲突检测、备份恢复
"""

import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import re


class MemoryManagerV2:
    """改进版记忆管理器"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent.parent / "memory"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 分层存储
        self.layers = {
            "facts": self.base_path / "facts.json",
            "relations": self.base_path / "relations.json",
            "habits": self.base_path / "habits.json",
            "timeline": self.base_path / "timeline.json"
        }
        
        # 备份目录
        self.backup_path = self.base_path / "backups"
        self.backup_path.mkdir(exist_ok=True)
        
        # 加载记忆
        self.memory = {}
        self._load_memory()
        
        # 统计信息
        self.stats = {
            "total_entries": 0,
            "last_cleanup": None,
            "compression_ratio": 0.0
        }
    
    def _load_memory(self):
        """加载所有层级的记忆"""
        for layer, path in self.layers.items():
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    self.memory[layer] = json.load(f)
            else:
                self.memory[layer] = {}
    
    def _save_memory(self, layer: str = None):
        """保存记忆到文件"""
        if layer:
            with open(self.layers[layer], 'w', encoding='utf-8') as f:
                json.dump(self.memory[layer], f, ensure_ascii=False, indent=2)
        else:
            for layer in self.layers:
                with open(self.layers[layer], 'w', encoding='utf-8') as f:
                    json.dump(self.memory[layer], f, ensure_ascii=False, indent=2)
    
    # ========== 核心功能 ==========
    
    def add_fact(self, key: str, value: Any, source: str = "user", 
                 ttl_days: int = None, priority: int = 0) -> bool:
        """添加事实记忆"""
        # 冲突检测
        if key in self.memory["facts"]:
            existing = self.memory["facts"][key]
            if existing["value"] != value:
                # 记录冲突
                self._log_conflict(key, existing["value"], value, source)
                # 高优先级覆盖
                if priority > existing.get("priority", 0):
                    return self._update_fact(key, value, source, ttl_days, priority)
                return False
        
        # 添加新事实
        entry = {
            "key": key,
            "value": value,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
            "priority": priority,
            "tags": self._extract_tags(value)
        }
        
        if ttl_days:
            entry["expires_at"] = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        
        self.memory["facts"][key] = entry
        self._save_memory("facts")
        return True
    
    def _update_fact(self, key: str, value: Any, source: str, 
                     ttl_days: int, priority: int) -> bool:
        """更新事实"""
        entry = self.memory["facts"][key]
        entry["value"] = value
        entry["source"] = source
        entry["updated_at"] = datetime.now().isoformat()
        entry["priority"] = priority
        
        if ttl_days:
            entry["expires_at"] = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        
        self._save_memory("facts")
        return True
    
    def get_fact(self, key: str) -> Optional[Any]:
        """获取事实"""
        if key not in self.memory["facts"]:
            return None
        
        entry = self.memory["facts"][key]
        
        # 检查过期
        if "expires_at" in entry:
            if datetime.now() > datetime.fromisoformat(entry["expires_at"]):
                del self.memory["facts"][key]
                self._save_memory("facts")
                return None
        
        # 更新访问计数
        entry["access_count"] = entry.get("access_count", 0) + 1
        entry["last_accessed"] = datetime.now().isoformat()
        self._save_memory("facts")
        
        return entry["value"]
    
    def query(self, query: str, layer: str = None, limit: int = 10) -> List[Dict]:
        """查询记忆"""
        results = []
        query_lower = query.lower()
        
        layers_to_search = [layer] if layer else self.layers.keys()
        
        for l in layers_to_search:
            if l not in self.memory:
                continue
            
            for key, entry in self.memory[l].items():
                # 简单的关键词匹配
                if self._matches_query(entry, query_lower):
                    results.append({
                        "layer": l,
                        "key": key,
                        "entry": entry,
                        "relevance": self._calculate_relevance(entry, query_lower)
                    })
        
        # 按相关性排序
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]
    
    def _matches_query(self, entry: Dict, query: str) -> bool:
        """检查条目是否匹配查询"""
        # 检查 key
        if query in entry.get("key", "").lower():
            return True
        
        # 检查 value
        value = entry.get("value", "")
        if isinstance(value, str) and query in value.lower():
            return True
        
        # 检查 tags
        if query in [tag.lower() for tag in entry.get("tags", [])]:
            return True
        
        return False
    
    def _calculate_relevance(self, entry: Dict, query: str) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # key 匹配加分
        if query in entry.get("key", "").lower():
            score += 10.0
        
        # value 匹配加分
        value = entry.get("value", "")
        if isinstance(value, str):
            score += value.lower().count(query) * 2.0
        
        # 访问次数加分
        score += entry.get("access_count", 0) * 0.1
        
        # 优先级加分
        score += entry.get("priority", 0) * 5.0
        
        # 时间衰减
        created_at = entry.get("created_at")
        if created_at:
            age_days = (datetime.now() - datetime.fromisoformat(created_at)).days
            score *= max(0.1, 1.0 - age_days * 0.01)
        
        return score
    
    # ========== 智能压缩 ==========
    
    def compress_memory(self) -> Dict[str, int]:
        """压缩记忆，移除冗余"""
        stats = {"removed": 0, "merged": 0, "compressed": 0}
        
        # 1. 移除过期条目
        stats["removed"] += self._remove_expired()
        
        # 2. 合并相似条目
        stats["merged"] += self._merge_similar()
        
        # 3. 压缩长文本
        stats["compressed"] += self._compress_long_texts()
        
        self._save_memory()
        
        self.stats["last_cleanup"] = datetime.now().isoformat()
        return stats
    
    def _remove_expired(self) -> int:
        """移除过期条目"""
        removed = 0
        now = datetime.now()
        
        for layer in self.memory:
            expired_keys = []
            for key, entry in self.memory[layer].items():
                if "expires_at" in entry:
                    if now > datetime.fromisoformat(entry["expires_at"]):
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory[layer][key]
                removed += 1
        
        return removed
    
    def _merge_similar(self) -> int:
        """合并相似条目"""
        merged = 0
        
        # 简单实现：合并相同 key 的条目
        # TODO: 实现更智能的相似度检测
        
        return merged
    
    def _compress_long_texts(self) -> int:
        """压缩长文本"""
        compressed = 0
        
        for layer in self.memory:
            for key, entry in self.memory[layer].items():
                value = entry.get("value")
                if isinstance(value, str) and len(value) > 1000:
                    # 保留前500字符 + 摘要
                    entry["value_full"] = value
                    entry["value"] = value[:500] + "...[已压缩]"
                    entry["compressed"] = True
                    compressed += 1
        
        return compressed
    
    # ========== 备份恢复 ==========
    
    def backup(self, name: str = None) -> str:
        """创建备份"""
        if name is None:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_dir = self.backup_path / name
        backup_dir.mkdir(exist_ok=True)
        
        # 复制所有记忆文件
        for layer, path in self.layers.items():
            if path.exists():
                shutil.copy2(path, backup_dir / path.name)
        
        # 创建备份元数据
        metadata = {
            "created_at": datetime.now().isoformat(),
            "stats": self.get_stats()
        }
        
        with open(backup_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return name
    
    def restore(self, name: str) -> bool:
        """从备份恢复"""
        backup_dir = self.backup_path / name
        
        if not backup_dir.exists():
            return False
        
        # 恢复所有记忆文件
        for layer, path in self.layers.items():
            backup_file = backup_dir / path.name
            if backup_file.exists():
                shutil.copy2(backup_file, path)
        
        # 重新加载记忆
        self._load_memory()
        
        return True
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for backup_dir in self.backup_path.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    backups.append({
                        "name": backup_dir.name,
                        "created_at": metadata.get("created_at"),
                        "stats": metadata.get("stats")
                    })
        
        # 按时间排序
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
    
    # ========== 统计信息 ==========
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            "layers": {},
            "total_entries": 0,
            "total_size_bytes": 0
        }
        
        for layer, path in self.layers.items():
            if path.exists():
                size = path.stat().st_size
                count = len(self.memory.get(layer, {}))
                stats["layers"][layer] = {
                    "count": count,
                    "size_bytes": size
                }
                stats["total_entries"] += count
                stats["total_size_bytes"] += size
        
        return stats
    
    # ========== 工具方法 ==========
    
    def _extract_tags(self, value: Any) -> List[str]:
        """从值中提取标签"""
        if not isinstance(value, str):
            return []
        
        # 简单的关键词提取
        tags = []
        keywords = re.findall(r'\b[A-Z][a-z]+\b', value)  # 大写开头的词
        tags.extend(keywords[:5])  # 最多5个标签
        
        return tags
    
    def _log_conflict(self, key: str, old_value: Any, new_value: Any, source: str):
        """记录冲突"""
        conflict = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存到冲突日志
        conflict_log = self.base_path / "conflicts.json"
        conflicts = []
        
        if conflict_log.exists():
            with open(conflict_log, 'r', encoding='utf-8') as f:
                conflicts = json.load(f)
        
        conflicts.append(conflict)
        
        with open(conflict_log, 'w', encoding='utf-8') as f:
            json.dump(conflicts, f, ensure_ascii=False, indent=2)

    # ========== 兼容性方法 ==========
    
    def retrieve_relevant(self, query: str, top_k: int = 5, min_score: float = 0.1) -> List[Tuple[Any, float]]:
        """
        检索相关记忆（兼容性方法）
        
        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            min_score: 最小相关性分数
        
        Returns:
            [(memory, score), ...] 列表
        """
        # 使用 query 方法获取结果
        results = self.query(query, layer="facts", limit=top_k * 2)
        
        # 过滤低分结果并格式化
        filtered_results = []
        for result in results:
            score = result.get("score", 0)
            if score >= min_score:
                # 创建一个简单的内存对象
                class Memory:
                    def __init__(self, content, metadata):
                        self.content = content
                        self.metadata = metadata
                
                memory = Memory(
                    content=str(result.get("value", "")),
                    metadata=result
                )
                filtered_results.append((memory, score))
        
        # 按分数排序并限制数量
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        return filtered_results[:top_k]
    
    def add_memory(self, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        添加记忆（兼容性方法）
        
        Args:
            content: 记忆内容
            role: 角色（"user" 或 "assistant"）
            metadata: 元数据
        
        Returns:
            创建的记忆对象
        """
        # 生成唯一 key
        key = f"memory_{role}_{datetime.now().isoformat()}"
        
        # 添加到 facts 层
        self.add_fact(
            key=key,
            value={
                "content": content,
                "role": role,
                "metadata": metadata or {}
            },
            source="conversation"
        )
        
        # 返回一个简单的内存对象
        class Memory:
            def __init__(self, id, content, role):
                self.id = id
                self.content = content
                self.role = role
        
        return Memory(key, content, role)

    # ========== 向量搜索增强 ==========
    
    def query_vector(self, query: str, layer: str = None, limit: int = 10, use_vector: bool = True) -> List[Dict]:
        """
        增强版查询 - 支持向量相似度搜索
        
        Args:
            query: 查询文本
            layer: 指定层级（可选）
            limit: 返回结果数量
            use_vector: 是否使用向量搜索（默认True）
        
        Returns:
            排序后的结果列表
        """
        # 先执行关键词匹配
        keyword_results = self.query(query, layer, limit * 2)
        
        if not use_vector:
            return keyword_results[:limit]
        
        # 尝试向量搜索
        try:
            from pathlib import Path
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from embedding.local_embedding import VectorMemoryIndex
            
            vector_index = VectorMemoryIndex()
            
            # 向量搜索
            vector_results = vector_index.search(query, top_k=limit)
            
            # 合并结果
            merged = {}
            
            # 添加关键词结果
            for r in keyword_results:
                key = r["key"]
                merged[key] = r
                merged[key]["source"] = "keyword"
            
            # 添加/更新向量结果
            for key, score in vector_results:
                if key in merged:
                    # 融合分数
                    merged[key]["relevance"] = (merged[key]["relevance"] + score) / 2
                    merged[key]["source"] = "hybrid"
                else:
                    # 从记忆中获取条目
                    for l in (self.layers.keys() if not layer else [layer]):
                        if l in self.memory and key in self.memory[l]:
                            merged[key] = {
                                "layer": l,
                                "key": key,
                                "entry": self.memory[l][key],
                                "relevance": score,
                                "source": "vector"
                            }
                            break
            
            # 排序并返回
            results = list(merged.values())
            results.sort(key=lambda x: x["relevance"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            # 向量搜索失败，返回关键词结果
            return keyword_results[:limit]

    # ========== 自动向量索引 ==========
    
    def _update_vector_index(self, key: str, content: str):
        """自动更新向量索引"""
        try:
            from pathlib import Path
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from embedding.local_embedding import VectorMemoryIndex
            
            vector_index = VectorMemoryIndex()
            vector_index.add(key, content)
        except Exception as e:
            pass  # 静默失败，不影响主流程
    
    def build_vector_index(self, layer: str = None):
        """
        构建向量索引
        
        Args:
            layer: 指定层级（None表示所有层级）
        """
        try:
            from pathlib import Path
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from embedding.local_embedding import VectorMemoryIndex
            
            vector_index = VectorMemoryIndex()
            vector_index.clear()
            
            layers_to_index = [layer] if layer else self.layers.keys()
            count = 0
            
            for l in layers_to_index:
                if l not in self.memory:
                    continue
                
                for key, entry in self.memory[l].items():
                    # 提取内容
                    if isinstance(entry, dict):
                        content = str(entry.get("value", ""))
                    else:
                        content = str(entry)
                    
                    if content:
                        vector_index.add(key, content)
                        count += 1
            
            return count
        except Exception as e:
            return 0
