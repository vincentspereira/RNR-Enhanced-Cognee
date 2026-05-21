//! Enhanced Cognee Rust client.
//!
//! Talks to the FastAPI HTTP variant of the Enhanced Cognee MCP server
//! (src/enhanced_cognee_mcp.py) over HTTP/JSON. Endpoints covered:
//!
//! - `POST /memory/add`             → [`Client::add_memory`]
//! - `POST /memory/search`          → [`Client::search_memory`]
//! - `POST /knowledge/add_relation` → [`Client::add_knowledge_relation`]
//! - `GET  /stats`                  → [`Client::get_stats`]
//! - `GET  /health`                 → [`Client::get_health`]
//!
//! # Example
//!
//! ```no_run
//! use enhanced_cognee_client::{Client, MemoryEntry};
//!
//! #[tokio::main]
//! async fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let cli = Client::builder()
//!         .base_url("http://localhost:8000")
//!         .api_key(std::env::var("ENHANCED_API_KEY").ok())
//!         .tenant_id(Some("acme".to_string()))
//!         .build()?;
//!
//!     let id = cli.add_memory(&MemoryEntry {
//!         content: "We use OAuth 2.0 for external services".to_string(),
//!         agent_id: "code-reviewer".to_string(),
//!         memory_category: "engineering".to_string(),
//!         ..Default::default()
//!     }).await?;
//!
//!     println!("Stored memory: {}", id);
//!     Ok(())
//! }
//! ```

use serde::{Deserialize, Serialize};
use std::time::Duration;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("HTTP {status}: {body}")]
    Http { status: u16, body: String },

    #[error("network error: {0}")]
    Network(#[from] reqwest::Error),

    #[error("serde error: {0}")]
    Serde(#[from] serde_json::Error),

    #[error("invalid base URL: {0}")]
    InvalidBaseUrl(String),
}

pub type Result<T> = std::result::Result<T, Error>;

/// A memory entry. Mirrors the server-side MemoryEntry pydantic model.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MemoryEntry {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    pub content: String,
    pub agent_id: String,
    pub memory_category: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding: Option<Vec<f64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
}

/// Search query.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SearchQuery {
    pub query: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub embedding: Option<Vec<f64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub similarity_threshold: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory_category: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub agent_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub filters: Option<serde_json::Value>,
}

/// One search hit.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub content: String,
    pub agent_id: String,
    pub category: String,
    pub similarity_score: f64,
    pub metadata: serde_json::Value,
    pub created_at: String,
}

/// Search response envelope.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResponse {
    pub results: Vec<SearchResult>,
    pub count: u32,
}

/// Knowledge-graph relation.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct KnowledgeRelation {
    pub source_entity: String,
    pub target_entity: String,
    pub relationship_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub properties: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
}

/// Builder for [`Client`].
pub struct ClientBuilder {
    base_url: String,
    api_key: Option<String>,
    tenant_id: Option<String>,
    timeout: Duration,
}

impl Default for ClientBuilder {
    fn default() -> Self {
        Self {
            base_url: std::env::var("ENHANCED_COGNEE_URL")
                .unwrap_or_else(|_| "http://localhost:8000".to_string()),
            api_key: std::env::var("ENHANCED_API_KEY").ok(),
            tenant_id: std::env::var("ENHANCED_TENANT_ID").ok(),
            timeout: Duration::from_secs(30),
        }
    }
}

impl ClientBuilder {
    pub fn base_url<S: Into<String>>(mut self, url: S) -> Self {
        self.base_url = url.into();
        self
    }

    pub fn api_key(mut self, key: Option<String>) -> Self {
        self.api_key = key;
        self
    }

    pub fn tenant_id(mut self, tenant: Option<String>) -> Self {
        self.tenant_id = tenant;
        self
    }

    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }

    pub fn build(self) -> Result<Client> {
        let base = self.base_url.trim_end_matches('/').to_string();
        if base.is_empty() {
            return Err(Error::InvalidBaseUrl("empty".to_string()));
        }
        let http = reqwest::Client::builder()
            .timeout(self.timeout)
            .build()
            .map_err(Error::Network)?;
        Ok(Client {
            base_url: base,
            api_key: self.api_key,
            tenant_id: self.tenant_id,
            http,
        })
    }
}

/// Enhanced Cognee HTTP client.
pub struct Client {
    base_url: String,
    api_key: Option<String>,
    tenant_id: Option<String>,
    http: reqwest::Client,
}

impl Client {
    pub fn builder() -> ClientBuilder {
        ClientBuilder::default()
    }

    /// POST /memory/add. Returns the new memory ID.
    pub async fn add_memory(&self, entry: &MemoryEntry) -> Result<String> {
        #[derive(Deserialize)]
        struct Resp {
            id: String,
        }
        let resp: Resp = self.do_json("POST", "/memory/add", Some(entry)).await?;
        Ok(resp.id)
    }

    /// POST /memory/search.
    pub async fn search_memory(&self, query: &SearchQuery) -> Result<SearchResponse> {
        self.do_json("POST", "/memory/search", Some(query)).await
    }

    /// POST /knowledge/add_relation. Returns the new relation ID.
    pub async fn add_knowledge_relation(
        &self,
        relation: &KnowledgeRelation,
    ) -> Result<String> {
        #[derive(Deserialize)]
        struct Resp {
            id: String,
        }
        let resp: Resp = self
            .do_json("POST", "/knowledge/add_relation", Some(relation))
            .await?;
        Ok(resp.id)
    }

    /// GET /stats.
    pub async fn get_stats(&self) -> Result<serde_json::Value> {
        self.do_json::<(), _>("GET", "/stats", None).await
    }

    /// GET /health.
    pub async fn get_health(&self) -> Result<serde_json::Value> {
        self.do_json::<(), _>("GET", "/health", None).await
    }

    // --------------------------------------------------------------
    // Internals
    // --------------------------------------------------------------

    async fn do_json<B, R>(&self, method: &str, path: &str, body: Option<&B>) -> Result<R>
    where
        B: Serialize + ?Sized,
        R: for<'de> Deserialize<'de>,
    {
        let url = format!("{}{}", self.base_url, path);
        let mut req = match method {
            "GET" => self.http.get(&url),
            "POST" => self.http.post(&url),
            "PUT" => self.http.put(&url),
            "DELETE" => self.http.delete(&url),
            _ => self.http.request(method.parse().unwrap_or(reqwest::Method::GET), &url),
        };

        req = req.header("Accept", "application/json");

        if let Some(key) = &self.api_key {
            req = req.header("X-API-Key", key);
        }
        if let Some(tenant) = &self.tenant_id {
            req = req.header("X-Tenant-ID", tenant);
        }
        if let Some(b) = body {
            req = req.json(b);
        }

        let resp = req.send().await?;
        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(Error::Http {
                status: status.as_u16(),
                body,
            });
        }
        let body = resp.bytes().await?;
        let parsed = serde_json::from_slice(&body)?;
        Ok(parsed)
    }
}
