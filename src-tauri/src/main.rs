// Omnia Desktop Application
// An independent AIOS (AI Operating System)

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use commands::*;
use tauri::Manager;
use std::path::PathBuf;

fn get_config_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".omnia").join("config").join("settings.json")
}

fn is_first_run() -> bool {
    !get_config_path().exists()
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Check if this is first run
            let first_run = is_first_run();
            
            if first_run {
                println!("✓ First run detected - showing welcome window");
                
                // Show welcome window
                if let Some(welcome_window) = app.get_webview_window("welcome") {
                    welcome_window.show().unwrap();
                }
                
                // Hide main window initially
                if let Some(main_window) = app.get_webview_window("main") {
                    main_window.hide().unwrap();
                }
            } else {
                println!("✓ Existing installation - loading config");
                
                // Load config on startup
                let config = get_config();
                println!("✓ Config loaded");
                
                // Auto-start backend if configured
                if config.backend.auto_start {
                    let handle = app.handle().clone();
                    std::thread::spawn(move || {
                        std::thread::sleep(std::time::Duration::from_secs(1));
                        match start_backend(handle) {
                            Ok(msg) => println!("✓ Backend started automatically: {}", msg),
                            Err(e) => eprintln!("✗ Failed to auto-start backend: {}", e),
                        }
                    });
                }
            }
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_status,
            start_backend,
            stop_backend,
            restart_backend,
            get_config,
            update_config,
            read_logs,
            clear_logs,
            get_memory_stats,
            complete_setup
        ])
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Stop backend when window closes
                let _ = stop_backend();
                println!("✓ Backend stopped on window close");
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

// Complete setup wizard
#[tauri::command]
fn complete_setup(app: tauri::AppHandle, config: OmniaConfig) -> Result<(), String> {
    // Save config
    update_config(config)?;
    
    // Hide welcome window
    if let Some(welcome_window) = app.get_webview_window("welcome") {
        welcome_window.hide().unwrap();
    }
    
    // Show main window
    if let Some(main_window) = app.get_webview_window("main") {
        main_window.show().unwrap();
        main_window.set_focus().unwrap();
    }
    
    // Auto-start backend
    match start_backend(app) {
        Ok(msg) => println!("✓ Backend started after setup: {}", msg),
        Err(e) => eprintln!("✗ Failed to start backend: {}", e),
    }
    
    Ok(())
}
