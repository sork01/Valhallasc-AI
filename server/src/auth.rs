//! Accounts: a game login (username + password), a site SSO login, and the characters each account owns.
//! Guests are unchanged and never touch this module. A login returns a bearer session; the client keeps it in
//! localStorage and sends it only in the `Authorization` header or the first WebSocket message, never a URL.
use crate::{
    store::{Account, AccountKind, CharacterEntry, Store},
    world::MAX_ACCOUNT_CHARACTERS,
};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier, password_hash::SaltString};
use axum::{
    Json, Router,
    extract::{ConnectInfo, State},
    http::{HeaderMap, StatusCode, header},
    response::{IntoResponse, Response},
    routing::post,
};
use serde::Deserialize;
use serde_json::{Value, json};
use std::{
    collections::HashMap,
    net::SocketAddr,
    sync::{Arc, Mutex, OnceLock},
    time::{Duration, Instant},
};
use tokio::sync::{Semaphore, watch};

pub struct Auth {
    store: Store,
    /// The same Origin rule as the WebSocket (see main.rs origin_allowed).
    allowed_origin: Option<String>,
    /// The published world snapshot, to refuse deleting a character that is playing right now.
    snapshots: watch::Receiver<Value>,
    attempts: Mutex<HashMap<String, Vec<Instant>>>,
    http: reqwest::Client,
    sso_url: String,
    sso_gate: Semaphore,
}

pub fn router(
    store: Store,
    allowed_origin: Option<String>,
    snapshots: watch::Receiver<Value>,
) -> Router {
    let sso_url = std::env::var("VALHALLA_SSO_URL")
        .unwrap_or_else(|_| "https://gunning.se/sso/kriswe-session.php".into());
    // The site's Apache is on this host; reach it by loopback but verify the certificate for the real host name.
    let resolve = std::env::var("VALHALLA_SSO_RESOLVE").unwrap_or_else(|_| {
        if sso_url.starts_with("https://gunning.se/") {
            "127.0.0.1:443".into()
        } else {
            String::new()
        }
    });
    router_with(store, allowed_origin, snapshots, sso_url, &resolve)
}
fn router_with(
    store: Store,
    allowed_origin: Option<String>,
    snapshots: watch::Receiver<Value>,
    sso_url: String,
    resolve: &str,
) -> Router {
    let mut http = reqwest::Client::builder().timeout(Duration::from_secs(4));
    if let (Some(host), Ok(addr)) = (
        sso_url
            .split("://")
            .nth(1)
            .and_then(|r| r.split(['/', ':']).next()),
        resolve.parse::<SocketAddr>(),
    ) {
        http = http.resolve(host, addr);
    }
    let auth = Arc::new(Auth {
        store,
        allowed_origin,
        snapshots,
        attempts: Mutex::new(HashMap::new()),
        http: http.build().expect("HTTP client"),
        sso_url,
        sso_gate: Semaphore::new(8),
    });
    Router::new()
        .route("/register", post(register))
        .route("/login", post(login))
        .route("/sso", post(sso))
        .route("/session", post(session))
        .route("/logout", post(logout))
        .route("/character/delete", post(delete_character))
        .with_state(auth)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Credentials {
    username: String,
    password: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Delete {
    id: String,
}

fn fail(status: StatusCode, error: &str) -> Response {
    (status, Json(json!({"ok":false,"error":error}))).into_response()
}
fn account_json(
    account: &Account,
    characters: &[CharacterEntry],
    session: Option<&str>,
) -> Response {
    Json(json!({
        "ok":true,
        "session":session,
        "account":{"name":account.name,"kind":match account.kind {AccountKind::Game=>"game",AccountKind::Sso=>"sso"}},
        // A game master's account has one more slot, for the administrator character.
        "max":MAX_ACCOUNT_CHARACTERS,
        "gm":account.is_gm(),
        "characters":characters.iter().map(|c| json!({"id":c.id,"look":c.look,"level":c.level,"gm":c.gm})).collect::<Vec<_>>(),
    }))
    .into_response()
}
fn broken(e: Box<dyn std::error::Error>) -> Response {
    tracing::error!(%e,"account storage failed");
    fail(
        StatusCode::INTERNAL_SERVER_ERROR,
        "Account storage is unavailable.",
    )
}

pub fn valid_username(name: &str) -> bool {
    (3..=30).contains(&name.len()) && name.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
}
/// The site SSO's rule: 8+ characters with a letter and a digit.
pub fn valid_password(password: &str) -> Result<(), &'static str> {
    if !(8..=128).contains(&password.chars().count()) {
        return Err("Passwords need 8 to 128 characters.");
    }
    if !password.chars().any(|c| c.is_alphabetic()) || !password.chars().any(|c| c.is_ascii_digit())
    {
        return Err("Passwords need at least one letter and one digit.");
    }
    Ok(())
}
fn hash_password(password: &str) -> Result<String, String> {
    let salt =
        SaltString::encode_b64(uuid::Uuid::new_v4().as_bytes()).map_err(|e| e.to_string())?;
    Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map(|h| h.to_string())
        .map_err(|e| e.to_string())
}
fn verify_password(password: &str, stored: &str) -> bool {
    PasswordHash::new(stored).is_ok_and(|h| {
        Argon2::default()
            .verify_password(password.as_bytes(), &h)
            .is_ok()
    })
}
/// Checked for unknown usernames too, so a login takes as long whether or not the account exists.
fn dummy_hash() -> &'static str {
    static HASH: OnceLock<String> = OnceLock::new();
    HASH.get_or_init(|| hash_password("not-a-real-password-0").unwrap_or_default())
}

impl Auth {
    fn origin_ok(&self, headers: &HeaderMap) -> bool {
        crate::origin_allowed(headers, self.allowed_origin.as_deref())
    }
    fn blocked(&self, key: &str, max: usize, window: Duration) -> bool {
        let mut all = self.attempts.lock().unwrap_or_else(|e| e.into_inner());
        let Some(list) = all.get_mut(key) else {
            return false;
        };
        list.retain(|t| t.elapsed() < window);
        list.len() >= max
    }
    fn record(&self, key: &str) {
        let mut all = self.attempts.lock().unwrap_or_else(|e| e.into_inner());
        if all.len() > 10_000 {
            all.retain(|_, l| l.iter().any(|t| t.elapsed() < Duration::from_secs(3600)));
        }
        all.entry(key.to_owned()).or_default().push(Instant::now());
    }
    /// The account behind `Authorization: Bearer <session>`.
    fn bearer(&self, headers: &HeaderMap) -> Result<(String, Account), Box<Response>> {
        let token = headers
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.strip_prefix("Bearer "))
            .unwrap_or_default();
        match self.store.session_account(token) {
            Ok(Some(account)) => Ok((token.to_owned(), account)),
            Ok(None) => Err(Box::new(fail(
                StatusCode::UNAUTHORIZED,
                "Your login expired. Please sign in again.",
            ))),
            Err(e) => Err(Box::new(broken(e))),
        }
    }
    fn signed_in(&self, account: &Account) -> Response {
        let session = self.store.new_session(&account.id);
        let characters = self.store.account_characters(&account.id);
        match (session, characters) {
            (Ok(session), Ok(characters)) => account_json(account, &characters, Some(&session)),
            (Err(e), _) | (_, Err(e)) => broken(e),
        }
    }
    /// The site SSO user for the browser's `sso_session` cookie, as Tremor asks it: the SSO's own session check.
    async fn sso_user(&self, headers: &HeaderMap) -> Option<String> {
        let sid = headers
            .get(header::COOKIE)?
            .to_str()
            .ok()?
            .split(';')
            .find_map(|part| part.trim().strip_prefix("sso_session="))?
            .to_owned();
        if !(8..=200).contains(&sid.len())
            || !sid
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b',' || b == b'-')
        {
            return None;
        }
        let _permit = self.sso_gate.try_acquire().ok()?;
        let response = self
            .http
            .get(&self.sso_url)
            .header(header::COOKIE, format!("sso_session={sid}"))
            .header(header::ACCEPT, "application/json")
            .send()
            .await
            .map_err(|e| tracing::warn!(%e, "SSO check failed"))
            .ok()?;
        if !response.status().is_success() {
            return None;
        }
        let body: Value = response.json().await.ok()?;
        let name = body["username"].as_str()?;
        (body["authenticated"] == true && valid_username(name)).then(|| name.to_owned())
    }
}

/// The last X-Forwarded-For entry is the one Apache appended, so it is the real client; direct connections use the socket.
fn client_ip(headers: &HeaderMap, peer: SocketAddr) -> String {
    headers
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.rsplit(',').next())
        .map(|v| v.trim().to_owned())
        .filter(|v| !v.is_empty() && v.len() < 64)
        .unwrap_or_else(|| peer.ip().to_string())
}

async fn register(
    State(auth): State<Arc<Auth>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    Json(body): Json<Credentials>,
) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    let ip = format!("register:{}", client_ip(&headers, peer));
    if auth.blocked(&ip, 5, Duration::from_secs(3600)) {
        return fail(
            StatusCode::TOO_MANY_REQUESTS,
            "Too many new accounts from here. Try again later.",
        );
    }
    if !valid_username(&body.username) {
        return fail(
            StatusCode::BAD_REQUEST,
            "Usernames are 3 to 30 letters, digits or underscores.",
        );
    }
    if let Err(why) = valid_password(&body.password) {
        return fail(StatusCode::BAD_REQUEST, why);
    }
    auth.record(&ip);
    let password = body.password;
    let Ok(Ok(hashed)) = tokio::task::spawn_blocking(move || hash_password(&password)).await else {
        return fail(
            StatusCode::INTERNAL_SERVER_ERROR,
            "Could not store that password.",
        );
    };
    match auth.store.create_account(&body.username, &hashed) {
        Ok(Some(account)) => auth.signed_in(&account),
        Ok(None) => fail(StatusCode::CONFLICT, "That username is taken."),
        Err(e) => broken(e),
    }
}

async fn login(
    State(auth): State<Arc<Auth>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
    Json(body): Json<Credentials>,
) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    // Only failures count: 5 per address per 5 minutes, 10 per account per 15 minutes.
    let ip = format!("login:{}", client_ip(&headers, peer));
    let user = format!("login-user:{}", body.username.to_lowercase());
    if auth.blocked(&ip, 5, Duration::from_secs(300))
        || auth.blocked(&user, 10, Duration::from_secs(900))
    {
        return fail(
            StatusCode::TOO_MANY_REQUESTS,
            "Too many failed logins. Wait a few minutes.",
        );
    }
    let found = match auth.store.game_account(&body.username) {
        Ok(found) => found,
        Err(e) => return broken(e),
    };
    let (account, stored) = match found {
        Some((account, stored)) => (Some(account), stored),
        None => (None, dummy_hash().to_owned()),
    };
    let password = body.password;
    let matches = tokio::task::spawn_blocking(move || verify_password(&password, &stored))
        .await
        .unwrap_or(false);
    match account {
        Some(account) if matches => auth.signed_in(&account),
        _ => {
            auth.record(&ip);
            auth.record(&user);
            fail(StatusCode::UNAUTHORIZED, "Wrong username or password.")
        }
    }
}

async fn sso(
    State(auth): State<Arc<Auth>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    headers: HeaderMap,
) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    let ip = format!("sso:{}", client_ip(&headers, peer));
    if auth.blocked(&ip, 30, Duration::from_secs(300)) {
        return fail(
            StatusCode::TOO_MANY_REQUESTS,
            "Too many attempts. Wait a few minutes.",
        );
    }
    auth.record(&ip);
    let Some(name) = auth.sso_user(&headers).await else {
        return fail(
            StatusCode::UNAUTHORIZED,
            "You are not signed in to gunning.se.",
        );
    };
    match auth.store.sso_account(&name) {
        Ok(account) => auth.signed_in(&account),
        Err(e) => broken(e),
    }
}

/// Validates a stored session and returns the account and its characters (no new session).
async fn session(State(auth): State<Arc<Auth>>, headers: HeaderMap) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    let (_, account) = match auth.bearer(&headers) {
        Ok(found) => found,
        Err(response) => return *response,
    };
    match auth.store.account_characters(&account.id) {
        Ok(characters) => account_json(&account, &characters, None),
        Err(e) => broken(e),
    }
}

async fn logout(State(auth): State<Arc<Auth>>, headers: HeaderMap) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    let (token, _) = match auth.bearer(&headers) {
        Ok(found) => found,
        Err(response) => return *response,
    };
    match auth.store.end_session(&token) {
        Ok(()) => Json(json!({"ok":true})).into_response(),
        Err(e) => broken(e),
    }
}

async fn delete_character(
    State(auth): State<Arc<Auth>>,
    headers: HeaderMap,
    Json(body): Json<Delete>,
) -> Response {
    if !auth.origin_ok(&headers) {
        return fail(StatusCode::FORBIDDEN, "Origin refused.");
    }
    let (_, account) = match auth.bearer(&headers) {
        Ok(found) => found,
        Err(response) => return *response,
    };
    let playing = auth.snapshots.borrow()["zones"]
        .as_array()
        .is_some_and(|zones| {
            zones.iter().any(|z| {
                z["players"]
                    .as_array()
                    .is_some_and(|ps| ps.iter().any(|p| p["id"] == body.id.as_str()))
            })
        });
    if playing {
        return fail(
            StatusCode::CONFLICT,
            "That character is in the world right now. Leave first.",
        );
    }
    match auth.store.delete_account_character(&account.id, &body.id) {
        Ok(true) => match auth.store.account_characters(&account.id) {
            Ok(characters) => account_json(&account, &characters, None),
            Err(e) => broken(e),
        },
        Ok(false) => fail(StatusCode::NOT_FOUND, "No such character on your account."),
        Err(e) => broken(e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{body::Body, http::Request};
    use tower::ServiceExt;

    fn fresh() -> (Router, Store, watch::Sender<Value>) {
        let store = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (tx, rx) = watch::channel(json!({"zones":[]}));
        (router(store.clone(), None, rx), store, tx)
    }
    async fn call(
        app: &Router,
        path: &str,
        body: Value,
        extra: &[(&str, &str)],
    ) -> (StatusCode, Value) {
        let mut request = Request::post(path)
            .header("content-type", "application/json")
            .extension(ConnectInfo(SocketAddr::from(([127, 0, 0, 1], 5000))));
        for (k, v) in extra {
            request = request.header(*k, *v);
        }
        let response = app
            .clone()
            .oneshot(request.body(Body::from(body.to_string())).unwrap())
            .await
            .unwrap();
        let status = response.status();
        let bytes = axum::body::to_bytes(response.into_body(), 1 << 20)
            .await
            .unwrap();
        (
            status,
            serde_json::from_slice(&bytes).unwrap_or(Value::Null),
        )
    }

    /// A stand-in for the site's session check on a local port: one known cookie, one answer per path.
    async fn fake_sso() -> String {
        use axum::routing::get;
        let app = Router::new()
            .route(
                "/ok",
                get(|headers: HeaderMap| async move {
                    let cookie = headers
                        .get("cookie")
                        .and_then(|v| v.to_str().ok())
                        .unwrap_or("");
                    if cookie == "sso_session=goodsession123" {
                        Json(json!({"authenticated":true,"username":"Sso_Tester"})).into_response()
                    } else {
                        (
                            StatusCode::UNAUTHORIZED,
                            Json(json!({"authenticated":false})),
                        )
                            .into_response()
                    }
                }),
            )
            .route(
                "/odd",
                get(|| async { Json(json!({"authenticated":true,"username":"has space"})) }),
            )
            .route(
                "/no",
                get(|| async { Json(json!({"authenticated":false,"username":"Sork"})) }),
            );
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        tokio::spawn(async move { axum::serve(listener, app).await.unwrap() });
        base
    }

    #[tokio::test]
    async fn sso_signs_in_the_site_user_only_for_a_valid_site_session() {
        let base = fake_sso().await;
        let store = Store::open(std::path::Path::new(":memory:")).unwrap();
        let (_tx, rx) = watch::channel(json!({"zones":[]}));
        let app = router_with(store.clone(), None, rx.clone(), format!("{base}/ok"), "");
        let (status, body) = call(
            &app,
            "/sso",
            json!(null),
            &[("cookie", "theme=dark; sso_session=goodsession123")],
        )
        .await;
        assert_eq!(status, StatusCode::OK, "{body}");
        assert_eq!(
            (
                body["account"]["name"].as_str(),
                body["account"]["kind"].as_str()
            ),
            (Some("Sso_Tester"), Some("sso"))
        );
        let first = store
            .session_account(body["session"].as_str().unwrap())
            .unwrap()
            .unwrap();
        // The same site user is the same account next time.
        let (_, again) = call(
            &app,
            "/sso",
            json!(null),
            &[("cookie", "sso_session=goodsession123")],
        )
        .await;
        assert_eq!(
            store
                .session_account(again["session"].as_str().unwrap())
                .unwrap()
                .unwrap()
                .id,
            first.id
        );
        for cookie in [
            "sso_session=forgedforged123",
            "sso_session=",
            "other=1",
            "sso_session=bad value;x",
        ] {
            let (status, _) = call(&app, "/sso", json!(null), &[("cookie", cookie)]).await;
            assert_eq!(status, StatusCode::UNAUTHORIZED, "{cookie}");
        }
        let (status, _) = call(&app, "/sso", json!(null), &[]).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED);
        // A site answer that is not a plain user name, or that says "not authenticated", signs nobody in.
        for path in ["odd", "no"] {
            let app = router_with(
                store.clone(),
                None,
                rx.clone(),
                format!("{base}/{path}"),
                "",
            );
            let (status, _) = call(
                &app,
                "/sso",
                json!(null),
                &[("cookie", "sso_session=goodsession123")],
            )
            .await;
            assert_eq!(status, StatusCode::UNAUTHORIZED, "{path}");
        }
        // An unreachable site is a refusal, not a crash.
        let dead = router_with(store, None, rx, "http://127.0.0.1:1/x".into(), "");
        let (status, _) = call(
            &dead,
            "/sso",
            json!(null),
            &[("cookie", "sso_session=goodsession123")],
        )
        .await;
        assert_eq!(status, StatusCode::UNAUTHORIZED);
    }

    #[test]
    fn username_and_password_rules() {
        assert!(valid_username("Sork_01"));
        assert!(!valid_username("ab"));
        assert!(!valid_username("has space"));
        assert!(!valid_username("sso:Sork"));
        assert!(!valid_username(&"a".repeat(31)));
        assert!(valid_password("hunter22").is_ok());
        assert!(valid_password("short1").is_err());
        assert!(valid_password("allletters").is_err());
        assert!(valid_password("12345678").is_err());
    }

    #[test]
    fn passwords_are_hashed_and_verified() {
        let hashed = hash_password("hunter22x").unwrap();
        assert!(!hashed.contains("hunter22x"));
        assert!(verify_password("hunter22x", &hashed));
        assert!(!verify_password("hunter22y", &hashed));
        assert!(!verify_password("hunter22x", "garbage"));
        assert_ne!(hashed, hash_password("hunter22x").unwrap());
    }

    #[test]
    fn the_client_address_is_apaches_entry() {
        let peer = SocketAddr::from(([172, 18, 0, 9], 4000));
        let mut h = HeaderMap::new();
        assert_eq!(client_ip(&h, peer), "172.18.0.9");
        h.insert("x-forwarded-for", "6.6.6.6, 203.0.113.7".parse().unwrap());
        assert_eq!(client_ip(&h, peer), "203.0.113.7");
    }

    #[tokio::test]
    async fn register_login_session_and_logout() {
        let (app, store, _tx) = fresh();
        let creds = json!({"username":"Sork_One","password":"hunter22x"});
        let (status, body) = call(&app, "/register", creds.clone(), &[]).await;
        assert_eq!(status, StatusCode::OK, "{body}");
        let session = body["session"].as_str().unwrap().to_owned();
        assert_eq!(body["account"]["name"], "Sork_One");
        assert_eq!(body["account"]["kind"], "game");
        assert_eq!(body["characters"], json!([]));
        // Names are unique without case; the password is never echoed or stored in the clear.
        let (status, _) = call(
            &app,
            "/register",
            json!({"username":"sork_one","password":"another99"}),
            &[],
        )
        .await;
        assert_eq!(status, StatusCode::CONFLICT);
        let stored: String = store
            .conn()
            .query_row("SELECT pw_hash FROM accounts", [], |r| r.get(0))
            .unwrap();
        assert!(stored.starts_with("$argon2"));
        let (status, body) = call(&app, "/login", creds, &[]).await;
        assert_eq!(status, StatusCode::OK);
        assert_ne!(body["session"], session.as_str());
        let bearer = format!("Bearer {session}");
        let (status, body) =
            call(&app, "/session", json!(null), &[("authorization", &bearer)]).await;
        assert_eq!(status, StatusCode::OK, "{body}");
        assert_eq!(body["session"], Value::Null);
        let (status, _) = call(&app, "/logout", json!(null), &[("authorization", &bearer)]).await;
        assert_eq!(status, StatusCode::OK);
        let (status, _) = call(&app, "/session", json!(null), &[("authorization", &bearer)]).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED);
        let (status, _) = call(&app, "/session", json!(null), &[]).await;
        assert_eq!(status, StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn bad_credentials_are_refused_and_rate_limited() {
        let (app, _store, _tx) = fresh();
        call(
            &app,
            "/register",
            json!({"username":"Sork_One","password":"hunter22x"}),
            &[],
        )
        .await;
        for _ in 0..5 {
            let (status, body) = call(
                &app,
                "/login",
                json!({"username":"Sork_One","password":"wrong-pass1"}),
                &[],
            )
            .await;
            assert_eq!(status, StatusCode::UNAUTHORIZED);
            assert_eq!(body["error"], "Wrong username or password.");
        }
        // The sixth attempt from this address is refused even with the right password.
        let (status, _) = call(
            &app,
            "/login",
            json!({"username":"Sork_One","password":"hunter22x"}),
            &[],
        )
        .await;
        assert_eq!(status, StatusCode::TOO_MANY_REQUESTS);
        // An unknown user fails with the same message as a wrong password.
        let (app, _store, _tx) = fresh();
        let (status, body) = call(
            &app,
            "/login",
            json!({"username":"nobody_x","password":"hunter22x"}),
            &[],
        )
        .await;
        assert_eq!(
            (status, body["error"].as_str()),
            (
                StatusCode::UNAUTHORIZED,
                Some("Wrong username or password.")
            )
        );
        let (status, _) = call(
            &app,
            "/register",
            json!({"username":"x","password":"hunter22x"}),
            &[],
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
        let (status, _) = call(
            &app,
            "/register",
            json!({"username":"Valid_Name","password":"weak"}),
            &[],
        )
        .await;
        assert_eq!(status, StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn other_origins_are_refused() {
        let (app, _store, _tx) = fresh();
        let creds = json!({"username":"Sork_One","password":"hunter22x"});
        let (status, _) = call(
            &app,
            "/register",
            creds.clone(),
            &[("host", "gunning.se"), ("origin", "https://evil.example")],
        )
        .await;
        assert_eq!(status, StatusCode::FORBIDDEN);
        let (status, _) = call(
            &app,
            "/register",
            creds,
            &[("host", "gunning.se"), ("origin", "https://gunning.se")],
        )
        .await;
        assert_eq!(status, StatusCode::OK);
    }

    #[tokio::test]
    async fn characters_belong_to_one_account_and_are_deleted_by_it() {
        let (app, store, tx) = fresh();
        let (_, a) = call(
            &app,
            "/register",
            json!({"username":"Ann_One","password":"hunter22x"}),
            &[],
        )
        .await;
        let (_, b) = call(
            &app,
            "/register",
            json!({"username":"Bob_One","password":"hunter22x"}),
            &[],
        )
        .await;
        let account = |body: &Value| {
            store
                .session_account(body["session"].as_str().unwrap())
                .unwrap()
                .unwrap()
        };
        let (ann, bob) = (account(&a), account(&b));
        let (c, _) = store
            .create_for(
                Some(&ann.id),
                crate::model::Look::default(),
                Default::default(),
            )
            .unwrap();
        assert!(store.load_for_account(&ann.id, &c.id).unwrap().is_some());
        assert!(store.load_for_account(&bob.id, &c.id).unwrap().is_none());
        let abearer = format!("Bearer {}", a["session"].as_str().unwrap());
        let bbearer = format!("Bearer {}", b["session"].as_str().unwrap());
        let (_, listed) = call(
            &app,
            "/session",
            json!(null),
            &[("authorization", &abearer)],
        )
        .await;
        assert_eq!(listed["characters"][0]["id"], c.id.as_str());
        assert_eq!(listed["characters"][0]["level"], 1);
        assert_eq!(listed["max"], MAX_ACCOUNT_CHARACTERS);
        // Another account can neither delete it nor see it.
        let (status, _) = call(
            &app,
            "/character/delete",
            json!({"id":c.id}),
            &[("authorization", &bbearer)],
        )
        .await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        // Not while it is in the world.
        tx.send_replace(json!({"zones":[{"players":[{"id":c.id}]}]}));
        let (status, _) = call(
            &app,
            "/character/delete",
            json!({"id":c.id}),
            &[("authorization", &abearer)],
        )
        .await;
        assert_eq!(status, StatusCode::CONFLICT);
        tx.send_replace(json!({"zones":[]}));
        let (status, left) = call(
            &app,
            "/character/delete",
            json!({"id":c.id}),
            &[("authorization", &abearer)],
        )
        .await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(left["characters"], json!([]));
        assert!(store.load_for_account(&ann.id, &c.id).unwrap().is_none());
    }

    #[test]
    fn account_characters_cannot_be_loaded_by_key_and_guests_stay_separate() {
        let store = Store::open(std::path::Path::new(":memory:")).unwrap();
        let account = store.sso_account("Sork").unwrap();
        assert_eq!(store.sso_account("sork").unwrap().id, account.id);
        let (_, key) = store
            .create_for(
                Some(&account.id),
                crate::model::Look::default(),
                Default::default(),
            )
            .unwrap();
        assert!(store.load(&key).unwrap().is_none());
        let (guest, guest_key) = store
            .create(crate::model::Look::default(), Default::default())
            .unwrap();
        assert!(store.load(&guest_key).unwrap().is_some());
        assert!(
            store
                .load_for_account(&account.id, &guest.id)
                .unwrap()
                .is_none()
        );
        assert_eq!(store.account_character_count(&account.id).unwrap(), 1);
        // A site account and a game account of the same name are different accounts.
        let game = store.create_account("Sork", "x").unwrap().unwrap();
        assert_ne!(game.id, account.id);
    }

    #[test]
    fn sessions_expire_and_renew() {
        let store = Store::open(std::path::Path::new(":memory:")).unwrap();
        let account = store.sso_account("Sork").unwrap();
        let token = store.new_session(&account.id).unwrap();
        assert_eq!(
            store.session_account(&token).unwrap().unwrap().id,
            account.id
        );
        assert!(store.session_account(&"0".repeat(64)).unwrap().is_none());
        assert!(store.session_account("short").unwrap().is_none());
        // Used after more than a day: renewed. Past its end: refused.
        store
            .conn()
            .execute(
                "UPDATE sessions SET expires=?1",
                [crate::store::unix_now() + 3600],
            )
            .unwrap();
        assert!(store.session_account(&token).unwrap().is_some());
        let renewed: i64 = store
            .conn()
            .query_row("SELECT expires FROM sessions", [], |r| r.get(0))
            .unwrap();
        assert!(renewed > crate::store::unix_now() + 29 * 86_400);
        store
            .conn()
            .execute(
                "UPDATE sessions SET expires=?1",
                [crate::store::unix_now() - 1],
            )
            .unwrap();
        assert!(store.session_account(&token).unwrap().is_none());
    }
}
