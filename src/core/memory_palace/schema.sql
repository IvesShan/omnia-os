-- Memory Palace 2.0 Schema
-- Six layers of memory: facts, relations, habits, timeline, conversation_logs, tool_logs
-- With vector embeddings for semantic search
-- Version 2.1: Added versioning, conflict detection, and status tracking

-- ============================================
-- Layer 1: Facts (entities and their attributes)
-- ============================================
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,           -- e.g. 'project', 'person', 'preference', 'credential'
    key TEXT NOT NULL,                -- e.g. '喵修匠'
    value TEXT NOT NULL,              -- the fact itself
    source TEXT,                      -- 'conversation', 'file', 'observation'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    strength REAL DEFAULT 1.0,        -- memory strength, decays over time if not reinforced
    embedding BLOB,                   -- 384-dim vector for semantic search
    
    -- 版本控制（新增）
    version INTEGER DEFAULT 1,        -- 版本号，每次更新递增
    status TEXT DEFAULT 'active',     -- 'active', 'deprecated', 'archived'
    supersedes INTEGER,               -- 被此版本取代的旧版本 ID
    tags TEXT,                        -- JSON array of tags
    priority INTEGER DEFAULT 0,       -- 优先级（越高越重要）
    
    UNIQUE(category, key, version)
);

-- ============================================
-- Layer 2: Relations (connections between entities)
-- ============================================
CREATE TABLE IF NOT EXISTS relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,            -- e.g. '喵修匠'
    predicate TEXT NOT NULL,          -- e.g. 'depends_on'
    object TEXT NOT NULL,             -- e.g. 'njuosun.com'
    context TEXT,                     -- why this relation exists
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    strength REAL DEFAULT 1.0,
    
    -- 版本控制（新增）
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',     -- 'active', 'deprecated', 'archived'
    supersedes INTEGER,
    evidence TEXT                     -- 具体证据
);

-- ============================================
-- Layer 3: Habits (user behavior patterns and preferences)
-- ============================================
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,             -- 'communication', 'work_hours', 'aesthetic', 'decision_style'
    pattern TEXT NOT NULL,            -- what the habit is
    evidence TEXT,                    -- specific examples that support this habit
    certainty REAL DEFAULT 0.5,       -- how confident we are (0.0 - 1.0)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_observed_at TIMESTAMP,
    embedding BLOB,                   -- 384-dim vector for semantic search
    
    -- 版本控制（新增）
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    supersedes INTEGER,
    observation_count INTEGER DEFAULT 1
);

-- ============================================
-- Layer 4: Timeline (chronological decisions and events)
-- ============================================
CREATE TABLE IF NOT EXISTS timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date DATE NOT NULL,         -- YYYY-MM-DD
    event_type TEXT NOT NULL,         -- 'decision', 'milestone', 'failure', 'insight'
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT,                        -- comma-separated for easy search
    related_facts TEXT,               -- JSON array of related fact IDs
    session_key TEXT,                 -- link back to the conversation that produced this
    embedding BLOB,                   -- 384-dim vector for semantic search
    
    -- 版本控制（新增）
    version INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    supersedes INTEGER
);

-- ============================================
-- Layer 5: Conversation Logs (complete dialogue history)
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,         -- unique session identifier
    turn_number INTEGER NOT NULL,     -- conversation turn (1, 2, 3...)
    role TEXT NOT NULL,               -- 'user' or 'assistant'
    content TEXT NOT NULL,            -- complete message content
    persona TEXT,                     -- which persona responded (if assistant)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding BLOB,                   -- 384-dim vector for semantic search
    metadata TEXT,                    -- JSON: context, detected_intent, etc.
    extracted INTEGER DEFAULT 0,      -- 是否已提取为核心记忆
    extraction_notes TEXT             -- 提取备注
);

CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_created ON conversation_logs(created_at);

-- ============================================
-- Layer 6: Tool Logs (complete tool invocation history)
-- ============================================
CREATE TABLE IF NOT EXISTS tool_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,         -- link to conversation session
    turn_number INTEGER,              -- which conversation turn triggered this
    tool_name TEXT NOT NULL,          -- e.g. 'read_file', 'execute_shell'
    arguments TEXT NOT NULL,          -- JSON of arguments
    result TEXT,                      -- complete result/output
    success INTEGER DEFAULT 1,        -- 1 = success, 0 = failure
    error_message TEXT,               -- if failed
    duration_ms INTEGER,              -- execution time in milliseconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding BLOB                    -- 384-dim vector for semantic search
);

CREATE INDEX IF NOT EXISTS idx_tool_session ON tool_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_name ON tool_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_created ON tool_logs(created_at);

-- ============================================
-- 冲突检测表（新增）
-- ============================================
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    layer TEXT NOT NULL,              -- 'facts', 'relations', 'habits', 'timeline'
    entity_key TEXT NOT NULL,         -- 冲突实体的标识（如 category:key）
    old_id INTEGER,                   -- 旧版本 ID
    new_id INTEGER,                   -- 新版本 ID
    old_value TEXT,                   -- 旧值摘要
    new_value TEXT,                   -- 新值摘要
    source TEXT,                      -- 冲突来源
    resolved TEXT DEFAULT 'pending',  -- 'pending', 'resolved', 'ignored'
    resolution_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- ============================================
-- Full-text search virtual table for timeline
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS timeline_search USING fts5(
    title,
    description,
    tags,
    content='timeline',
    content_rowid='id'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS timeline_insert_fts AFTER INSERT ON timeline BEGIN
    INSERT INTO timeline_search(rowid, title, description, tags)
    VALUES (new.id, new.title, new.description, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS timeline_delete_fts AFTER DELETE ON timeline BEGIN
    INSERT INTO timeline_search(timeline_search, rowid, title, description, tags)
    VALUES ('delete', old.id, old.title, old.description, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS timeline_update_fts AFTER UPDATE ON timeline BEGIN
    INSERT INTO timeline_search(timeline_search, rowid, title, description, tags)
    VALUES ('delete', old.id, old.title, old.description, old.tags);
    INSERT INTO timeline_search(rowid, title, description, tags)
    VALUES (new.id, new.title, new.description, new.tags);
END;

-- ============================================
-- Full-text search for conversation logs
-- ============================================
CREATE VIRTUAL TABLE IF NOT EXISTS conversation_search USING fts5(
    content,
    content='conversation_logs',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS conversation_insert_fts AFTER INSERT ON conversation_logs BEGIN
    INSERT INTO conversation_search(rowid, content)
    VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS conversation_delete_fts AFTER DELETE ON conversation_logs BEGIN
    INSERT INTO conversation_search(conversation_search, rowid, content)
    VALUES ('delete', old.id, old.content);
END;

-- ============================================
-- Indexes for semantic search
-- ============================================
CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category);
CREATE INDEX IF NOT EXISTS idx_facts_strength ON facts(strength DESC);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status);

CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline(event_date DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_type ON timeline(event_type);
CREATE INDEX IF NOT EXISTS idx_timeline_status ON timeline(status);

CREATE INDEX IF NOT EXISTS idx_habits_domain ON habits(domain);
CREATE INDEX IF NOT EXISTS idx_habits_certainty ON habits(certainty DESC);
CREATE INDEX IF NOT EXISTS idx_habits_status ON habits(status);

CREATE INDEX IF NOT EXISTS idx_relations_status ON relations(status);
CREATE INDEX IF NOT EXISTS idx_conflicts_resolved ON conflicts(resolved);
