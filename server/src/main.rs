#![recursion_limit = "256"]
mod auth;
mod cathedral;
mod items;
mod model;
mod skills;
mod store;
mod world;

use axum::{
    Router,
    extract::{
        Request, State, WebSocketUpgrade,
        ws::{Message, WebSocket},
    },
    http::{HeaderMap, HeaderValue, StatusCode, header},
    middleware::{self, Next},
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
use world::{Command, Identity};

#[derive(Clone)]
struct App {
    commands: mpsc::Sender<Command>,
    snapshots: watch::Receiver<Value>,
    shutdown: watch::Receiver<bool>,
    slots: Arc<Semaphore>,
    sessions: Arc<AtomicU64>,
    allowed_origin: Option<String>,
    store: store::Store,
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
    let accounts = store.clone();
    // Each enemy's level is its kind's default plus or minus this many levels (0 pins every enemy to its default).
    let spread = std::env::var("VALHALLA_LEVEL_SPREAD")
        .ok()
        .and_then(|v| v.parse::<i32>().ok())
        .map_or(world::LEVEL_SPREAD, |v| v.clamp(0, 5));
    let mut world = world::World::with_level_spread(store, spread);
    // Shared outdoor maps and cities may host temporary autonomous adventurers. Test servers leave this off unless
    // they explicitly exercise the feature; private dungeon copies never receive them.
    world.ambient_enabled = std::env::var("VALHALLA_AMBIENT_PLAYERS").is_ok_and(|v| v == "1");
    // For automated tests only: players take no damage. Never set on the public service.
    world.god_mode = std::env::var("VALHALLA_GOD_MODE").is_ok_and(|v| v == "1");
    if world.god_mode {
        tracing::warn!("VALHALLA_GOD_MODE is on: players cannot be hurt");
    }
    // For automated tests only: new characters start at this level (1-100), so skills can be driven for real.
    world.start_level = std::env::var("VALHALLA_START_LEVEL")
        .ok()
        .and_then(|v| v.parse::<u32>().ok())
        .map_or(1, |v| v.clamp(1, 100));
    if world.start_level > 1 {
        tracing::warn!(
            "VALHALLA_START_LEVEL={} is on: new characters start above level 1",
            world.start_level
        );
    }
    // For automated tests only: players may send `debug` shortcuts (levels, items, teleports...). Never set on the public service.
    world.test_commands = std::env::var("VALHALLA_TEST_COMMANDS").is_ok_and(|v| v == "1");
    if world.test_commands {
        tracing::warn!("VALHALLA_TEST_COMMANDS is on: players may use debug shortcuts");
    }
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
        store: accounts.clone(),
    };
    const CSP: &str = concat!(
        "default-src 'self'; script-src 'self'; ",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; ",
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; ",
        "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
    );
    let router = Router::new()
        .route("/health", get(health))
        .nest_service(
            "/api",
            auth::router(accounts, app.allowed_origin.clone(), app.snapshots.clone()),
        )
        .route("/ws", any(upgrade))
        .fallback_service(ServeDir::new(client))
        .layer(middleware::from_fn(cache_policy))
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
    axum::serve(
        listener,
        router.into_make_service_with_connect_info::<std::net::SocketAddr>(),
    )
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
        json!({"status":"ok","version":1,"tick":snapshot["tick"],"online":snapshot["humansOnline"],"visibleOnline":snapshot["online"],"capacity":MAX_PLAYERS}),
    )
}
// One zone's complete snapshot: the one listing this player, else the last zone they were in.
fn zone_view(snapshot: &Value, id: &str, zone: &mut usize) -> Option<Value> {
    let zones = snapshot["zones"].as_array()?;
    let listed = |z: &Value| {
        z["players"]
            .as_array()
            .is_some_and(|players| players.iter().any(|p| p["id"] == id))
    };
    if let Some(found) = zones.iter().position(listed) {
        *zone = found;
    }
    zones.get(*zone).cloned()
}
pub(crate) fn origin_allowed(headers: &HeaderMap, configured: Option<&str>) -> bool {
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
    let identity = match first {
        Ok(Some(Ok(Message::Text(text)))) => {
            match serde_json::from_str::<ClientMessage>(&text) {
                Ok(ClientMessage::Join {
                    version: 1,
                    token,
                    look,
                    session: None,
                    character: None,
                }) => Identity::Guest {
                    token,
                    look: look.map(|l| *l),
                },
                Ok(ClientMessage::Join {
                    version: 1,
                    token: None,
                    look,
                    session: Some(session),
                    character,
                }) => {
                    let store = app.store.clone();
                    let found = tokio::task::spawn_blocking(move || {
                        store.session_account(&session).map_err(|e| e.to_string())
                    })
                    .await
                    .map_err(|e| e.to_string())
                    .and_then(|r| r);
                    match found {
                        Ok(Some(account)) => Identity::Account {
                            gm: account.is_gm(),
                            id: account.id,
                            character,
                            look: look.map(|l| *l),
                        },
                        Ok(None) => {
                            send(&mut socket,&json!({"type":"error","fatal":true,"code":"auth","text":"Your login expired. Please sign in again."})).await;
                            return;
                        }
                        Err(e) => {
                            tracing::error!(%e,"session check failed");
                            send(&mut socket,&json!({"type":"error","fatal":true,"text":"Account storage is unavailable."})).await;
                            return;
                        }
                    }
                }
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
            identity,
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
    // Which zone's view this connection forwards: wherever its own character is listed.
    let id = welcome["id"].as_str().unwrap_or_default().to_owned();
    let mut zone = welcome["snapshot"]["players"]
        .as_array()
        .and_then(|players| players.iter().find(|p| p["id"] == id.as_str()))
        .and_then(|p| p["zone"].as_u64())
        .unwrap_or(0) as usize;
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
                    if changed.is_err(){break;}
                    let view=zone_view(&app.snapshots.borrow_and_update(),&id,&mut zone);
                    if let Some(view)=view && !send(&mut socket,&view).await{break;}
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

/// Pages, scripts and API replies are never cached, so a saved client file is live at once. The art under /assets/
/// (sprite atlases and their metadata, music) is megabytes that do not change between visits: `no-cache` lets the
/// browser keep it but makes it ask first, and ServeDir answers that with a bodiless 304 from Last-Modified. A
/// regenerated file is therefore still picked up on the next load. (Restoring an older file keeps its older mtime and
/// would be answered 304: `touch` it.) Errors are never cached.
async fn cache_policy(request: Request, next: Next) -> Response {
    let art = request.uri().path().starts_with("/assets/");
    let mut response = next.run(request).await;
    let cacheable =
        art && (response.status().is_success() || response.status() == StatusCode::NOT_MODIFIED);
    response.headers_mut().insert(
        header::CACHE_CONTROL,
        HeaderValue::from_static(if cacheable { "no-cache" } else { "no-store" }),
    );
    response
}

#[cfg(test)]
mod tests {
    use super::*;
    use tower::ServiceExt;

    #[tokio::test]
    async fn art_is_revalidated_while_code_and_errors_are_never_stored() {
        let dir = std::env::temp_dir().join(format!("valhalla-cache-test-{}", std::process::id()));
        std::fs::create_dir_all(dir.join("assets")).unwrap();
        std::fs::write(dir.join("assets/a.png"), b"png").unwrap();
        std::fs::write(dir.join("game.js"), b"js").unwrap();
        let app = Router::new()
            .route("/health", get(|| async { "ok" }))
            .fallback_service(ServeDir::new(&dir))
            .layer(middleware::from_fn(cache_policy));
        let get_path = |path: &str, since: Option<&str>| {
            let mut request = Request::builder().uri(path);
            if let Some(since) = since {
                request = request.header(header::IF_MODIFIED_SINCE, since);
            }
            app.clone()
                .oneshot(request.body(axum::body::Body::empty()).unwrap())
        };
        let cache = |r: &Response| {
            r.headers()[header::CACHE_CONTROL]
                .to_str()
                .unwrap()
                .to_owned()
        };
        let art = get_path("/assets/a.png", None).await.unwrap();
        assert_eq!(
            (art.status(), cache(&art).as_str()),
            (StatusCode::OK, "no-cache")
        );
        // The browser's revalidation is a 304 with no body, and stays storable.
        let stamp = art.headers()[header::LAST_MODIFIED]
            .to_str()
            .unwrap()
            .to_owned();
        let again = get_path("/assets/a.png", Some(&stamp)).await.unwrap();
        assert_eq!(
            (again.status(), cache(&again).as_str()),
            (StatusCode::NOT_MODIFIED, "no-cache")
        );
        for (path, status) in [
            ("/game.js", StatusCode::OK),
            ("/health", StatusCode::OK),
            ("/assets/missing.png", StatusCode::NOT_FOUND),
        ] {
            let r = get_path(path, None).await.unwrap();
            assert_eq!(
                (r.status(), cache(&r).as_str()),
                (status, "no-store"),
                "{path}"
            );
        }
        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn each_connection_forwards_only_the_zone_that_lists_its_character() {
        let view = |zone: usize, ids: &[&str]| json!({"zone": zone, "players": ids.iter().map(|id| json!({"id": id})).collect::<Vec<_>>()});
        let snapshot =
            json!({"tick": 7, "online": 3, "zones": [view(0, &["a", "b"]), view(1, &["c"])]});
        let mut zone = 0;
        assert_eq!(zone_view(&snapshot, "c", &mut zone).unwrap()["zone"], 1);
        assert_eq!(zone, 1);
        assert_eq!(zone_view(&snapshot, "a", &mut zone).unwrap()["zone"], 0);
        // A character missing from every view (leaving) keeps the zone it had.
        zone = 1;
        assert_eq!(zone_view(&snapshot, "gone", &mut zone).unwrap()["zone"], 1);
        assert!(zone_view(&json!({"tick": 1}), "a", &mut zone).is_none());
    }

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
