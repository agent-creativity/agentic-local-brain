use std::sync::Mutex;
use tauri_plugin_shell::process::CommandChild;

pub struct SidecarState {
    pub child: Mutex<Option<CommandChild>>,
    pub port: u16,
}

impl SidecarState {
    pub fn new(port: u16) -> Self {
        Self {
            child: Mutex::new(None),
            port,
        }
    }
}

#[tauri::command]
pub fn get_server_port(state: tauri::State<'_, SidecarState>) -> u16 {
    state.port
}

#[tauri::command]
pub async fn get_server_status(state: tauri::State<'_, SidecarState>) -> Result<String, String> {
    let port = state.port;
    let url = format!("http://127.0.0.1:{}/health", port);

    match reqwest::get(&url).await {
        Ok(resp) if resp.status().is_success() => Ok("running".to_string()),
        _ => {
            let child = state.child.lock().unwrap();
            if child.is_some() {
                Ok("starting".to_string())
            } else {
                Ok("stopped".to_string())
            }
        }
    }
}
