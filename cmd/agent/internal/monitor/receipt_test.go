package monitor

import (
	"testing"
)

type mockReleaser struct {
	released []string
}

func (m *mockReleaser) ReleaseDedup(key string) { m.released = append(m.released, key) }

func TestHandleReceiptRevertClearsDedup(t *testing.T) {
	m := &mockReleaser{}
	err := HandleReceipt(m, "bot:funder:1", &ReceiptResult{TxHash: "0xabc", Status: ReceiptFailed, Success: false})
	if err == nil {
		t.Fatal("expected error on revert")
	}
	if len(m.released) != 1 {
		t.Fatalf("released=%v", m.released)
	}
}

func TestHandleReceiptSuccessKeepsDedup(t *testing.T) {
	m := &mockReleaser{}
	if err := HandleReceipt(m, "k", &ReceiptResult{TxHash: "0xabc", Status: ReceiptSuccess, Success: true}); err != nil {
		t.Fatal(err)
	}
	if len(m.released) != 0 {
		t.Fatal("should not release on success")
	}
}
