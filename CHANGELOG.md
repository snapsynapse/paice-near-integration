# Changelog

## v1.1.0 — 2026-02-16 (Real On-Chain Attestation)

### On-Chain Transaction Signing
- **near-api-js integration**: All three demo files now sign real `attest()` transactions client-side via `near-api-js` v4.0.4
- **Full 7-step pipeline**: "Attest on NEAR" writes a signed transaction; "Verify" reads it back from chain — all 7 steps complete with green checkmarks
- **Transaction hash display**: Attestation card shows clickable tx hash linking to NearBlocks explorer
- **Graceful fallback**: If signing fails, demo continues with read-only attestation display

### New Testnet Account
- **`paice-demo.testnet`**: Dedicated demo account with locally-managed ed25519 keypair, deployed via NEAR CLI
- **Contract**: Same Rust WASM as v1.0.0, verified working with `attest()`, `verify()`, `get_attestation_count()`
- **Replaces**: `e756da-291226-1771097746.nearplay.testnet` (nearplay.app Playground — no key export)

### GitHub Pages
- **Live demo**: [https://snapsynapse.github.io/paice-near-integration/](https://snapsynapse.github.io/paice-near-integration/)
- API key pre-loaded, testnet contract configured — judges can try immediately

### Supporting File Updates
- Updated contract address in `.env.example`, `README.md`, `docs/architecture.md`, `near_config.py`, `test_attestation.py`
- README: added live demo URL, near-api-js signing context, updated testnet contract table

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

### Day 3 — Monday Feb 16 (Submission Day)
- **Repo restructure**: Moved contract from `contracts/assessment-attestation/` to repo root for nearplay.app compatibility
- **Mainnet deployment**: Contract deployed to `paice.near` via NEAR CLI (tx: `3dG2Qr8KRgLedeZctz8TPe2KwRinWXPCzLkvX37yoRFY`)
- **Production integration**: PAICE staging backend (`paice-development-backend.onrender.com`) configured for mainnet attestations
- **Badge persistence**: Fixed `?s=confidential` toggle surviving React Router navigation via sessionStorage
