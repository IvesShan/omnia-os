// Tauri commands for Omnia backend management

use std::process::{Command, Child};
use std::sync::Mutex;
use std::path::PathBuf;
use std::fs;
use std::io::{BufRead, BufReader};
use tauri::{Emitter, Manager};
use serde::{Deserialize, Serialize};

// Global state
lazy_static::lazy_static! {
    static ref BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);
    static ref BACKEND_STATUS: Mutex<BackendStatus> = Mutex::new(BackendStatus::default());
    static ref CONFIG: Mutex<OmniaConfig> = Mutex::new(OmniaConfig::default());
}

// ============ Data Structures ============

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BackendStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub port: u16,
    pub uptime_secs: Option<u64>,
    pub last_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OmniaConfig {
    pub backend: BackendConfig,
    pub api: ApiConfig,
    pub memory: MemoryConfig,
}

impl Default for OmniaConfig {
    fn default() -> Self {
        Self {
            backend: BackendConfig::default(),
            api: ApiConfig::default(),
            memory: MemoryConfig::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    pub port: u16,
    pub auto_start: bool,
    pub log_level: String,
}

impl Default for BackendConfig {
    fn default() -> Self {
        Self {
            port: 5001,
            auto_start: true,
            log_level: "info".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiConfig {
    pub baidu_api_key: Option<String>,
    pub baidu_secret_key: Option<String>,
    pub kimi_api_key: Option<String>,
    pub default_model: String,
}

impl Default for ApiConfig {
    fn default() -> Self {
        Self {
            baidu_api_key: None,
            baidu_secret_key: None,
            kimi_api_key: None,
            default_model: "ernie-4.0-8k".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    pub memory_palace_path: Option<String>,
    pub max_entries: usize,
}

impl Default for MemoryConfig {
    fn default() -> Self {
        Self {
            memory_palace_path: None,
            max_entries: 10000,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryStats {
    pub total_facts: usize,
    pub total_relations: usize,
    pub total_habits: usize,
    pub total_timeline: usize,
}

// ============ Commands ============

#[tauri::command]
pub fn get_backend_status() -> BackendStatus {
    BACKEND_STATUS.lock().unwrap().clone()
}

#[tauri::command]
pub fn start_backend(app_handle: tauri::AppHandle) -> Result<String, String> {
    let config = CONFIG.lock().unwrap().clone();
    let port = config.backend.port;
    
    // Get backend executable path
    let backend_path = find_backend_path(&app_handle)?;
    
    println!("Starting backend from: {:?}", backend_path);
    
    // Kill existing backend if running
    let _ = Command::new("pkill")
        .args(["-f", "omnia-backend"])
        .output();
    
    std::thread::sleep(std::time::Duration::from_millis(500));
    
    // Start backend process
    let child = Command::new(&backend_path)
        .env("OMNIA_PORT", port.to_string())
        .env("RUST_LOG", &config.backend.log_level)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;
    
    let pid = child.id();
    
    // Update status
    {
        let mut status = BACKEND_STATUS.lock().unwrap();
        status.running = true;
        status.pid = Some(pid);
        status.port = port;
        status.last_error = None;
    }
    
    // Store process handle
    *BACKEND_PROCESS.lock().unwrap() = Some(child);
    
    // Start health check thread
    start_health_monitor(app_handle, pid);
    
    Ok(format!("Backend started on port {}", port))
}

#[tauri::command]
pub fn stop_backend() -> Result<String, String> {
    // Kill the backend process
    let _ = Command::new("pkill")
        .args(["-f", "omnia-backend"])
        .output();
    
    // Update status
    {
        let mut status = BACKEND_STATUS.lock().unwrap();
        status.running = false;
        status.pid = None;
        status.uptime_secs = None;
    }
    
    // Clear process handle
    *BACKEND_PROCESS.lock().unwrap() = None;
    
    Ok("Backend stopped".to_string())
}

#[tauri::command]
pub fn restart_backend(app_handle: tauri::AppHandle) -> Result<String, String> {
    stop_backend()?;
    std::thread::sleep(std::time::Duration::from_secs(1));
    start_backend(app_handle)
}

#[tauri::command]
pub fn get_config() -> OmniaConfig {
    CONFIG.lock().unwrap().clone()
}

#[tauri::command]
pub fn update_config(new_config: OmniaConfig) -> Result<String, String> {
    let mut config = CONFIG.lock().unwrap();
    *config = new_config;
    Ok("Config updated".to_string())
}

#[tauri::command]
pub async fn query_memory(query: String, layer: Option<String>) -> Result<serde_json::Value, String> {
    // Forward request to backend API
    let client = reqwest::Client::new();
    let url = format!("http://localhost:5001/api/memory/query");
    
    let mut body = serde_json::json!({
        "query": query
    });
    
    if let Some(l) = layer {
        body["layer"] = serde_json::json!(l);
    }
    
    let response = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    Ok(result)
}

#[tauri::command]
pub async fn add_memory_fact(content: String, tags: Vec<String>) -> Result<String, String> {
    let client = reqwest::Client::new();
    let url = format!("http://localhost:5001/api/memory/facts");
    
    let body = serde_json::json!({
        "content": content,
        "tags": tags
    });
    
    let response = client
        .post(&url)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;
    
    let result: serde_json::Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    Ok(result["id"].as_str().unwrap_or("unknown").to_string())
}

#[tauri::command]
pub fn get_memory_stats() -> MemoryStats {
    // Return mock stats for now
    // TODO: Query actual memory palace
    MemoryStats {
        total_facts: 0,
        total_relations: 0,
        total_habits: 0,
        total_timeline: 0,
    }
}

#[tauri::command]
pub fn read_logs(lines: Option<usize>) -> Result<Vec<String>, String> {
    let lines = lines.unwrap_or(100);
    
    // Try to read from log file
    let log_path = dirs::cache_dir()
        .map(|p| p.join("omnia/omnia-backend.log"))
        .ok_or("Could not find cache directory")?;
    
    if !log_path.exists() {
        return Ok(vec!["No logs found".to_string()]);
    }
    
    let file = fs::File::open(&log_path)
        .map_err(|e| format!("Failed to open log file: {}", e))?;
    
    let reader = BufReader::new(file);
    
    // Collect all lines first, then reverse
    let all_lines: Vec<String> = reader
        .lines()
        .filter_map(|l| l.ok())
        .collect();
    
    // Take last N lines
    let logs: Vec<String> = all_lines
        .into_iter()
        .rev()
        .take(lines)
        .collect();
    
    Ok(logs.into_iter().rev().collect())
}

#[tauri::command]
pub fn clear_logs() -> Result<String, String> {
    let log_path = dirs::cache_dir()
        .map(|p| p.join("omnia/omnia-backend.log"))
        .ok_or("Could not find cache directory")?;
    
    if log_path.exists() {
        fs::remove_file(&log_path)
            .map_err(|e| format!("Failed to clear logs: {}", e))?;
    }
    
    Ok("Logs cleared".to_string())
}

// ============ Helper Functions ============

fn find_backend_path(app_handle: &tauri::AppHandle) -> Result<PathBuf, String> {
    // Tauri 2.x path API
    let app_data_dir = app_handle.path().app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;
    
    let resource_dir = app_handle.path().resource_dir()
        .map_err(|e| format!("Failed to get resource dir: {}", e))?;
    
    // Try multiple locations
    let possible_paths = vec![
        // Development path
        app_data_dir.join("backend/omnia-backend"),
        // Production path (bundled)
        resource_dir.join("backend/omnia-backend"),
        // System path
        PathBuf::from("/usr/local/bin/omnia-backend"),
        // Relative path
        PathBuf::from("backend/omnia-backend"),
    ];
    
    for path in possible_paths {
        if path.exists() {
            return Ok(path);
        }
    }
    
    // Fallback: try to find in PATH
    let output = Command::new("which")
        .arg("omnia-backend")
        .output();
    
    if let Ok(output) = output {
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !path.is_empty() {
                return Ok(PathBuf::from(path));
            }
        }
    }
    
    Err("Could not find omnia-backend executable".to_string())
}

fn start_health_monitor(app_handle: tauri::AppHandle, pid: u32) {
    std::thread::spawn(move || {
        let start_time = std::time::Instant::now();
        
        loop {
            std::thread::sleep(std::time::Duration::from_secs(5));
            
            // Check if process is still running using /proc
            let is_running = check_process_alive(pid);
            
            // Update status
            {
                let mut status = BACKEND_STATUS.lock().unwrap();
                
                if is_running {
                    status.uptime_secs = Some(start_time.elapsed().as_secs());
                } else {
                    status.running = false;
                    status.pid = None;
                    status.uptime_secs = None;
                    status.last_error = Some("Backend process exited unexpectedly".to_string());
                    
                    // Emit event to frontend
                    let _ = app_handle.emit("backend-stopped", ());
                    break;
                }
            }
        }
    });
}

fn check_process_alive(pid: u32) -> bool {
    // Check /proc/{pid}/stat on Linux
    let stat_path = format!("/proc/{}/stat", pid);
    std::path::Path::new(&stat_path).exists()
}
