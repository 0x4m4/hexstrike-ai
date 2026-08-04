package entity

import (
	"os"
	"testing"
	"time"
)

func TestCacheScoreArtifact(t *testing.T) {
	path := t.TempDir() + "/entity-id.json"
	body := `{
  "target": "0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA",
  "entity_resolution": {"status": "UNIDENTIFIED", "confidence": "low"}
}`
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	c := NewCache(path, time.Minute)
	s, err := c.Score("0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA")
	if err != nil {
		t.Fatal(err)
	}
	if s.Risk != "high" {
		t.Fatalf("risk=%s", s.Risk)
	}
	s2, _ := c.Score("0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA")
	if s2.CachedAt != s.CachedAt {
		t.Fatal("expected cache hit")
	}
}
