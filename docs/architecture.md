# PAICE + NEAR Integration Architecture

## Overview

PAICE (Privacy-preserving AI Collaboration Effectiveness) integrates with NEAR
Protocol at two layers to provide verifiable privacy guarantees for AI-powered
assessments.

## Architecture Diagram

```
                         PAICE Architecture with NEAR Integration

User Browser                    PAICE Backend                    NEAR Ecosystem
+------------------+      +----------------------+      +-------------------------+
|                  |      |                      |      |                         |
|  Assessment UI   |----->|  FastAPI Server       |      |  NEAR AI Cloud          |
|                  |      |                      |      |  (TEE-protected)        |
|  - Chat input    |      |  +----------------+  |      |  +-------------------+  |
|  - Score display |      |  | LLM Service    |-------->|  | DeepSeek V3.1     |  |
|  - NEAR badge    |      |  | (cascade)      |  |      |  | Qwen3 30B         |  |
|  - Explorer link |      |  +----------------+  |      |  | GPT OSS 120B      |  |
|                  |      |                      |      |  +-------------------+  |
+------------------+      |  +----------------+  |      |                         |
                          |  | Scoring Engine |  |      |  NEAR Blockchain        |
                          |  | (5 dimensions) |  |      |  (testnet)              |
                          |  +-------+--------+  |      |  +-------------------+  |
                          |          |           |      |  | Attestation       |  |
                          |  +-------v--------+  |      |  | Contract          |  |
                          |  | NEAR Service   |-------->|  |                   |  |
                          |  | - hash payload |  |      |  | attest()          |  |
                          |  | - attest()     |  |      |  | verify()          |  |
                          |  | - verify()     |  |      |  | get_count()       |  |
                          |  +----------------+  |      |  +-------------------+  |
                          |                      |      |                         |
                          +----------------------+      +-------------------------+
```

## Layer 1: Assessment Attestation (On-Chain)

### Purpose
After an assessment is completed and scored, the score payload is hashed
(SHA-256) and written to a NEAR smart contract. This creates a tamper-proof
record that anyone can verify.

### Flow
1. User completes assessment chat
2. Scoring engine generates dimensional scores and tier
3. Score payload is canonicalized (JSON with sorted keys)
4. SHA-256 hash is computed
5. `attest(session_id, score_hash)` is called on the contract
6. Transaction hash is returned to the client
7. Results page shows "Verified on NEAR" badge with explorer link

### Smart Contract
- **Language:** Rust (compiled to WebAssembly)
- **Framework:** NEAR SDK 5.6.0
- **Storage:** `LookupMap<String, Attestation>` - O(1) lookups by session ID
- **Methods:**
  - `attest(session_id, score_hash)` - Store attestation (state change, requires gas)
  - `verify(session_id)` - Read attestation (view call, free)
  - `get_attestation_count()` - Total attestations (view call, free)

### Verification
Anyone can verify an assessment by:
1. Obtaining the assessment score data
2. Computing the SHA-256 hash using the same canonical format
3. Calling `verify(session_id)` on the contract
4. Comparing the returned `score_hash` with the computed hash

## Layer 2: Private Inference via NEAR AI Cloud

### Purpose
Route AI inference through NEAR AI Private Cloud so that all conversation
processing happens inside Trusted Execution Environments (TEEs).

### How TEE Inference Works
1. User sends a message
2. PAICE backend sends it to NEAR AI Cloud API
3. NEAR AI routes to a TEE-protected model
4. The model runs inside a hardware-secured enclave (NVIDIA H100/H200)
5. Neither NEAR, the cloud provider, nor PAICE can access the raw conversation
6. Response is returned through the secure channel
7. Only the final assessment scores (not conversation content) are stored

### API Compatibility
NEAR AI Cloud uses the **OpenAI-compatible API format**:
- Base URL: `https://cloud-api.near.ai/v1`
- Endpoint: `POST /v1/chat/completions`
- Auth: `Authorization: Bearer <API_KEY>`

This means PAICE's existing LLM abstraction layer (`llm_service.py`) can
integrate NEAR AI as a provider with minimal code changes.

### TEE-Protected Models
As of February 2026, these models run in full TEE enclaves:
- `deepseek-ai/DeepSeek-V3.1` - Best balance of quality and cost
- `openai/gpt-oss-120b` - Budget option
- `Qwen/Qwen3-30B-A3B-Instruct-2507` - Budget option
- `zai-org/GLM-4.7` - Alternative

## Privacy Guarantees

| Claim | Mechanism | Verifiable? |
|-------|-----------|-------------|
| Conversations aren't stored | TEE-protected inference | Yes (TEE attestation) |
| Scores aren't tampered with | On-chain hash | Yes (anyone can verify) |
| AI runs in secure hardware | NEAR AI Cloud TEEs | Yes (hardware attestation) |
| No PII in storage | PAICE architecture | Yes (audit the codebase) |

## Deployed Contract

- **Address:** `e756da-291226-1771097746.nearplay.testnet`
- **Network:** NEAR Testnet
- **Explorer:** https://testnet.nearblocks.io/address/e756da-291226-1771097746.nearplay.testnet
- **Deployed via:** [nearplay.app](https://nearplay.app)
