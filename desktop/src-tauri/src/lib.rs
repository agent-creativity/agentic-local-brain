mod sidecar;
mod tray;

use sidecar::SidecarState;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let port: u16 = 11201;

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(SidecarState::new(port))
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            tray::setup_tray(app)?;

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                start_sidecar(&app_handle, port).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            sidecar::get_server_port,
            sidecar::get_server_status,
            send_notification,
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let app = window.app_handle();
                if let Some(state) = app.try_state::<SidecarState>() {
                    let mut child = state.child.lock().unwrap();
                    if let Some(c) = child.take() {
                        let _ = c.kill();
                        log::info!("Sidecar process killed on window close");
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn send_notification(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())
}

async fn start_sidecar(app: &tauri::AppHandle, port: u16) {
    use tauri_plugin_shell::ShellExt;

    let sidecar_cmd = app
        .shell()
        .sidecar("localbrain")
        .expect("failed to create sidecar command")
        .args(["web", "--host", "127.0.0.1", "--port", &port.to_string()]);

    match sidecar_cmd.spawn() {
        Ok((mut rx, child)) => {
            log::info!("Sidecar started on port {}", port);

            if let Some(state) = app.try_state::<SidecarState>() {
                *state.child.lock().unwrap() = Some(child);
            }

            while let Some(event) = rx.recv().await {
                use tauri_plugin_shell::process::CommandEvent;
                match event {
                    CommandEvent::Stdout(line) => {
                        log::info!("[sidecar] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Stderr(line) => {
                        log::warn!("[sidecar] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Terminated(status) => {
                        log::info!("[sidecar] terminated with {:?}", status);
                        break;
                    }
                    CommandEvent::Error(err) => {
                        log::error!("[sidecar] error: {}", err);
                        break;
                    }
                    _ => {}
                }
            }
        }
        Err(e) => {
            log::error!("Failed to start sidecar: {}", e);
        }
    }
}
