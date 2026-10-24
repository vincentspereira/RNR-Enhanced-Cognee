use enhanced_cognee_client::{Client, Error};

#[tokio::test]
#[ignore = "requires an explicitly selected synthetic canonical service"]
async fn canonical_live_project_memory() {
    let base = std::env::var("RNR_CLIENT_QUALIFICATION_URL").expect("select a synthetic service");
    let client = Client::builder().base_url(&base).api_key(None)
        .access_token(Some(std::env::var("RNR_CLIENT_QUALIFICATION_TOKEN").unwrap())).build().unwrap();
    let other = Client::builder().base_url(&base).api_key(None)
        .access_token(Some(std::env::var("RNR_CLIENT_OTHER_TOKEN").unwrap())).build().unwrap();
    let first = client.remember("Synthetic Rust Cedar retains eleven copies.", "rust-live-one", None).await.unwrap();
    let id = first["id"].as_str().unwrap();
    assert_eq!(client.remember("Synthetic Rust Cedar retains eleven copies.", "rust-live-one", None).await.unwrap()["id"], id);
    assert_eq!(client.recall("Cedar", 5).await.unwrap()["results"][0]["id"], id);
    assert!(matches!(other.get_record(id).await, Err(Error::Http {status:404, ..})));
    assert_eq!(client.correct_record(id, "Synthetic Rust Cedar retains nine copies.", 1).await.unwrap()["version"], 2);
    assert!(matches!(client.correct_record(id, "Stale", 1).await, Err(Error::Http {status:409, ..})));
    client.retract_record(id, 2).await.unwrap();
    assert_eq!(client.recall("Cedar", 5).await.unwrap()["results"].as_array().unwrap().len(), 0);
    assert_eq!(client.record_history(id).await.unwrap()["versions"].as_array().unwrap().len(), 3);
    assert!(client.remember("password: synthetic-only-secret", "rust-no-secret", None).await.is_err());
    assert_eq!(client.memory_status().await.unwrap()["active_records"], 0);
}
