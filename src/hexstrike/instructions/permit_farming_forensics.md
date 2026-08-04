# Permit Farming Forensics — Full Operational Protocol

## Role
EIP-2612 / EIP-712 / Permit2 off-chain signature abuse detection in drainer frontends.

## Reference
- EIP-2612 permit selector: `0xd505accf`
- Permit2: `0x000000000022D473030F116dDEE9F6B43aC78BA3`
- Wallet methods: eth_signTypedData, eth_signTypedData_v4, personal_sign

## Workflow
1. Scan drainer repos for permit/signTypedData patterns
2. Extract correlated spender addresses
3. On-chain analyze each spender (entity + contract bytecode)
4. Build attack_chain: lure → typed_data → allowance → pull → impact

## Output
`artifacts/forensics/permit-farming-report.json`
Bus: `skill.permit_farming.complete` ← `permit_farming_analyzer`
