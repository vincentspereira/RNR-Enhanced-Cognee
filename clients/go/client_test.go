package enhancedcognee

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestScopedTokenRedirectAndResponseBudget(t *testing.T) {
	called := false
	destination := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true }))
	defer destination.Close()
	origin := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer synthetic" {
			t.Error("missing scoped token")
		}
		http.Redirect(w, r, destination.URL, http.StatusFound)
	}))
	defer origin.Close()
	client, err := NewClient(Options{BaseURL: origin.URL, AccessToken: "synthetic"})
	if err != nil {
		t.Fatal(err)
	}
	_, err = client.GetHealth(context.Background())
	var status *Error
	if !errors.As(err, &status) || status.Status != 302 || called {
		t.Fatal("redirect was followed or not reported")
	}
	oversized := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte(strings.Repeat("x", 1024*1024+1))) }))
	defer oversized.Close()
	client, _ = NewClient(Options{BaseURL: oversized.URL})
	_, err = client.GetHealth(context.Background())
	if err == nil || !strings.Contains(err.Error(), "1 MiB") {
		t.Fatal("response budget was not enforced")
	}
}

func TestUnsafeOrAmbiguousCredentials(t *testing.T) {
	for _, options := range []Options{
		{BaseURL: "http://remote", AccessToken: "synthetic"},
		{BaseURL: "https://approved", AccessToken: "one", APIKey: "two"},
		{BaseURL: "file:///private"},
		{BaseURL: "https://user:pass@approved"},
		{BaseURL: "https://approved/?secret=fixture"},
	} {
		if _, err := NewClient(options); err == nil {
			t.Error("unsafe constructor accepted")
		}
	}
}

func newTestClient(handler http.Handler) (*Client, *httptest.Server) {
	srv := httptest.NewServer(handler)
	cli, _ := NewClient(Options{
		BaseURL: srv.URL,
		Timeout: 5 * time.Second,
	})
	return cli, srv
}

func TestAddMemory_Success(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/memory/add", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			t.Errorf("method = %s, want POST", r.Method)
		}
		var got MemoryEntry
		if err := json.NewDecoder(r.Body).Decode(&got); err != nil {
			t.Fatalf("decode: %v", err)
		}
		if got.Content != "hello" || got.AgentID != "agent-1" {
			t.Errorf("got = %+v", got)
		}
		json.NewEncoder(w).Encode(map[string]string{"id": "mem-abc"})
	})

	cli, srv := newTestClient(mux)
	defer srv.Close()

	id, err := cli.AddMemory(context.Background(), &MemoryEntry{
		Content:        "hello",
		AgentID:        "agent-1",
		MemoryCategory: "engineering",
	})
	if err != nil {
		t.Fatal(err)
	}
	if id != "mem-abc" {
		t.Errorf("id = %q, want mem-abc", id)
	}
}

func TestSearchMemory_Success(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/memory/search", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		w.Write([]byte(`{"results":[{"id":"1","content":"hi","agent_id":"a","category":"eng","similarity_score":0.9,"metadata":{},"created_at":"2026-05-21T00:00:00Z"}],"count":1}`))
	})

	cli, srv := newTestClient(mux)
	defer srv.Close()

	resp, err := cli.SearchMemory(context.Background(), &SearchQuery{
		Query: "hi",
		Limit: 5,
	})
	if err != nil {
		t.Fatal(err)
	}
	if resp.Count != 1 || len(resp.Results) != 1 || resp.Results[0].ID != "1" {
		t.Errorf("resp = %+v", resp)
	}
}

func TestAddKnowledgeRelation_Success(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/knowledge/add_relation", func(w http.ResponseWriter, r *http.Request) {
		var got KnowledgeRelation
		json.NewDecoder(r.Body).Decode(&got)
		if got.SourceEntity != "a" || got.TargetEntity != "b" {
			t.Errorf("got = %+v", got)
		}
		json.NewEncoder(w).Encode(map[string]string{"id": "rel-1"})
	})

	cli, srv := newTestClient(mux)
	defer srv.Close()

	id, err := cli.AddKnowledgeRelation(context.Background(), &KnowledgeRelation{
		SourceEntity:     "a",
		TargetEntity:     "b",
		RelationshipType: "KNOWS",
		Confidence:       0.9,
	})
	if err != nil {
		t.Fatal(err)
	}
	if id != "rel-1" {
		t.Errorf("id = %q", id)
	}
}

func TestAPIKeyHeader(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/memory/search", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-API-Key") != "sk-test" {
			t.Errorf("X-API-Key = %q", r.Header.Get("X-API-Key"))
		}
		w.Write([]byte(`{"results":[],"count":0}`))
	})

	srv := httptest.NewServer(mux)
	defer srv.Close()
	cli, _ := NewClient(Options{BaseURL: srv.URL, APIKey: "sk-test"})

	_, err := cli.SearchMemory(context.Background(), &SearchQuery{Query: "x"})
	if err != nil {
		t.Fatal(err)
	}
}

func TestTenantHeader(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/memory/search", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Tenant-ID") != "acme" {
			t.Errorf("X-Tenant-ID = %q", r.Header.Get("X-Tenant-ID"))
		}
		w.Write([]byte(`{"results":[],"count":0}`))
	})

	srv := httptest.NewServer(mux)
	defer srv.Close()
	cli, _ := NewClient(Options{BaseURL: srv.URL, TenantID: "acme"})

	_, err := cli.SearchMemory(context.Background(), &SearchQuery{Query: "x"})
	if err != nil {
		t.Fatal(err)
	}
}

func TestHTTPError_Surfaces(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/memory/add", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(422)
		w.Write([]byte(`{"detail":"validation failed"}`))
	})
	cli, srv := newTestClient(mux)
	defer srv.Close()

	_, err := cli.AddMemory(context.Background(), &MemoryEntry{
		Content: "", AgentID: "a", MemoryCategory: "x",
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if !IsHTTPError(err) {
		t.Errorf("IsHTTPError(%v) = false", err)
	}
	var httpErr *Error
	if !errors.As(err, &httpErr) {
		t.Fatalf("errors.As failed")
	}
	if httpErr.Status != 422 || !strings.Contains(httpErr.Body, "validation failed") {
		t.Errorf("httpErr = %+v", httpErr)
	}
}

func TestGetHealth(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("method = %s", r.Method)
		}
		w.Write([]byte(`{"status":"healthy","enhanced_mode":true}`))
	})
	cli, srv := newTestClient(mux)
	defer srv.Close()

	h, err := cli.GetHealth(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if h["status"] != "healthy" {
		t.Errorf("h = %+v", h)
	}
}

func TestBaseURL_TrailingSlash_Stripped(t *testing.T) {
	cli, _ := NewClient(Options{BaseURL: "http://x/"})
	if cli.baseURL != "http://x" {
		t.Errorf("baseURL = %q", cli.baseURL)
	}
}

func TestBaseURL_EnvFallback(t *testing.T) {
	t.Setenv("ENHANCED_COGNEE_URL", "http://env-host:1234")
	cli, _ := NewClient(Options{})
	if cli.baseURL != "http://env-host:1234" {
		t.Errorf("baseURL = %q", cli.baseURL)
	}
}
