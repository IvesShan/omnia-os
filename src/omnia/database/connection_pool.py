"""
数据库连接池和优化
"""
import sqlite3
import threading
from typing import Optional, Dict, Any
from queue import Queue, Empty
from contextlib import contextmanager
import time


class ConnectionPool:
    """SQLite 连接池"""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        """
        Args:
            db_path: 数据库文件路径
            max_connections: 最大连接数
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool: Queue = Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        self.created_connections = 0
        
        # 初始化一些连接
        for _ in range(min(3, max_connections)):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """创建新连接"""
        with self.lock:
            if self.created_connections >= self.max_connections:
                return None
            
            try:
                conn = sqlite3.Connection(self.db_path)
                
                # 优化配置
                conn.execute("PRAGMA journal_mode=WAL")  # WAL 模式，提高并发
                conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
                conn.execute("PRAGMA cache_size=-64000")  # 64MB 缓存
                conn.execute("PRAGMA temp_store=MEMORY")  # 临时表在内存
                conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
                
                self.created_connections += 1
                return conn
            except Exception as e:
                print(f"[DB] Failed to create connection: {e}")
                return None
    
    def get(self, timeout: float = 5.0) -> Optional[sqlite3.Connection]:
        """获取连接"""
        try:
            # 尝试从池中获取
            conn = self.pool.get(block=True, timeout=timeout)
            return conn
        except Empty:
            # 池为空，尝试创建新连接
            conn = self._create_connection()
            if conn:
                return conn
            
            # 再次尝试从池中获取
            try:
                conn = self.pool.get(block=True, timeout=timeout)
                return conn
            except Empty:
                print("[DB] Connection pool exhausted")
                return None
    
    def put(self, conn: sqlite3.Connection):
        """归还连接"""
        if conn:
            try:
                # 检查连接是否有效
                conn.execute("SELECT 1")
                self.pool.put(conn, block=False)
            except Exception:
                # 连接无效，关闭并减少计数
                try:
                    conn.close()
                except:
                    pass
                with self.lock:
                    self.created_connections -= 1
    
    @contextmanager
    def connection(self, timeout: float = 5.0):
        """上下文管理器，自动归还连接"""
        conn = self.get(timeout)
        if conn is None:
            raise Exception("Failed to get database connection")
        
        try:
            yield conn
        finally:
            self.put(conn)
    
    def close_all(self):
        """关闭所有连接"""
        while not self.pool.empty():
            try:
                conn = self.pool.get(block=False)
                conn.close()
            except:
                pass
        
        with self.lock:
            self.created_connections = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            "pool_size": self.pool.qsize(),
            "max_connections": self.max_connections,
            "created_connections": self.created_connections,
            "available": self.pool.qsize()
        }


class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def create_indexes(conn: sqlite3.Connection, table: str):
        """为表创建常用索引"""
        if table == "memory_palace":
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory_palace(layer)",
                "CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_palace(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_palace(memory_type)",
            ]
        elif table == "sessions":
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_session_user ON sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_session_created ON sessions(created_at)",
            ]
        else:
            return
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                print(f"[DB] Failed to create index: {e}")
        
        conn.commit()
    
    @staticmethod
    def vacuum(conn: sqlite3.Connection):
        """清理数据库碎片"""
        try:
            conn.execute("VACUUM")
            conn.commit()
            print("[DB] Database vacuumed")
        except Exception as e:
            print(f"[DB] Vacuum failed: {e}")
    
    @staticmethod
    def analyze(conn: sqlite3.Connection):
        """分析数据库统计信息"""
        try:
            conn.execute("ANALYZE")
            conn.commit()
            print("[DB] Database analyzed")
        except Exception as e:
            print(f"[DB] Analyze failed: {e}")
    
    @staticmethod
    def get_table_stats(conn: sqlite3.Connection, table: str) -> Dict[str, Any]:
        """获取表统计信息"""
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            return {
                "table": table,
                "row_count": count,
                "columns": columns
            }
        except Exception as e:
            return {
                "table": table,
                "error": str(e)
            }


class BatchInserter:
    """批量插入器"""
    
    def __init__(self, conn: sqlite3.Connection, table: str, batch_size: int = 100):
        """
        Args:
            conn: 数据库连接
            table: 表名
            batch_size: 批量大小
        """
        self.conn = conn
        self.table = table
        self.batch_size = batch_size
        self.buffer = []
        self.columns = []
    
    def add(self, row: Dict[str, Any]):
        """添加一行数据"""
        if not self.columns:
            self.columns = list(row.keys())
        
        self.buffer.append(tuple(row[col] for col in self.columns))
        
        # 达到批量大小，执行插入
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """刷新缓冲区，执行插入"""
        if not self.buffer:
            return
        
        try:
            placeholders = ",".join(["?" for _ in self.columns])
            sql = f"INSERT INTO {self.table} ({','.join(self.columns)}) VALUES ({placeholders})"
            
            self.conn.executemany(sql, self.buffer)
            self.conn.commit()
            
            self.buffer = []
        except Exception as e:
            print(f"[DB] Batch insert failed: {e}")
            self.conn.rollback()


# 全局连接池实例
connection_pools: Dict[str, ConnectionPool] = {}


def get_connection_pool(db_path: str, max_connections: int = 10) -> ConnectionPool:
    """获取或创建连接池"""
    if db_path not in connection_pools:
        connection_pools[db_path] = ConnectionPool(db_path, max_connections)
    
    return connection_pools[db_path]


def close_all_pools():
    """关闭所有连接池"""
    for pool in connection_pools.values():
        pool.close_all()
    
    connection_pools.clear()


def get_all_pool_stats() -> Dict[str, Any]:
    """获取所有连接池统计"""
    return {
        db_path: pool.get_stats()
        for db_path, pool in connection_pools.items()
    }


if __name__ == "__main__":
    # 测试连接池
    print("Testing connection pool...")
    
    pool = ConnectionPool("/tmp/test.db", max_connections=5)
    
    # 使用上下文管理器
    with pool.connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test (name) VALUES (?)", ("test1",))
        conn.commit()
        
        cursor = conn.execute("SELECT * FROM test")
        print(f"Rows: {cursor.fetchall()}")
    
    print(f"Pool stats: {pool.get_stats()}")
    
    pool.close_all()
    print("Connection pool closed")
