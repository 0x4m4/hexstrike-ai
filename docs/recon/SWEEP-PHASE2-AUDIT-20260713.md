# Sweep Phase-2 Audit — 2026-07-13

**Mode:** read-only | **Impl:** `0x314C01e758a7911e7339aa4F960C7749E8947775`

## EIP-7702 Implementation Audit

| Property | Value |
|----------|-------|
| Bytecode size | 2751 bytes |
| Compiler | Solidity 0.8.4 (unverified) |
| RBAC | ECDSA signature-gated batch execute |
| Replay protection | `nonce()` per delegated account |

### Function selectors

| Selector | Signature |
|----------|-----------|
| `0x3f707e6b` | `execute((address,uint256,bytes)[])` |
| `0x4e487b71` | `Panic(uint256)` |
| `0x6171d1c9` | `execute((address,uint256,bytes)[],bytes)` |
| `0xaffed0e0` | `nonce()` |

### Security strings found

- ECDSA: invalid signature
- ECDSA: invalid signature 's' val`D
- ECDSA: invalid signature 'v' val`D
- ECDSA: invalid signature length
- Ethereum Signed Message:
- RpInvalid authority`x
- RpInvalid signature`x

### Verdict: unauthorized transfer **CLOSED** — requires valid authority ECDSA signature.

## Delegated Accounts (4)

| Role | Address | Matches impl |
|------|---------|--------------|
| authority | `0x730ea023…` | ✅ |
| sweep_router_primary | `0x55ed7fcd…` | ✅ |
| sweep_router_secondary | `0x3e0b65c9…` | ✅ |
| sweep_router_tertiary | `0x3a8b6289…` | ✅ |

## Rhino.fi Hub

| Property | Value |
|----------|-------|
| Address | `0xb80a582fa430645a043bb4f6135321ee01005fef` |
| USDT balance | **1,683,795.71** USDT |
| BNB balance | 74.9874 BNB |
| Direct CEX outflow | **False** |
| Role | Primary cross-chain exit sink |

## Architecture (confirmed)

```
hot_wallet → 4x EIP-7702 delegates → impl 0x314C01e7... → Rhino.fi hub
```

## Next steps

1. Trace Rhino.fi bridge exits on Base/Ethereum (correlate with hot wallet Base USDC)
2. Arkham label propagation
3. Monitor new delegate deployments on hot wallet

---
*Read-only defensive forensics.*
