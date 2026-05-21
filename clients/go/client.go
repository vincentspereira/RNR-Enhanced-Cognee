// Package enhancedcognee is the official Go client for the Enhanced Cognee
// MCP HTTP server. It talks to the FastAPI variant at
// src/enhanced_cognee_mcp.py over HTTP/JSON.
//
// Example:
//
//	cli, err := enhancedcognee.NewClient(enhancedcognee.Options{
//	    BaseURL:  "http://localhost:8000",
//	    APIKey:   os.Getenv("ENHANCED_API_KEY"),  // optional
//	    TenantID: "acme",                          // optional
//	})
//	if err != nil { log.Fatal(err) }
//
//	id, err := cli.AddMemory(ctx, &enhancedcognee.MemoryEntry{
//	    Content:        "We use OAuth 2.0 for external services",
//	    AgentID:        "code-reviewer",
//	    MemoryCategory: "engineering",
//	})
package enhancedcognee

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// Options configures a Client.
type Options struct {
	BaseURL    string        // defaults to ENHANCED_COGNEE_URL env or http://localhost:8000
	APIKey     string        // optional; defaults to ENHANCED_API_KEY env
	TenantID   string        // optional; defaults to ENHANCED_TENANT_ID env
	HTTPClient *http.Client  // optional; defaults to net/http default with 30s timeout
	Timeout    time.Duration // optional; defaults to 30s
}

// Client is the Enhanced Cognee MCP HTTP client.
type Client struct {
	baseURL  string
	apiKey   string
	tenantID string
	hc       *http.Client
}

// NewClient constructs a Client. Returns an error only if no valid base URL
// can be resolved (constructor will not network-test the server).
func NewClient(opts Options) (*Client, error) {
	base := opts.BaseURL
	if base == "" {
		base = os.Getenv("ENHANCED_COGNEE_URL")
	}
	if base == "" {
		base = "http://localhost:8000"
	}
	base = strings.TrimRight(base, "/")

	apiKey := opts.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("ENHANCED_API_KEY")
	}
	tenantID := opts.TenantID
	if tenantID == "" {
		tenantID = os.Getenv("ENHANCED_TENANT_ID")
	}

	hc := opts.HTTPClient
	if hc == nil {
		timeout := opts.Timeout
		if timeout == 0 {
			timeout = 30 * time.Second
		}
		hc = &http.Client{Timeout: timeout}
	}

	return &Client{
		baseURL:  base,
		apiKey:   apiKey,
		tenantID: tenantID,
		hc:       hc,
	}, nil
}

// MemoryEntry mirrors the server's MemoryEntry pydantic model. JSON
// field names are snake_case to match the API.
type MemoryEntry struct {
	ID             string                 `json:"id,omitempty"`
	Content        string                 `json:"content"`
	AgentID        string                 `json:"agent_id"`
	MemoryCategory string                 `json:"memory_category"`
	Embedding      []float64              `json:"embedding,omitempty"`
	Metadata       map[string]interface{} `json:"metadata,omitempty"`
	Tags           []string               `json:"tags,omitempty"`
	CreatedAt      string                 `json:"created_at,omitempty"`
}

// SearchQuery mirrors the server's SearchQuery.
type SearchQuery struct {
	Query               string                 `json:"query"`
	Embedding           []float64              `json:"embedding,omitempty"`
	Limit               int                    `json:"limit,omitempty"`
	SimilarityThreshold float64                `json:"similarity_threshold,omitempty"`
	MemoryCategory      string                 `json:"memory_category,omitempty"`
	AgentID             string                 `json:"agent_id,omitempty"`
	Filters             map[string]interface{} `json:"filters,omitempty"`
}

// SearchResult is one row from /memory/search.
type SearchResult struct {
	ID              string                 `json:"id"`
	Content         string                 `json:"content"`
	AgentID         string                 `json:"agent_id"`
	Category        string                 `json:"category"`
	SimilarityScore float64                `json:"similarity_score"`
	Metadata        map[string]interface{} `json:"metadata"`
	CreatedAt       string                 `json:"created_at"`
}

// SearchResponse is the /memory/search response envelope.
type SearchResponse struct {
	Results []SearchResult `json:"results"`
	Count   int            `json:"count"`
}

// KnowledgeRelation mirrors the server's KnowledgeRelation.
type KnowledgeRelation struct {
	SourceEntity     string                 `json:"source_entity"`
	TargetEntity     string                 `json:"target_entity"`
	RelationshipType string                 `json:"relationship_type"`
	Properties       map[string]interface{} `json:"properties,omitempty"`
	Confidence       float64                `json:"confidence,omitempty"`
}

// Error is the typed error returned for any non-2xx HTTP response.
type Error struct {
	Status int
	Body   string
}

func (e *Error) Error() string {
	return fmt.Sprintf("enhanced-cognee HTTP %d: %s", e.Status, e.Body)
}

// AddMemory POSTs /memory/add. Returns the new memory ID.
func (c *Client) AddMemory(ctx context.Context, entry *MemoryEntry) (string, error) {
	var resp struct {
		ID string `json:"id"`
	}
	if err := c.doJSON(ctx, "POST", "/memory/add", entry, &resp); err != nil {
		return "", err
	}
	return resp.ID, nil
}

// SearchMemory POSTs /memory/search.
func (c *Client) SearchMemory(ctx context.Context, q *SearchQuery) (*SearchResponse, error) {
	var out SearchResponse
	if err := c.doJSON(ctx, "POST", "/memory/search", q, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// AddKnowledgeRelation POSTs /knowledge/add_relation.
func (c *Client) AddKnowledgeRelation(ctx context.Context, r *KnowledgeRelation) (string, error) {
	var resp struct {
		ID string `json:"id"`
	}
	if err := c.doJSON(ctx, "POST", "/knowledge/add_relation", r, &resp); err != nil {
		return "", err
	}
	return resp.ID, nil
}

// GetStats GETs /stats.
func (c *Client) GetStats(ctx context.Context) (map[string]interface{}, error) {
	out := map[string]interface{}{}
	if err := c.doJSON(ctx, "GET", "/stats", nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// GetHealth GETs /health.
func (c *Client) GetHealth(ctx context.Context) (map[string]interface{}, error) {
	out := map[string]interface{}{}
	if err := c.doJSON(ctx, "GET", "/health", nil, &out); err != nil {
		return nil, err
	}
	return out, nil
}

// --------------------------------------------------------------
// Internals
// --------------------------------------------------------------

func (c *Client) doJSON(ctx context.Context, method, path string, body, out interface{}) error {
	var reqBody io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		reqBody = bytes.NewReader(buf)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, reqBody)
	if err != nil {
		return fmt.Errorf("build request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if reqBody != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("X-API-Key", c.apiKey)
	}
	if c.tenantID != "" {
		req.Header.Set("X-Tenant-ID", c.tenantID)
	}

	resp, err := c.hc.Do(req)
	if err != nil {
		return fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return &Error{Status: resp.StatusCode, Body: string(respBody)}
	}

	if out == nil {
		return nil
	}
	if err := json.Unmarshal(respBody, out); err != nil {
		return fmt.Errorf("unmarshal response: %w", err)
	}
	return nil
}

// IsHTTPError reports whether err is an enhanced-cognee HTTP error (non-2xx).
func IsHTTPError(err error) bool {
	var e *Error
	return errors.As(err, &e)
}
