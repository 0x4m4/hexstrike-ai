# Entity ID — Next Steps (UNIDENTIFIED)

**Target:** `0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA`  
**Confidence:** low  
**Net worth (public):** ~$1,122,486 (BASE USDC + BSC stable)

## Automated pipeline (Mac / VPS)

```bash
cd /Volumes/Eva/mufasaai-storage/hexstrike-ai
./hexstrike-orchestrator run entity-id-pipeline
./hexstrike-orchestrator report
```

## Manual OSINT (required for entity name)

1. **Blockscan multichain**  
   https://blockscan.com/address/0x4943F5E7F4e450d48Ae82026163ecDe8A52C53dA

2. **Arkham Intelligence** (UI — no API key in env)  
   https://platform.arkhamintelligence.com/explorer/address/0x4943f5e7f4e450d48ae82026163ecde8a52c53da

3. **BscScan labels & counterparty graph**  
   https://bscscan.com/address/0x4943f5e7f4e450d48ae82026163ecde8a52c53da

4. **Funding trace (done)**  
   +1,100,000 USDT from Binance Hot Wallet 11 — identity requires **legal/exchange** channel, not OSINT alone.

## Outflow tracing (not yet automated)

- Rhino.fi bridge sink: `0xb80a582fa430645a043bb4f6135321ee01005fef`
- Workflow `Graph-02` — planned; not in registry yet

## Disclosure gate

Do **not** send owner-directed email until entity is identified OR abuse report goes to **cloud provider only** (Yandex/OVH templates in this folder).
