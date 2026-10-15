//! Optional, best-effort Gotify login notices. The world only does a bounded try_send.
use crate::model::{Character, Class};
use std::{
    collections::HashMap,
    time::{Duration, Instant},
};
use tokio::sync::mpsc;

const COOLDOWN: Duration = Duration::from_secs(30 * 60);
const QUEUE_SIZE: usize = 32;
const REQUEST_TIMEOUT: Duration = Duration::from_secs(2);

#[derive(Clone)]
pub struct LoginNotice {
    pub id: String,
    pub name: String,
    pub class: Class,
    pub level: u32,
    pub zone: String,
}

pub fn eligible(
    character: &Character,
    test_commands: bool,
    god_mode: bool,
    start_level: u32,
) -> bool {
    !character.gm && !test_commands && !god_mode && start_level == 1
}

fn clean(value: &str) -> String {
    value.chars().filter(|c| !c.is_control()).take(40).collect()
}

fn body(notice: &LoginNotice) -> serde_json::Value {
    serde_json::json!({
        "title": "🎮 Valhalla login",
        "message": format!("{} · {:?} · level {} · {}", clean(&notice.name), notice.class, notice.level, clean(&notice.zone)),
        "priority": 2,
    })
}

pub fn start_from_env() -> Option<mpsc::Sender<LoginNotice>> {
    let url = std::env::var("VALHALLA_GOTIFY_URL").ok()?;
    let token = std::env::var("VALHALLA_GOTIFY_TOKEN").ok()?;
    start(url, token)
}

pub(crate) fn start(url: String, token: String) -> Option<mpsc::Sender<LoginNotice>> {
    let mut endpoint = reqwest::Url::parse(url.trim_end_matches('/')).ok()?;
    if !matches!(endpoint.scheme(), "http" | "https") || token.is_empty() {
        tracing::warn!("Gotify login notifications disabled: invalid configuration");
        return None;
    }
    endpoint.path_segments_mut().ok()?.push("message");
    let token = reqwest::header::HeaderValue::from_str(&token).ok()?;
    let client = reqwest::Client::builder()
        .timeout(REQUEST_TIMEOUT)
        .build()
        .ok()?;
    let (tx, mut rx) = mpsc::channel::<LoginNotice>(QUEUE_SIZE);
    tokio::spawn(async move {
        let mut sent = HashMap::<String, Instant>::new();
        let mut failed = false;
        while let Some(notice) = rx.recv().await {
            let now = Instant::now();
            sent.retain(|_, when| now.duration_since(*when) < COOLDOWN);
            if sent.contains_key(&notice.id) {
                continue;
            }
            sent.insert(notice.id.clone(), now);
            let result = client
                .post(endpoint.clone())
                .header("X-Gotify-Key", token.clone())
                .json(&body(&notice))
                .send()
                .await;
            let okay = result.is_ok_and(|response| response.status().is_success());
            if okay {
                failed = false;
            } else if !failed {
                // Do not format reqwest errors: they may contain the endpoint or credentials.
                tracing::warn!(
                    "Gotify login notification failed; later failures are suppressed until recovery"
                );
                failed = true;
            }
        }
    });
    Some(tx)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{Json, Router, extract::State, http::HeaderMap, routing::post};
    use std::sync::Arc;
    use tokio::sync::Mutex;

    #[test]
    fn message_is_plain_and_bounded() {
        let n = LoginNotice {
            id: "a".into(),
            name: "A\nB\r".into(),
            class: Class::Mage,
            level: 7,
            zone: "The\nCrags".into(),
        };
        let msg = body(&n);
        assert_eq!(msg["message"], "AB · Mage · level 7 · TheCrags");
        assert_eq!(msg["priority"], 2);
        assert_eq!(clean(&"x".repeat(100)).len(), 40);
        let mut character = Character::mercenary(Class::Mage, 1, "A");
        assert!(eligible(&character, false, false, 1));
        character.gm = true;
        assert!(!eligible(&character, false, false, 1));
        character.gm = false;
        assert!(!eligible(&character, true, false, 1));
        assert!(!eligible(&character, false, true, 1));
        assert!(!eligible(&character, false, false, 20));
    }

    #[tokio::test]
    async fn fake_gotify_receives_one_push_per_cooldown() {
        type Received = Arc<Mutex<Vec<serde_json::Value>>>;
        async fn receive(
            State(messages): State<Received>,
            headers: HeaderMap,
            Json(value): Json<serde_json::Value>,
        ) {
            assert_eq!(headers["X-Gotify-Key"], "local-test-token");
            messages.lock().await.push(value);
        }
        let messages: Received = Arc::new(Mutex::new(vec![]));
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(
            axum::serve(
                listener,
                Router::new()
                    .route("/message", post(receive))
                    .with_state(messages.clone()),
            )
            .into_future(),
        );
        let tx = start(format!("http://{addr}"), "local-test-token".into()).unwrap();
        let notice = LoginNotice {
            id: "hero".into(),
            name: "Aria".into(),
            class: Class::Hunter,
            level: 9,
            zone: "Meadow".into(),
        };
        tx.try_send(notice.clone()).unwrap();
        tx.try_send(notice).unwrap();
        tokio::time::timeout(Duration::from_secs(2), async {
            while messages.lock().await.is_empty() {
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        })
        .await
        .unwrap();
        tokio::time::sleep(Duration::from_millis(50)).await;
        let rows = messages.lock().await;
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["message"], "Aria · Hunter · level 9 · Meadow");
        assert!(!rows[0].to_string().contains("local-test-token"));
    }

    #[tokio::test]
    async fn unreachable_endpoint_never_blocks_queue() {
        let tx = start("http://127.0.0.1:1".into(), "local-test-token".into()).unwrap();
        let start = Instant::now();
        for n in 0..100 {
            let _ = tx.try_send(LoginNotice {
                id: n.to_string(),
                name: "A".into(),
                class: Class::Mage,
                level: 1,
                zone: "Meadow".into(),
            });
        }
        assert!(start.elapsed() < Duration::from_millis(100));
    }

    #[tokio::test]
    async fn slow_endpoint_does_not_block_queue() {
        async fn slow() {
            tokio::time::sleep(Duration::from_secs(3)).await;
        }
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(
            axum::serve(listener, Router::new().route("/message", post(slow))).into_future(),
        );
        let tx = start(format!("http://{addr}"), "local-test-token".into()).unwrap();
        let start = Instant::now();
        tx.try_send(LoginNotice {
            id: "slow".into(),
            name: "A".into(),
            class: Class::Mage,
            level: 1,
            zone: "Meadow".into(),
        })
        .unwrap();
        assert!(start.elapsed() < Duration::from_millis(100));
    }
}
