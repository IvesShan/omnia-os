use serde::{Deserialize, Serialize};
use std::process::Command;
use std::fs;
use std::path::PathBuf;
use chrono::{DateTime, Local, TimeZone};

#[derive(Debug, Serialize, Deserialize)]
pub struct Stats {
    facts: i32,
    relations: i32,
    habits: i32,
    timeline: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Status {
    daemon_pid: Option<u32>,
    api_online: bool,
    stats: Stats,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Backup {
    name: String,
    size: String,
    created: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchResult {
    id: i64,
    category: String,
    key: String,
    value: String,
}

fn get_omnia_path() -> PathBuf {
    dirs::home_dir()
        .unwrap()
        .join(".openclaw")
        .join("workspace")
        .join("omnia-os")
}

fn get_db_path() -> PathBuf {
    get_omnia_path().join("memory_palace.db")
}

fn get_backups_path() -> PathBuf {
    get_omnia_path().join("backups")
}

fn get_logs_path() -> PathBuf {
    get_omnia_path().join("logs").join("daemon.log")
}

// 获取守护进程 PID
#[tauri::command]
fn get_daemon_pid() -> Option<u32> {
    let output = Command::new("pgrep")
        .args(["-f", "start_daemon.py"])
        .output()
        .ok()?;
    
    if output.status.success() {
        let pid_str = String::from_utf8_lossy(&output.stdout);
        pid_str.trim().parse().ok()
    } else {
        None
    }
}

// 检查 API 是否在线
#[tauri::command]
fn check_api_online() -> bool {
    let client = reqwest::blocking::Client::new();
    client
        .get("http://localhost:5001/health")
        .timeout(std::time::Duration::from_secs(2))
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

// 获取记忆统计
#[tauri::command]
fn get_stats() -> Stats {
    let db_path = get_db_path();
    
    if !db_path.exists() {
        return Stats {
            facts: 0,
            relations: 0,
            habits: 0,
            timeline: 0,
        };
    }

    let conn = rusqlite::Connection::open(&db_path).ok().unwrap();
    
    let facts: i32 = conn
        .query_row("SELECT COUNT(*) FROM facts", [], |r| r.get(0))
        .unwrap_or(0);
    
    let relations: i32 = conn
        .query_row("SELECT COUNT(*) FROM relations", [], |r| r.get(0))
        .unwrap_or(0);
    
    let habits: i32 = conn
        .query_row("SELECT COUNT(*) FROM habits", [], |r| r.get(0))
        .unwrap_or(0);
    
    let timeline: i32 = conn
        .query_row("SELECT COUNT(*) FROM timeline", [], |r| r.get(0))
        .unwrap_or(0);

    Stats {
        facts,
        relations,
        habits,
        timeline,
    }
}

// 获取完整状态
#[tauri::command]
fn get_status() -> Status {
    Status {
        daemon_pid: get_daemon_pid(),
        api_online: check_api_online(),
        stats: get_stats(),
    }
}

// 启动守护进程
#[tauri::command]
fn start_daemon() -> Result<String, String> {
    let omnia_path = get_omnia_path();
    let daemon_script = omnia_path.join("scripts").join("start_daemon.py");
    
    Command::new("python3")
        .arg(&daemon_script)
        .current_dir(&omnia_path)
        .spawn()
        .map(|_| "守护进程已启动".to_string())
        .map_err(|e| format!("启动失败: {}", e))
}

// 停止守护进程
#[tauri::command]
fn stop_daemon() -> Result<String, String> {
    if let Some(pid) = get_daemon_pid() {
        Command::new("kill")
            .arg(pid.to_string())
            .spawn()
            .map(|_| "守护进程已停止".to_string())
            .map_err(|e| format!("停止失败: {}", e))
    } else {
        Err("守护进程未运行".to_string())
    }
}

// 获取日志
#[tauri::command]
fn get_logs(lines: i32) -> String {
    let logs_path = get_logs_path();
    
    if !logs_path.exists() {
        return "日志文件不存在".to_string();
    }
    
    let output = Command::new("tail")
        .args(["-n", &lines.to_string()])
        .arg(&logs_path)
        .output();
    
    match output {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(e) => format!("读取日志失败: {}", e),
    }
}

// 创建备份
#[tauri::command]
fn create_backup() -> Result<String, String> {
    let db_path = get_db_path();
    let backups_path = get_backups_path();
    
    if !db_path.exists() {
        return Err("数据库文件不存在".to_string());
    }
    
    fs::create_dir_all(&backups_path).map_err(|e| e.to_string())?;
    
    let timestamp = Local::now().format("%Y%m%d_%H%M%S");
    let backup_name = format!("memory_palace_{}.db", timestamp);
    let backup_path = backups_path.join(&backup_name);
    
    fs::copy(&db_path, &backup_path)
        .map(|_| format!("备份已创建: {}", backup_name))
        .map_err(|e| format!("备份失败: {}", e))
}

// 获取备份列表
#[tauri::command]
fn list_backups() -> Vec<Backup> {
    let backups_path = get_backups_path();
    let mut backups = Vec::new();
    
    if !backups_path.exists() {
        return backups;
    }
    
    if let Ok(entries) = fs::read_dir(&backups_path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map(|e| e == "db").unwrap_or(false) {
                if let Ok(metadata) = entry.metadata() {
                    let size = metadata.len();
                    let created = metadata.created()
                        .ok()
                        .and_then(|t| {
                            let dt: DateTime<Local> = DateTime::from(t);
                            Some(dt)
                        })
                        .unwrap_or_else(Local::now);

                    backups.push(Backup {
                        name: path.file_name().unwrap().to_string_lossy().to_string(),
                        size: format!("{:.2} MB", size as f64 / 1024.0 / 1024.0),
                        created: created.format("%Y-%m-%d %H:%M:%S").to_string(),
                    });
                }
            }
        }
    }
    
    backups.sort_by(|a, b| b.created.cmp(&a.created));
    backups
}

// 恢复备份
#[tauri::command]
fn restore_backup(backup_name: String) -> Result<String, String> {
    let db_path = get_db_path();
    let backup_path = get_backups_path().join(&backup_name);
    
    if !backup_path.exists() {
        return Err("备份文件不存在".to_string());
    }
    
    // 先备份当前数据库
    if db_path.exists() {
        let current_backup = db_path.with_extension("db.pre_restore");
        fs::copy(&db_path, &current_backup).map_err(|e| e.to_string())?;
    }
    
    fs::copy(&backup_path, &db_path)
        .map(|_| format!("已恢复备份: {}", backup_name))
        .map_err(|e| format!("恢复失败: {}", e))
}

// 搜索记忆
#[tauri::command]
fn search_memory(query: String) -> Vec<SearchResult> {
    let db_path = get_db_path();
    let mut results = Vec::new();
    
    if !db_path.exists() {
        return results;
    }
    
    if let Ok(conn) = rusqlite::Connection::open(&db_path) {
        let search_pattern = format!("%{}%", query);
        
        // 搜索 facts
        let mut stmt = conn
            .prepare("SELECT id, category, key, value FROM facts WHERE key LIKE ?1 OR value LIKE ?1 LIMIT 50")
            .unwrap();
        
        let rows = stmt.query_map([&search_pattern], |row| {
            Ok(SearchResult {
                id: row.get(0)?,
                category: row.get(1)?,
                key: row.get(2)?,
                value: row.get(3)?,
            })
        }).unwrap();
        
        for row in rows.flatten() {
            results.push(row);
        }
    }
    
    results
}

// 获取分类统计
#[tauri::command]
fn get_category_stats() -> Vec<(String, i32)> {
    let db_path = get_db_path();
    let mut stats = Vec::new();
    
    if !db_path.exists() {
        return stats;
    }
    
    if let Ok(conn) = rusqlite::Connection::open(&db_path) {
        let mut stmt = conn
            .prepare("SELECT category, COUNT(*) as count FROM facts GROUP BY category ORDER BY count DESC LIMIT 20")
            .unwrap();
        
        let rows = stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i32>(1)?))
        }).unwrap();
        
        for row in rows.flatten() {
            stats.push(row);
        }
    }
    
    stats
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            get_daemon_pid,
            check_api_online,
            get_stats,
            get_status,
            start_daemon,
            stop_daemon,
            get_logs,
            create_backup,
            list_backups,
            restore_backup,
            search_memory,
            get_category_stats,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
