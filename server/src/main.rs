mod model;
mod store;
mod world;

use axum::{
    Router,
    extract::{
        State, WebSocketUpgrade,
        ws::{Message, WebSocket},
    },
    http::{HeaderMap, HeaderValue, StatusCode, header},
    response::{IntoResponse, Response},
    routing::{any, get},
};
use model::{ClientMessage, MAX_PLAYERS};
use serde_json::{Value, json};
use std::{
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering},
    },
    time::{Duration, Instant},
};
use tokio::sync::{Semaphore, mpsc, oneshot, watch};
use tower_http::{services::ServeDir, set_header::SetResponseHeaderLayer};
use world::Command;

#[derive(Clone)]
struct App {
    commands: mpsc::Sender<Command>,
    snapshots: watch::Receiver<Value>,
    shutdown: watch::Receiver<bool>,
    slots: Arc<Semaphore>,
    sessions: Arc<AtomicU64>,
    allowed_origin: Option<String>,
}
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "valhalla_server=info".into()),
        )
        .init();
    let bind = std::env::var("VALHALLA_BIND").unwrap_or_else(|_| "127.0.0.1:8080".into());
    let data = std::env::var("VALHALLA_DB").unwrap_or_else(|_| "data/valhalla.sqlite".into());
    let client = std::env::var("VALHALLA_CLIENT_DIR").unwrap_or_else(|_| "client".into());
    if !std::path::Path::new(&client).join("index.html").is_file() {
        return Err(
            "Client files missing. Run from the project root or set VALHALLA_CLIENT_DIR.".into(),
        );
    }
    let store = store::Store::open(std::path::Path::new(&data))?;
    let world = world::World::new(store);
    let (tx, rx) = mpsc::channel(1024);
    let (snap_tx, snap_rx) = watch::channel(world.snapshot());
    let (shutdown_tx, shutdown_rx) = watch::channel(false);
    let app = App {
        commands: tx.clone(),
        snapshots: snap_rx,
        shutdown: shutdown_rx,
        slots: Arc::new(Semaphore::new(MAX_PLAYERS)),
        sessions: Arc::new(AtomicU64::new(1)),
        allowed_origin: std::env::var("VALHALLA_ORIGIN").ok(),
    };
    const CSP: &str = concat!(
        "default-src 'self'; script-src 'self'; ",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; ",
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; ",
        "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
    );
    let router = Router::new()
        .route("/health", get(health))
        .route("/ws", any(upgrade))
        .fallback_service(ServeDir::new(client))
        .layer(SetResponseHeaderLayer::overriding(
            header::CACHE_CONTROL,
            HeaderValue::from_static("no-store"),
        ))
        .layer(SetResponseHeaderLayer::overriding(
            header::X_CONTENT_TYPE_OPTIONS,
            HeaderValue::from_static("nosniff"),
        ))
        .layer(SetResponseHeaderLayer::overriding(
            header::CONTENT_SECURITY_POLICY,
            HeaderValue::from_static(CSP),
        ))
        .with_state(app);
    let listener = tokio::net::TcpListener::bind(&bind).await?;
    let world_task = tokio::spawn(world.run(rx, snap_tx));
    tracing::info!(address=%listener.local_addr()?,"Valhalla multiplayer server ready");
    axum::serve(listener, router)
        .with_graceful_shutdown(async move {
            shutdown_signal().await;
            shutdown_tx.send_replace(true);
            let (reply, done) = oneshot::channel();
            let _ = tx.send(Command::Shutdown { reply }).await;
            let _ = done.await;
        })
        .await?;
    world_task.await?;
    Ok(())
}
async fn shutdown_signal() {
    #[cfg(unix)]
    {
        let mut term = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("SIGTERM handler");
        tokio::select! {_=tokio::signal::ctrl_c()=>{},_=term.recv()=>{}}
    }
    #[cfg(not(unix))]
    {
        let _ = tokio::signal::ctrl_c().await;
    }
}
async fn health(State(app): State<App>) -> impl IntoResponse {
    let snapshot = app.snapshots.borrow();
    axum::Json(
        json!({"status":"ok","version":1,"tick":snapshot["tick"],"online":snapshot["online"],"capacity":MAX_PLAYERS}),
    )
}
fn origin_allowed(headers: &HeaderMap, configured: Option<&str>) -> bool {
    let Some(origin) = headers.get(header::ORIGIN) else {
        return true;
    };
    let Ok(origin) = origin.to_str() else {
        return false;
    };
    if let Some(expected) = configured {
        return origin == expected;
    }
    let Some(host) = headers.get(header::HOST).and_then(|h| h.to_str().ok()) else {
        return false;
    };
    origin == format!("http://{host}") || origin == format!("https://{host}")
}
async fn upgrade(State(app): State<App>, headers: HeaderMap, ws: WebSocketUpgrade) -> Response {
    if !origin_allowed(&headers, app.allowed_origin.as_deref()) {
        return (StatusCode::FORBIDDEN, "Origin refused").into_response();
    }
    let Ok(permit) = app.slots.clone().try_acquire_owned() else {
        return (StatusCode::SERVICE_UNAVAILABLE, "World full").into_response();
    };
    ws.max_message_size(4096)
        .max_frame_size(4096)
        .on_upgrade(move |socket| async move {
            let _permit = permit;
            connection(socket, app).await;
        })
}
async fn send(socket: &mut WebSocket, value: &Value) -> bool {
    let Ok(text) = serde_json::to_string(value) else {
        return false;
    };
    matches!(
        tokio::time::timeout(
            Duration::from_secs(2),
            socket.send(Message::Text(text.into()))
        )
        .await,
        Ok(Ok(()))
    )
}
async fn connection(mut socket: WebSocket, mut app: App) {
    let first = tokio::time::timeout(Duration::from_secs(8), socket.recv()).await;
    let (token, look) = match first {
        Ok(Some(Ok(Message::Text(text)))) => {
            match serde_json::from_str::<ClientMessage>(&text) {
                Ok(ClientMessage::Join {
                    version: 1,
                    token,
                    look,
                }) => (token, look),
                _ => {
                    send(&mut socket,&json!({"type":"error","fatal":true,"text":"Join with protocol version 1."})).await;
                    return;
                }
            }
        }
        _ => return,
    };
    let session = app.sessions.fetch_add(1, Ordering::Relaxed);
    let (peer, mut events) = mpsc::channel(128);
    let (reply, done) = oneshot::channel();
    if app
        .commands
        .send(Command::Join {
            session,
            token,
            look,
            peer,
            reply,
        })
        .await
        .is_err()
    {
        return;
    }
    let welcome = match done.await {
        Ok(Ok(welcome)) => welcome,
        Ok(Err(text)) => {
            send(
                &mut socket,
                &json!({"type":"error","fatal":true,"text":text}),
            )
            .await;
            return;
        }
        Err(_) => return,
    };
    if send(&mut socket, &welcome).await {
        let mut last_seen = Instant::now();
        let mut window = Instant::now();
        let mut messages = 0;
        let mut heartbeat = tokio::time::interval(Duration::from_secs(15));
        loop {
            tokio::select! {
                _=app.shutdown.changed()=>break,
                _=heartbeat.tick()=>{
                    if last_seen.elapsed()>Duration::from_secs(60){break;}
                    if !matches!(tokio::time::timeout(Duration::from_secs(2),socket.send(Message::Ping(vec![].into()))).await,Ok(Ok(()))){break;}
                }
                changed=app.snapshots.changed()=>{
                    if changed.is_err(){break;}let snapshot=app.snapshots.borrow_and_update().clone();
                    if !send(&mut socket,&snapshot).await{break;}
                }
                event=events.recv()=>{
                    let Some(event)=event else {break;};if !send(&mut socket,&event).await{break;}
                }
                message=socket.recv()=>{
                    let Some(Ok(message))=message else {break;};last_seen=Instant::now();
                    if window.elapsed()>=Duration::from_secs(1){messages=0;window=Instant::now();}
                    messages+=1;if messages>80{send(&mut socket,&json!({"type":"error","fatal":true,"text":"Too many messages."})).await;break;}
                    match message {
                        Message::Text(text)=>match serde_json::from_str::<ClientMessage>(&text){
                            Ok(ClientMessage::Join{..})=>break,
                            Ok(message)=>{if app.commands.try_send(Command::Message{session,message}).is_err(){break;}}
                            Err(_)=>{if !send(&mut socket,&json!({"type":"error","text":"Invalid command."})).await{break;}}
                        },
                        Message::Close(_)=>break,
                        Message::Binary(_)=>break,
                        _=>{},
                    }
                }
            }
        }
    }
    let _ = app.commands.send(Command::Leave { session }).await;
    let _ = tokio::time::timeout(Duration::from_secs(1), socket.send(Message::Close(None))).await;
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn websocket_origin_policy() {
        let mut h = HeaderMap::new();
        h.insert(header::HOST, "localhost:8080".parse().unwrap());
        h.insert(header::ORIGIN, "https://evil.example".parse().unwrap());
        assert!(!origin_allowed(&h, None));
        h.insert(header::ORIGIN, "http://localhost:8080".parse().unwrap());
        assert!(origin_allowed(&h, None));
        assert!(!origin_allowed(&h, Some("https://game.example")));
        h.insert(header::ORIGIN, "https://game.example".parse().unwrap());
        assert!(origin_allowed(&h, Some("https://game.example")));
    }
}
