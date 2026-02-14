# PAICE + NEAR Protocol Integration

**Privacy-preserving AI collaboration assessment with verifiable private inference and on-chain attestation via NEAR.**

PAICE is a production privacy-preserving AI assessment platform deployed at [paice.work](https://paice.work). This repository contains the NEAR Protocol integration layer, built for the [NEARCON Innovation Sandbox 2026](https://near-innovation-sandbox.devspot.app/).

## What This Does

### Layer 1: On-Chain Assessment Attestation
After each assessment, the score payload is SHA-256 hashed and written to a NEAR smart contract. Anyone can verify that assessment results haven't been tampered with by checking the on-chain hash.

### Layer 2: Private Inference via NEAR AI Cloud
All AI inference runs inside hardware-secured TEE (Trusted Execution Environment) enclaves via NEAR AI Cloud. Neither PAICE, NEAR, nor the cloud provider can see conversation content during processing.

## Quick Start

### Try the Demo
Open `demo/index.html` in a browser, enter your [NEAR AI Cloud API key](https://cloud.near.ai), and walk through the full pipeline:

1. Chat with AI via TEE-protected inference
2. Generate assessment scores
3. Hash the score payload (SHA-256)
4. Write attestation to NEAR testnet
5. Verify the attestation on-chain

### Test the API

```bash
# Test NEAR AI Cloud inference
export NEAR_AI_API_KEY=sk-your-key
python integration/examples/test_near_ai.py

# Test attestation verification
python integration/examples/test_attestation.py
```

### Verify an Attestation

```python
from integration.near_service import AttestationService

service = AttestationService(
    contract_id="e756da-291226-1771097746.nearplay.testnet",
    network="testnet"
)

# Verify a session
result = service.verify("test-session-001")
print(f"Found: {result.found}")
print(f"Score hash: {result.score_hash}")
print(f"Attester: {result.attester}")
```

## Repository Structure

```
paice-near-integration/
  contracts/
    assessment-attestation/      # Rust smart contract (NEAR SDK)
      Cargo.toml
      src/lib.rs
  integration/
    near_service.py              # Python service (inference + attestation)
    near_config.py               # Configuration management
    examples/
      test_near_ai.py            # NEAR AI Cloud test script
      test_attestation.py        # Contract verification test
  demo/
    index.html                   # Standalone interactive demo
  docs/
    architecture.md              # Integration architecture diagram
```

## Deployed Contract

| Field | Value |
|-------|-------|
| Address | `e756da-291226-1771097746.nearplay.testnet` |
| Network | NEAR Testnet |
| Explorer | [View on NearBlocks](https://testnet.nearblocks.io/address/e756da-291226-1771097746.nearplay.testnet) |
| Methods | `attest()`, `verify()`, `get_attestation_count()` |
| Deployed via | [nearplay.app](https://nearplay.app) |

## NEAR AI Cloud Models Used

| Model | TEE Protected | Cost (Input/Output per M tokens) |
|-------|:---:|-------|
| DeepSeek V3.1 | Yes | $1.05 / $3.10 |
| Qwen3 30B | Yes | $0.15 / $0.55 |
| GPT OSS 120B | Yes | $0.15 / $0.55 |
| Claude Opus 4.6 | -- | $5.00 / $25.00 |
| GPT-5.2 | -- | $1.80 / $15.50 |

## How Verification Works

1. Obtain the assessment score payload (session ID, dimensional scores, tier, timestamp)
2. Serialize as JSON with sorted keys: `JSON.stringify(payload, Object.keys(payload).sort())`
3. Compute SHA-256: `sha256:<hex>`
4. Call `verify(session_id)` on the contract via NEAR RPC
5. Compare the returned `score_hash` with your computed hash
6. If they match, the scores are authentic and untampered

## Environment Variables

```env
NEAR_AI_API_KEY=sk-your-api-key
NEAR_AI_ENABLED=true
NEAR_AI_MODEL=deepseek-ai/DeepSeek-V3.1
NEAR_CONTRACT_ID=e756da-291226-1771097746.nearplay.testnet
NEAR_NETWORK=testnet
```

## Why NEAR?

This integration can only work with NEAR's unique combination of:
- **NEAR AI Cloud**: TEE-protected inference with hardware attestation
- **NEAR Blockchain**: On-chain state for immutable attestations
- **Account Model**: Named accounts for human-readable contract addresses
- **Low Fees**: Testnet deployments are free; mainnet attestations cost fractions of a cent

## License

MIT

## About PAICE

PAICE (Privacy-preserving AI Collaboration Effectiveness) is a production application that assesses how effectively people collaborate with AI. It uses adaptive conversational assessment with embedded behavioral tests across five dimensions: Performance, Accountability, Integrity, Collaboration, and Evolution.

The main application is deployed at [paice.work](https://paice.work). This repo contains only the NEAR Protocol integration layer.

Built by [Snap Synapse](https://snapsynapse.com) for NEARCON Innovation Sandbox 2026.
