//! Optional, best-effort login notices. The world only does a bounded try_send.
//!
//! Two sinks, chosen by the environment: Surv's notify endpoint (`VALHALLA_SURV_NOTIFY_URL`, optionally pinned to a local
//! address with `VALHALLA_SURV_NOTIFY_ADDR`), which pushes to Gotify with Surv's own token and also records the push in
//! Surv's alarm log; or a Gotify application directly (`VALHALLA_GOTIFY_URL` and `VALHALLA_GOTIFY_TOKEN`).
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

/// The same notice for Surv's notify endpoint, which pushes it to Gotify and logs it.
fn surv_body(notice: &LoginNotice) -> serde_json::Value {
    let mut value = body(notice);
    value["send_gotify"] = serde_json::json!(true);
    value
}

pub fn start_from_env() -> Option<mpsc::Sender<LoginNotice>> {
    if let Ok(url) = std::env::var("VALHALLA_SURV_NOTIFY_URL") {
        let pin = std::env::var("VALHALLA_SURV_NOTIFY_ADDR").ok();
        return start_surv(url, pin);
    }
    let url = std::env::var("VALHALLA_GOTIFY_URL").ok()?;
    let token = std::env::var("VALHALLA_GOTIFY_TOKEN").ok()?;
    start(url, token)
}

/// Posts to Surv's notify endpoint. `pin` ("127.0.0.1:443") sends the request to that address while the URL's host name
/// is still used for the TLS check, so a host service can reach Surv's vhost on loopback with a verified certificate.
pub(crate) fn start_surv(url: String, pin: Option<String>) -> Option<mpsc::Sender<LoginNotice>> {
    let endpoint = reqwest::Url::parse(&url).ok()?;
    if !matches!(endpoint.scheme(), "http" | "https") || endpoint.host_str().is_none() {
        tracing::warn!("Surv login notifications disabled: invalid configuration");
        return None;
    }
    let mut client = reqwest::Client::builder().timeout(REQUEST_TIMEOUT);
    if let Some(pin) = pin {
        let Ok(addr) = pin.parse::<std::net::SocketAddr>() else {
            tracing::warn!("Surv login notifications disabled: invalid address");
            return None;
        };
        client = client.resolve(endpoint.host_str()?, addr);
    }
    Some(spawn_worker(client.build().ok()?, endpoint, None))
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
    Some(spawn_worker(client, endpoint, Some(token)))
}

/// The background task shared by both sinks: one push per character per `COOLDOWN`, failures logged once.
fn spawn_worker(
    client: reqwest::Client,
    endpoint: reqwest::Url,
    token: Option<reqwest::header::HeaderValue>,
) -> mpsc::Sender<LoginNotice> {
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
            let request = client.post(endpoint.clone());
            let result = match &token {
                Some(token) => {
                    request
                        .header("X-Gotify-Key", token.clone())
                        .json(&body(&notice))
                        .send()
                        .await
                }
                None => request.json(&surv_body(&notice)).send().await,
            };
            let okay = match result {
                Ok(response) if response.status().is_success() && token.is_none() => {
                    // Surv answers 200 with {"success": false} when it refuses.
                    response
                        .json::<serde_json::Value>()
                        .await
                        .is_ok_and(|value| value["success"] == true)
                }
                Ok(response) => response.status().is_success(),
                Err(_) => false,
            };
            if okay {
                failed = false;
            } else if !failed {
                // Do not format reqwest errors: they may contain the endpoint or credentials.
                tracing::warn!(
                    "Login notification failed; later failures are suppressed until recovery"
                );
                failed = true;
            }
        }
    });
    tx
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

    fn notice(id: &str) -> LoginNotice {
        LoginNotice {
            id: id.into(),
            name: "Aria".into(),
            class: Class::Hunter,
            level: 9,
            zone: "Meadow".into(),
        }
    }

    #[tokio::test]
    async fn surv_endpoint_gets_one_push_with_gotify_flag_and_no_token() {
        type Received = Arc<Mutex<Vec<(Option<String>, serde_json::Value)>>>;
        async fn receive(
            State(messages): State<Received>,
            headers: HeaderMap,
            Json(value): Json<serde_json::Value>,
        ) -> Json<serde_json::Value> {
            let host = headers.get("host").map(|h| h.to_str().unwrap().to_owned());
            assert!(
                headers.get("X-Gotify-Key").is_none(),
                "Surv holds the token"
            );
            messages.lock().await.push((host, value));
            Json(serde_json::json!({"success": true}))
        }
        let messages: Received = Arc::new(Mutex::new(vec![]));
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(
            axum::serve(
                listener,
                Router::new()
                    .route("/surv/api.php", post(receive))
                    .with_state(messages.clone()),
            )
            .into_future(),
        );
        // The host name is not resolvable: only the pinned address can make this reach the fake.
        let tx = start_surv(
            format!(
                "http://surv.invalid:{}/surv/api.php?action=notify",
                addr.port()
            ),
            Some(addr.to_string()),
        )
        .unwrap();
        tx.try_send(notice("hero")).unwrap();
        tx.try_send(notice("hero")).unwrap();
        tokio::time::timeout(Duration::from_secs(2), async {
            while messages.lock().await.is_empty() {
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        })
        .await
        .unwrap();
        tokio::time::sleep(Duration::from_millis(50)).await;
        let rows = messages.lock().await;
        assert_eq!(rows.len(), 1, "one push per character per cooldown");
        let (host, value) = &rows[0];
        assert_eq!(
            host.as_deref(),
            Some(&*format!("surv.invalid:{}", addr.port()))
        );
        assert_eq!(value["title"], "🎮 Valhalla login");
        assert_eq!(value["message"], "Aria · Hunter · level 9 · Meadow");
        assert_eq!(value["priority"], 2);
        assert_eq!(value["send_gotify"], true);
    }

    #[tokio::test]
    async fn surv_refusal_is_a_failure_that_does_not_stop_later_pushes() {
        type Count = Arc<Mutex<usize>>;
        async fn refuse(State(count): State<Count>) -> Json<serde_json::Value> {
            let mut n = count.lock().await;
            *n += 1;
            // The first call is refused with HTTP 200, as Surv does; the second succeeds.
            Json(serde_json::json!({"success": *n > 1}))
        }
        let count: Count = Arc::new(Mutex::new(0));
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(
            axum::serve(
                listener,
                Router::new()
                    .route("/n", post(refuse))
                    .with_state(count.clone()),
            )
            .into_future(),
        );
        let tx = start_surv(format!("http://{addr}/n"), None).unwrap();
        tx.try_send(notice("a")).unwrap();
        tx.try_send(notice("b")).unwrap();
        tokio::time::timeout(Duration::from_secs(2), async {
            while *count.lock().await < 2 {
                tokio::time::sleep(Duration::from_millis(10)).await;
            }
        })
        .await
        .unwrap();
    }

    #[test]
    fn invalid_surv_configuration_is_refused() {
        assert!(start_surv("not a url".into(), None).is_none());
        assert!(start_surv("ftp://example.invalid/x".into(), None).is_none());
    }

    #[tokio::test]
    async fn invalid_pin_address_is_refused() {
        assert!(start_surv("http://surv.invalid/x".into(), Some("nonsense".into())).is_none());
    }
}
