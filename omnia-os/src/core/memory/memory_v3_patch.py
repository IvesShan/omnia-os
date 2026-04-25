"""
补丁：添加 add_habit 和 add_timeline_event 方法到 MemoryV3
"""

# 在 get_relations 方法之后添加以下方法

def add_habit(
    self,
    domain: str,
    pattern: str,
    evidence: str = None,
    certainty: float = 0.5
) -> int:
    """
    添加习惯记忆（自动版本控制）
    
    Args:
        domain: 领域（如 coding, communication, workflow）
        pattern: 模式描述
        evidence: 证据
        certainty: 确定性 (0-1)
    
    Returns:
        新记录的 ID
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    
    # 检查是否存在相同 pattern
    cursor.execute('''
        SELECT id, version FROM habits 
        WHERE domain = ? AND pattern = ? AND status = 'active'
        ORDER BY version DESC LIMIT 1
    ''', (domain, pattern))
    
    existing = cursor.fetchone()
    
    if existing:
        # 更新现有记录
        cursor.execute('''
            UPDATE habits 
            SET observation_count = observation_count + 1,
                last_observed_at = ?,
                certainty = (certainty + ?) / 2
            WHERE id = ?
        ''', (datetime.now().isoformat(), certainty, existing['id']))
        
        conn.commit()
        conn.close()
        return existing['id']
    
    # 创建新记录
    cursor.execute('''
        INSERT INTO habits
        (domain, pattern, evidence, version, status, created_at, last_observed_at, certainty)
        VALUES (?, ?, ?, 1, 'active', ?, ?, ?)
    ''', (
        domain,
        pattern,
        evidence,
        datetime.now().isoformat(),
        datetime.now().isoformat(),
        certainty
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    self.stats["total_facts"] += 1
    return new_id


def add_timeline_event(
    self,
    event_date: str,
    title: str,
    event_type: str = None,
    description: str = None,
    tags: List[str] = None,
    session_key: str = None
) -> int:
    """
    添加时间线事件（自动版本控制）
    
    Args:
        event_date: 事件日期 (YYYY-MM-DD)
        title: 事件标题
        event_type: 事件类型
        description: 事件描述
        tags: 标签列表
        session_key: 关联的会话 key
    
    Returns:
        新记录的 ID
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO timeline
        (event_date, event_type, title, description, tags, session_key, version, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?)
    ''', (
        event_date,
        event_type,
        title,
        description,
        json.dumps(tags) if tags else None,
        session_key,
        datetime.now().isoformat()
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return new_id
