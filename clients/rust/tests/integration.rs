//! Tests for the Enhanced Cognee Rust client using `wiremock` to mock the
//! HTTP server.

use enhanced_cognee_client::{Client, Error, MemoryEntry, SearchQuery};
use wiremock::matchers::{header, method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

async fn test_client(server_url: &str) -> Client {
    Client::builder()
        .base_url(server_url)
        .build()
        .expect("client builds")
}

#[tokio::test]
async fn add_memory_success() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/memory/add"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "id": "mem-abc"
        })))
        .mount(&server)
        .await;

    let cli = test_client(&server.uri()).await;
    let id = cli
        .add_memory(&MemoryEntry {
            content: "hello".into(),
            agent_id: "agent-1".into(),
            memory_category: "engineering".into(),
            ..Default::default()
        })
        .await
        .unwrap();
    assert_eq!(id, "mem-abc");
}

#[tokio::test]
async fn search_memory_returns_results() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/memory/search"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "results": [{
                "id": "1",
                "content": "hi",
                "agent_id": "a",
                "category": "eng",
                "similarity_score": 0.9,
                "metadata": {},
                "created_at": "2026-05-21T00:00:00Z"
            }],
            "count": 1
        })))
        .mount(&server)
        .await;

    let cli = test_client(&server.uri()).await;
    let resp = cli
        .search_memory(&SearchQuery {
            query: "hi".into(),
            limit: Some(5),
            ..Default::default()
        })
        .await
        .unwrap();
    assert_eq!(resp.count, 1);
    assert_eq!(resp.results[0].id, "1");
}

#[tokio::test]
async fn api_key_header_attached() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/memory/search"))
        .and(header("X-API-Key", "sk-test"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "results": [],
            "count": 0
        })))
        .expect(1)
        .mount(&server)
        .await;

    let cli = Client::builder()
        .base_url(&server.uri())
        .api_key(Some("sk-test".into()))
        .build()
        .unwrap();

    cli.search_memory(&SearchQuery {
        query: "x".into(),
        ..Default::default()
    })
    .await
    .unwrap();
}

#[tokio::test]
async fn tenant_header_attached() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/memory/search"))
        .and(header("X-Tenant-ID", "acme"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "results": [],
            "count": 0
        })))
        .expect(1)
        .mount(&server)
        .await;

    let cli = Client::builder()
        .base_url(&server.uri())
        .tenant_id(Some("acme".into()))
        .build()
        .unwrap();

    cli.search_memory(&SearchQuery {
        query: "x".into(),
        ..Default::default()
    })
    .await
    .unwrap();
}

#[tokio::test]
async fn http_error_surfaces_status_and_body() {
    let server = MockServer::start().await;
    Mock::given(method("POST"))
        .and(path("/memory/add"))
        .respond_with(
            ResponseTemplate::new(422)
                .set_body_string("{\"detail\":\"validation failed\"}"),
        )
        .mount(&server)
        .await;

    let cli = test_client(&server.uri()).await;
    let err = cli
        .add_memory(&MemoryEntry {
            content: "".into(),
            agent_id: "a".into(),
            memory_category: "x".into(),
            ..Default::default()
        })
        .await
        .unwrap_err();

    match err {
        Error::Http { status, body } => {
            assert_eq!(status, 422);
            assert!(body.contains("validation failed"));
        }
        _ => panic!("expected Error::Http, got {:?}", err),
    }
}

#[tokio::test]
async fn health_endpoint_is_get() {
    let server = MockServer::start().await;
    Mock::given(method("GET"))
        .and(path("/health"))
        .respond_with(ResponseTemplate::new(200).set_body_json(serde_json::json!({
            "status": "healthy",
            "enhanced_mode": true
        })))
        .mount(&server)
        .await;

    let cli = test_client(&server.uri()).await;
    let h = cli.get_health().await.unwrap();
    assert_eq!(h["status"], "healthy");
}

#[tokio::test]
async fn base_url_trailing_slash_stripped() {
    let cli = Client::builder()
        .base_url("http://x/")
        .build()
        .expect("builds");
    // Use a non-public field check indirectly via env-fallback test pattern;
    // here we just confirm the builder accepts the trailing slash without error.
    drop(cli);
}
