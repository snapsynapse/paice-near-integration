# PAICE + NEAR Protocol Integration

**Privacy-preserving AI collaboration assessment with verifiable private inference and on-chain attestation via NEAR.**

PAICE is a production privacy-preserving AI assessment platform deployed at [paice.work](https://paice.work). This repository contains the NEAR Protocol integration layer, built for the [NEARCON Innovation Sandbox 2026](https://near-innovation-sandbox.devspot.app/).

## What This Does

### Layer 1: On-Chain Assessment Attestation
After each assessment, the score payload is SHA-256 hashed and written to a NEAR smart contract. Anyone can verify that assessment results haven't been tampered with by checking the on-chain hash.

### Layer 2: Private Inference via NEAR AI Cloud
All AI inference runs inside hardware-secured TEE (Trusted Execution Environment) enclaves via NEAR AI Cloud. Neither PAICE, NEAR, nor the cloud provider can see conversation content during processing.

### Layer 3: Three-Layer Model Cascade
PAICE separates concerns across three dedicated model layers, each running inside TEE enclaves:

| Layer | Primary Model | Fallback | Role |
|-------|--------------|----------|------|
| **Chat** | GPT OSS 120B | DeepSeek V3.1 | Conducts the assessment conversation |
| **Middleware** | Qwen3 30B | DeepSeek V3.1 | QA validation of AI responses |
| **Evaluation** | GLM 4.7 | GPT OSS 120B | Scores the conversation (0-1000 PAICE scale) |

All four models are TEE-protected ("Private" classification on NEAR AI Cloud). If a primary model fails, the cascade automatically falls back to the secondary model.

## Quick Start

### Try the Demo

**Single-model demo** — Open `demo/index.html` in a browser, enter your [NEAR AI Cloud API key](https://cloud.near.ai), and walk through the full pipeline:

1. Chat with AI via TEE-protected inference
2. Generate assessment scores
3. Hash the score payload (SHA-256)
4. Write attestation to NEAR (testnet by default, switchable to mainnet)
5. Verify the attestation on-chain

**Cascade demo** — Open `demo/cascade.html` for the three-layer architecture:

1. Chat via TEE-protected cascade (GPT OSS 120B)
2. Middleware QA check (Qwen3 30B)
3. Generate assessment scores (GLM 4.7)
4. Hash score payload (SHA-256)
5. Write attestation to NEAR (testnet by default, switchable to mainnet)
6. Verify on-chain

Both demos default to the testnet contract for evaluation. Switch the network dropdown to "Mainnet" and enter `paice.near` to use the production contract.

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

# Testnet (demo)
service = AttestationService(
    contract_id="e756da-291226-1771097746.nearplay.testnet",
    network="testnet"
)

# Mainnet (production)
# service = AttestationService(contract_id="paice.near", network="mainnet")

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
    near_service.py              # Python service (inference + attestation + cascade)
    near_config.py               # Configuration management
    examples/
      test_near_ai.py            # NEAR AI Cloud test script
      test_attestation.py        # Contract verification test
  demo/
    index.html                   # Single-model interactive demo
    cascade.html                 # Three-layer cascade demo
  docs/
    architecture.md              # Integration architecture & cascade design
```

## Deployed Contracts

### Testnet (Hackathon Demo)

| Field | Value |
|-------|-------|
| Address | `e756da-291226-1771097746.nearplay.testnet` |
| Network | NEAR Testnet |
| Explorer | [View on NearBlocks](https://testnet.nearblocks.io/address/e756da-291226-1771097746.nearplay.testnet) |
| Methods | `attest()`, `verify()`, `get_attestation_count()` |
| Deployed via | [nearplay.app](https://nearplay.app) |

### Mainnet (Production)

| Field | Value |
|-------|-------|
| Address | `paice.near` |
| Network | NEAR Mainnet |
| Explorer | [View on NearBlocks](https://nearblocks.io/address/paice.near) |
| Methods | `attest()`, `verify()`, `get_attestation_count()` |

The mainnet contract at `paice.near` is deployed for production use within the PAICE platform. The testnet contract is used for the interactive demos in this repository.

## NEAR AI Cloud Models Used

### TEE-Protected ("Private") Models

These models run inside hardware-secured TEE enclaves. Conversation data is inaccessible to NEAR, the cloud provider, or PAICE during processing.

| Model | Cascade Role | Cost (Input/Output per M tokens) | Latency |
|-------|:---:|-------|-------|
| GPT OSS 120B | Chat (primary) | $0.15 / $0.55 | ~1-3s |
| Qwen3 30B | Middleware (primary) | $0.15 / $0.55 | ~1-2s |
| GLM 4.7 | Evaluation (primary) | $0.85 / $3.30 | ~15-20s |
| DeepSeek V3.1 | Fallback (chat/middleware) | $1.05 / $3.10 | ~1-3s |

### Anonymised Models

These models are proxied through NEAR AI Cloud but do not run in TEE enclaves.

| Model | Cost (Input/Output per M tokens) |
|-------|-------|
| GPT-5.2 | $1.80 / $15.50 |

## Model Cascade Architecture

The cascade separates concerns to match PAICE's production architecture:

```
User Message
     |
     v
+-----------------------+
|  CHAT LAYER           |  GPT OSS 120B (primary)
|  Conducts the         |  DeepSeek V3.1 (fallback)
|  assessment           |
+-----------+-----------+
            | AI response
            v
+-----------------------+
|  MIDDLEWARE LAYER      |  Qwen3 30B (primary)
|  QA validation         |  DeepSeek V3.1 (fallback)
|  of AI responses       |
+-----------+-----------+
            | (after conversation complete)
            v
+-----------------------+
|  EVAL LAYER           |  GLM 4.7 (primary, 2000 max_tokens)
|  Scores across        |  GPT OSS 120B (fallback)
|  5 PAICE dimensions   |
+-----------------------+
```

**Why these models?**

- **GPT OSS 120B for chat**: Fast (~1-2s), naturally probes all 5 PAICE dimensions, excellent conversational quality
- **Qwen3 30B for middleware**: 4/4 accuracy on error injection detection tests, sub-2s latency, cheapest option
- **GLM 4.7 for evaluation**: Most calibrated scorer in testing (550/1000 for a rich 5-turn conversation vs GPT OSS's generous 700/1000). Uses extensive internal reasoning before scoring. Best equivalent to production PAICE's evaluation models

## PAICE Scoring System

Scores are stored on a 0-100 scale internally and displayed on a 0-1000 scale:

| Display Score | Tier | Description |
|:---:|-------|-------|
| 900-1000 | Exceptional | Catches subtle issues, innovative approaches, meta-aware |
| 700-899 | Advanced | Systematic verification, proactive refinement, demonstrates learning |
| 500-699 | Proficient | Regular iteration, consistent verification, adapts to feedback |
| 300-499 | Informed | Some task clarity, occasional verification, inconsistent follow-through |
| 0-299 | Constrained | Minimal engagement, no iteration, surface-level interaction |

**Calibration**: Most typical conversations score 200-400. Productive conversations score 400-550. Only sustained, high-quality exchanges with clear evidence of verification, iteration, and learning reach 600+.

## How Verification Works

1. Obtain the assessment score payload (session ID, dimensional scores, tier, timestamp, cascade models used)
2. Serialize as JSON with sorted keys
3. Compute SHA-256: `sha256:<hex>`
4. Call `verify(session_id)` on the contract via NEAR RPC
5. Compare the returned `score_hash` with your computed hash
6. If they match, the scores are authentic and untampered

## Environment Variables

```env
# NEAR AI Cloud (get key at https://cloud.near.ai)
NEAR_AI_API_KEY=sk-your-api-key
NEAR_AI_ENABLED=true

# Cascade configuration
NEAR_CASCADE_CHAT_MODEL=openai/gpt-oss-120b
NEAR_CASCADE_CHAT_FALLBACK=deepseek-ai/DeepSeek-V3.1
NEAR_CASCADE_MIDDLEWARE_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
NEAR_CASCADE_MIDDLEWARE_FALLBACK=deepseek-ai/DeepSeek-V3.1
NEAR_CASCADE_EVAL_MODEL=zai-org/GLM-4.7
NEAR_CASCADE_EVAL_FALLBACK=openai/gpt-oss-120b

# Assessment Attestation Contract
# Testnet (demo):
NEAR_CONTRACT_ID=e756da-291226-1771097746.nearplay.testnet
NEAR_NETWORK=testnet
# Mainnet (production):
# NEAR_CONTRACT_ID=paice.near
# NEAR_NETWORK=mainnet
NEAR_PREFER_TEE=true
```

## Why NEAR?

This integration can only work with NEAR's unique combination of:
- **NEAR AI Cloud**: TEE-protected inference with hardware attestation — 4 text models running in secure enclaves
- **NEAR Blockchain**: On-chain state for immutable attestations
- **Account Model**: Named accounts like `paice.near` instead of hex strings
- **Low Fees**: Testnet deployments are free; mainnet attestations cost fractions of a cent

## License

MIT

## About PAICE

PAICE (Privacy-preserving AI Collaboration Effectiveness) is a production application that assesses how effectively people collaborate with AI. It uses adaptive conversational assessment with embedded behavioral tests across five dimensions: Performance, Accountability, Integrity, Collaboration, and Evolution.

The main application is deployed at [paice.work](https://paice.work). This repo contains only the NEAR Protocol integration layer.

Built by [Snap Synapse](https://snapsynapse.com) for NEARCON Innovation Sandbox 2026.
