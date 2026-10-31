//! Canonical project API. Signed identity, stable retries and retained history.
use crate::{Client, Error, Result};
use serde_json::{json, Value};

fn record_path(id: &str) -> Result<String> {
    if id.is_empty() || id.len() > 64 || !id.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-' || c == b'_') {
        return Err(Error::InvalidBaseUrl("invalid bounded record identity".into()));
    }
    Ok(format!("/{id}"))
}

impl Client {
    async fn project_request(&self, method: &str, path: &str, body: Option<&Value>) -> Result<Value> {
        let origin = reqwest::Url::parse(&self.base_url)
            .map_err(|_| Error::InvalidBaseUrl("invalid service origin".into()))?;
        if !self.explicit_base_url || self.access_token.as_deref().unwrap_or("").is_empty() || self.api_key.is_some() || origin.path() != "/" {
            return Err(Error::InvalidBaseUrl("canonical memory requires a scoped bearer token and service origin".into()));
        }
        match self.do_json(method, &format!("/v1/memories{path}"), body).await {
            Ok(value) => Ok(value),
            Err(Error::Http { status, body }) => {
                let details: Value = serde_json::from_str(&body).unwrap_or(Value::Null);
                Err(Error::Http { status, body: json!({"clarification_required": details["clarification_required"] == true}).to_string() })
            }
            Err(_) => Err(Error::Http { status: 503, body: "memory unavailable; no success acknowledged; retry the same identity".into() }),
        }
    }
    pub async fn remember(&self, content: &str, idempotency_key: &str, declarations: Option<&Value>) -> Result<Value> {
        let mut body = declarations.cloned().unwrap_or(json!({}));
        if !body.is_object() { return Err(Error::InvalidBaseUrl("declarations must be an object".into())); }
        body["content"] = json!(content);
        body["idempotency_key"] = json!(idempotency_key);
        self.project_request("POST", "", Some(&body)).await
    }
    pub async fn recall(&self, query: &str, limit: u32) -> Result<Value> {
        self.project_request("POST", "/recall", Some(&json!({"query": query, "limit": limit}))).await
    }
    pub async fn get_record(&self, id: &str) -> Result<Value> {
        self.project_request("GET", &record_path(id)?, None).await
    }
    pub async fn list_records(&self, limit: u32, offset: u32) -> Result<Value> {
        self.project_request("GET", &format!("?limit={limit}&offset={offset}"), None).await
    }
    pub async fn correct_record(&self, id: &str, content: &str, expected_version: u32) -> Result<Value> {
        self.project_request("PATCH", &record_path(id)?, Some(&json!({"content": content, "expected_version": expected_version}))).await
    }
    pub async fn retract_record(&self, id: &str, expected_version: u32) -> Result<Value> {
        self.project_request("POST", &format!("{}/retract", record_path(id)?), Some(&json!({"expected_version": expected_version}))).await
    }
    pub async fn record_history(&self, id: &str) -> Result<Value> {
        self.project_request("GET", &format!("{}/history", record_path(id)?), None).await
    }
    pub async fn connections(&self, entity: &str, depth: u32, limit: u32) -> Result<Value> {
        self.project_request("POST", "/connections", Some(&json!({"entity": entity, "depth": depth, "limit": limit}))).await
    }
    pub async fn memory_status(&self) -> Result<Value> {
        self.project_request("GET", "/status", None).await
    }
}
