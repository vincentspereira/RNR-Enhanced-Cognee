package enhancedcognee

import (
	"context"
	"errors"
	"net/http"
	"os"
	"testing"
)

type forbiddenProjectTransport struct{ t *testing.T }

func (transport forbiddenProjectTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	transport.t.Fatal("unconfigured destination received credential I/O")
	return nil, errors.New("unconfigured destination")
}

func TestCanonicalDestinationMustBeExplicit(t *testing.T) {
	t.Setenv("ENHANCED_COGNEE_URL", "")
	client, err := NewClient(Options{AccessToken: "synthetic", HTTPClient: &http.Client{Transport: forbiddenProjectTransport{t}}})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := client.MemoryStatus(context.Background()); err == nil {
		t.Fatal("implicit destination accepted")
	}
}

func TestCanonicalLiveProjectMemory(t *testing.T) {
	base := os.Getenv("RNR_CLIENT_QUALIFICATION_URL")
	if base == "" {
		t.Skip("requires an explicitly selected synthetic service")
	}
	c, err := NewClient(Options{BaseURL: base, AccessToken: os.Getenv("RNR_CLIENT_QUALIFICATION_TOKEN")})
	if err != nil {
		t.Fatal(err)
	}
	other, err := NewClient(Options{BaseURL: base, AccessToken: os.Getenv("RNR_CLIENT_OTHER_TOKEN")})
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	first, err := c.Remember(ctx, "Synthetic Go Cedar retains eleven copies.", "go-live-one", nil)
	if err != nil {
		t.Fatal(err)
	}
	id := first["id"].(string)
	again, err := c.Remember(ctx, "Synthetic Go Cedar retains eleven copies.", "go-live-one", nil)
	if err != nil || again["id"] != id {
		t.Fatal("retry did not preserve identity", err)
	}
	found, err := c.Recall(ctx, "Cedar", 5)
	if err != nil || len(found["results"].([]interface{})) != 1 {
		t.Fatal("recall failed", err)
	}
	_, err = other.GetRecord(ctx, id)
	var refused *Error
	if !errors.As(err, &refused) || refused.Status != 404 {
		t.Fatal("cross-project read was not refused")
	}
	changed, err := c.CorrectRecord(ctx, id, "Synthetic Go Cedar retains nine copies.", 1)
	if err != nil || changed["version"] != float64(2) {
		t.Fatal("correction failed", err)
	}
	_, err = c.CorrectRecord(ctx, id, "Stale", 1)
	if !errors.As(err, &refused) || refused.Status != 409 {
		t.Fatal("stale version accepted")
	}
	if _, err = c.RetractRecord(ctx, id, 2); err != nil {
		t.Fatal(err)
	}
	history, err := c.RecordHistory(ctx, id)
	if err != nil || len(history["versions"].([]interface{})) != 3 {
		t.Fatal("history lost", err)
	}
	if _, err = c.Remember(ctx, "password: synthetic-only-secret", "go-no-secret", nil); err == nil {
		t.Fatal("secret accepted")
	}
	status, err := c.MemoryStatus(ctx)
	if err != nil || status["active_records"] != float64(0) {
		t.Fatal("retraction failed", err)
	}
}
