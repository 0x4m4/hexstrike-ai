# CREATE2 Drainer Forensics — Full Operational Protocol

## Role
EIP-1014 CREATE2 + EIP-1167 minimal proxy factory pipeline analysis for blocklist evasion.

## Reference
- Opcode: `0xf5` (CREATE2)
- Address formula: `keccak256(0xff ++ deployer ++ salt ++ keccak256(init_code))[12:]`

## Drainer TTP
1. Deploy fresh claim/drain contract per phishing domain
2. Evade static blocklists targeting fixed addresses
3. Salt grinding for vanity or cross-chain address reuse
4. Minimal proxy (EIP-1167) + CREATE2 factory pipelines

## Workflow
1. Scan repos + artifacts for create2/cloneDeterministic/EIP-1167 markers
2. Extract claim contract candidates
3. Bytecode deobfuscate each claim contract via ForensicsEngine
4. Build attack_chain: factory → salt → proxy → phishing bind → drain → rotate

## Output
`artifacts/forensics/create2-drainer-report.json`
Bus: `skill.create2_drainer.complete` ← `create2_drainer_analyzer`
