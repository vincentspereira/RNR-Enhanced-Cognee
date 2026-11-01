package enhancedcognee

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
)

// Project memory derives scope from the token, never from body selectors.
// Retraction preserves history. Retry uncertain writes with the same key.
func (c *Client) projectRequest(ctx context.Context, method, path string, body interface{}) (map[string]interface{}, error) {
	origin, err := url.Parse(c.baseURL)
	if err != nil || !c.explicitBaseURL || c.accessToken == "" || c.apiKey != "" || (origin.Path != "" && origin.Path != "/") {
		return nil, errors.New("canonical memory requires a scoped bearer token and service origin")
	}
	out := map[string]interface{}{}
	if err := c.doJSON(ctx, method, "/v1/memories"+path, body, &out); err != nil {
		var refused *Error
		if errors.As(err, &refused) {
			var details map[string]interface{}
			_ = json.Unmarshal([]byte(refused.Body), &details)
			safe, _ := json.Marshal(map[string]interface{}{"clarification_required": details["clarification_required"] == true})
			return nil, &Error{Status: refused.Status, Body: string(safe)}
		}
		return nil, errors.New("memory request unavailable; no success acknowledged; retry with the same identity")
	}
	return out, nil
}

func (c *Client) Remember(ctx context.Context, content, idempotencyKey string, declarations map[string]interface{}) (map[string]interface{}, error) {
	body := map[string]interface{}{}
	for key, value := range declarations {
		body[key] = value
	}
	body["content"], body["idempotency_key"] = content, idempotencyKey
	return c.projectRequest(ctx, "POST", "", body)
}
func (c *Client) Recall(ctx context.Context, query string, limit int) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "POST", "/recall", map[string]interface{}{"query": query, "limit": limit})
}
func (c *Client) GetRecord(ctx context.Context, id string) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "GET", "/"+url.PathEscape(id), nil)
}
func (c *Client) ListRecords(ctx context.Context, limit, offset int) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "GET", fmt.Sprintf("?limit=%d&offset=%d", limit, offset), nil)
}
func (c *Client) CorrectRecord(ctx context.Context, id, content string, expectedVersion int) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "PATCH", "/"+url.PathEscape(id), map[string]interface{}{"content": content, "expected_version": expectedVersion})
}
func (c *Client) RetractRecord(ctx context.Context, id string, expectedVersion int) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "POST", "/"+url.PathEscape(id)+"/retract", map[string]interface{}{"expected_version": expectedVersion})
}
func (c *Client) RecordHistory(ctx context.Context, id string) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "GET", "/"+url.PathEscape(id)+"/history", nil)
}
func (c *Client) Connections(ctx context.Context, entity string, depth, limit int) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "POST", "/connections", map[string]interface{}{"entity": entity, "depth": depth, "limit": limit})
}
func (c *Client) MemoryStatus(ctx context.Context) (map[string]interface{}, error) {
	return c.projectRequest(ctx, "GET", "/status", nil)
}
