# Changelog

## v1.0.0 — 2026-02-15 (NEARCON Innovation Sandbox Submission)

### Day 1 — Saturday Feb 14
- **Initial integration**: NEAR AI Cloud as inference provider, single-model demo, Python service layer
- **Three-layer cascade**: GPT OSS 120B (chat) → Qwen3 30B (middleware) → GLM 4.7 (evaluation), all TEE-protected
- **Smart contract**: Rust attestation contract deployed to testnet via nearplay.app
- **Mainnet account**: `paice.near` registered and funded

### Day 2 — Sunday Feb 15
- **Mainnet cascade demo**: `demo/cascade-mainnet.html` pre-configured for `paice.near`
- **Bug fix**: Verification now uses actual session ID (was hardcoded to test value)
- **Cost analysis**: Real assessment token estimates based on production transcript data ($0.02–0.05 per assessment)
- **Documentation**: Architecture docs, cost breakdown, privacy context for judges
