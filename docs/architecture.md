# PAICE + NEAR Integration Architecture

## Overview

PAICE (Privacy-preserving AI Collaboration Effectiveness) integrates with NEAR
Protocol at two layers to provide verifiable privacy guarantees for AI-powered
assessments, plus a three-layer model cascade for separation of concerns.

## Architecture Diagram

```
                         PAICE Architecture with NEAR Integration

User Browser                    PAICE Backend                    NEAR Ecosystem
+------------------+      +----------------------+      +-------------------------+
|                  |      |                      |      |                         |
|  Assessment UI   |----->|  FastAPI Server       |      |  NEAR AI Cloud          |
|                  |      |                      |      |  (TEE-protected)        |
|  - Chat input    |      |  +----------------+  |      |  +-------------------+  |
|  - Score display |      |  | Cascade        |  |      |  | CHAT LAYER        |  |
|  - Cascade info  |      |  | Controller     |-------->|  | GPT OSS 120B      |  |
|  - NEAR badge    |      |  +-------+--------+  |      |  | -> DeepSeek V3.1  |  |
|  - Explorer link |      |  |   |         |     |      |  +-------------------+  |
|                  |      |  |   v         |     |      |  | MIDDLEWARE LAYER   |  |
+------------------+      |  | Middleware  |     |      |  | Qwen3 30B         |  |
                          |  | QA Layer   |------+----->|  | -> DeepSeek V3.1  |  |
                          |  +-------+--------+  |      |  +-------------------+  |
                          |          |           |      |  | EVAL LAYER        |  |
                          |  +-------v--------+  |      |  | GLM 4.7           |  |
                          |  | Scoring Engine |-------->|  | -> GPT OSS 120B   |  |
                          |  | (5 dimensions) |  |      |  +-------------------+  |
                          |  +-------+--------+  |      |                         |
                          |          |           |      |  NEAR Blockchain        |
                          |  +-------v--------+  |      |  (testnet / mainnet)    |
                          |  | NEAR Service   |-------->|  +-------------------+  |
                          |  | - hash payload |  |      |  | Attestation       |  |
                          |  | - attest()     |  |      |  | Contract          |  |
                          |  | - verify()     |  |      |  |                   |  |
                          |  +----------------+  |      |  | attest()          |  |
                          |                      |      |  | verify()          |  |
                          +----------------------+      |  | get_count()       |  |
                                                        |  +-------------------+  |
                                                        +-------------------------+
```

## Model Cascade Architecture

The cascade separates concerns across three layers, mirroring PAICE's production
architecture where different models serve different roles:

```
User Message
     |
     v
+---------------------------+
|  CHAT LAYER               |
|  Primary: GPT OSS 120B    |  Conducts the PAICE assessment conversation
|  Fallback: DeepSeek V3.1  |  Probes 5 dimensions: P-A-I-C-E
|  Latency: ~1-3s           |
|  Temp: 0.7                |
+---------------------------+
     |
     v AI response
+---------------------------+
|  MIDDLEWARE LAYER          |
|  Primary: Qwen3 30B       |  Validates AI response quality:
|  Fallback: DeepSeek V3.1  |  - Relevant probing question?
|  Latency: ~1-2s           |  - On-topic for assessment?
|  Temp: 0.2                |  - No scoring criteria leaked?
|  Optional (toggle)        |  - Appropriately concise?
+---------------------------+
     |
     v (after conversation complete)
+---------------------------+
|  EVALUATION LAYER         |
|  Primary: GLM 4.7         |  Scores across 5 PAICE dimensions
|  Fallback: GPT OSS 120B   |  Uses PAICE calibration anchors
|  Latency: ~15-20s         |  Stored: 0-100, Display: 0-1000
|  Temp: 0.3                |  Tier assignment (C/I/P/A/E)
|  max_tokens: 2000         |
+---------------------------+
```

### Why These Models?

**GPT OSS 120B (Chat)**: Selected for conversational quality. In testing, it
naturally probes all 5 PAICE dimensions without explicit prompting, produces
concise 2-3 sentence responses, and self-summarizes after 4 turns. At $0.15/M
input tokens, it's also the cheapest option.

**Qwen3 30B (Middleware)**: Achieved 4/4 on error injection detection tests:
- Explicit error catch: true (correct)
- Error not caught by user: false (correct)
- Ambiguous phrasing: false (correct)
- Subtle catch with correction: true (correct)

Sub-2s latency makes it invisible to the user experience.

**GLM 4.7 (Evaluation)**: Most calibrated scorer. In a rich 5-turn conversation
with demonstrated error-catching and learning, GLM scored 550/1000 (Proficient)
compared to GPT OSS's generous 700/1000 (Advanced). GLM uses extensive internal
reasoning (~600 words) before producing scores, making it the closest equivalent
to PAICE's production evaluation models (Claude Opus, GPT-5.2). Requires
`max_tokens: 2000` to accommodate its reasoning process.

### Fallback Behavior

Each layer has an automatic fallback:
1. Primary model is called first
2. If it fails (API error, empty content, timeout), the fallback model is called
3. The UI indicates when a fallback was used (orange status dot instead of green)
4. Cascade statistics track primary vs fallback usage

### Model Classification on NEAR AI Cloud

NEAR AI Cloud classifies models into two categories:

- **Private**: Runs inside TEE enclaves. Conversation data is hardware-isolated.
  Models: DeepSeek V3.1, Qwen3 30B, GPT OSS 120B, GLM 4.7
- **Anonymised**: Proxied to external providers. Not TEE-protected.
  Models: Claude Opus 4.6, Claude Sonnet 4.5, GPT-5.2, Gemini 3 Pro

All models in the PAICE cascade are "Private" (TEE-protected).

## Layer 1: Assessment Attestation (On-Chain)

### Purpose
After an assessment is completed and scored, the score payload is hashed
(SHA-256) and written to a NEAR smart contract. This creates a tamper-proof
record that anyone can verify.

### Flow
1. User completes assessment chat (via cascade chat layer)
2. Middleware validates AI response quality (optional)
3. Evaluation layer generates dimensional scores and tier
4. Score payload is canonicalized (JSON with sorted keys)
5. SHA-256 hash is computed
6. `attest(session_id, score_hash)` is called on the contract
7. Transaction hash is returned to the client
8. Results page shows "Verified on NEAR" badge with explorer link

### Attestation Payload

The on-chain attestation includes cascade metadata:

```json
{
  "session_id": "paice-1771107293691-8x2ra...",
  "score": 320,
  "stored_score": 32,
  "tier": "Informed",
  "dimensions": {
    "Performance": 350,
    "Accountability": 300,
    "Integrity": 300,
    "Collaboration": 320,
    "Evolution": 300
  },
  "eval_model": "GLM 4.7",
  "cascade": {
    "chat": "GPT OSS 120B",
    "middleware": "Qwen3 30B",
    "eval": "GLM 4.7"
  },
  "timestamp": 1771107293691
}
```

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
2. PAICE backend sends it to NEAR AI Cloud API (cascade chat layer)
3. NEAR AI routes to a TEE-protected model (GPT OSS 120B)
4. The model runs inside a hardware-secured enclave (NVIDIA H100/H200)
5. Neither NEAR, the cloud provider, nor PAICE can access the raw conversation
6. Response passes through middleware QA (Qwen3 30B, also TEE-protected)
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
- `openai/gpt-oss-120b` - Chat layer primary (fast, cheap)
- `Qwen/Qwen3-30B-A3B-Instruct-2507` - Middleware primary (fast, accurate QA)
- `zai-org/GLM-4.7` - Evaluation primary (best calibration, reasoning model)
- `deepseek-ai/DeepSeek-V3.1` - Fallback for chat and middleware

## PAICE Scoring System

### Storage vs Display Scale
- **Storage**: 0-100 (internal, used in computations)
- **Display**: 0-1000 (user-facing, multiply storage by 10)

### Tiers
| Code | Tier | Display Range |
|------|------|:---:|
| E | Exceptional | 900-1000 |
| A | Advanced | 700-899 |
| P | Proficient | 500-699 |
| I | Informed | 300-499 |
| C | Constrained | 0-299 |

### Calibration
Scoring prompts include calibration anchors from PAICE production:
- Default unobserved subscores to 30 (300 display)
- Most typical conversations: 20-40 stored (200-400 display)
- Productive conversations: 40-55 stored (400-550 display)
- Only sustained high-quality exchanges reach 60+ stored (600+ display)

### Five Dimensions (P-A-I-C-E)
- **Performance**: How they frame tasks and evaluate results
- **Accountability**: How they verify outputs and handle errors
- **Integrity**: How they maintain accuracy and context
- **Collaboration**: How they iterate and refine with AI
- **Evolution**: How they learn and adapt their approach

## Privacy Guarantees

| Claim | Mechanism | Verifiable? |
|-------|-----------|-------------|
| Conversations aren't stored | TEE-protected inference (all cascade layers) | Yes (TEE attestation) |
| Scores aren't tampered with | On-chain hash | Yes (anyone can verify) |
| AI runs in secure hardware | NEAR AI Cloud TEEs | Yes (hardware attestation) |
| No PII in storage | PAICE architecture | Yes (audit the codebase) |
| Cascade models identified | Attestation payload | Yes (on-chain record) |

## Deployed Contracts

### Testnet (Hackathon Demo)
- **Address:** `paice-demo.testnet`
- **Network:** NEAR Testnet
- **Explorer:** https://testnet.nearblocks.io/address/paice-demo.testnet
- **Deployed via:** NEAR CLI (`near-cli-rs`)

### Mainnet (Production)
- **Address:** `paice.near`
- **Network:** NEAR Mainnet
- **Explorer:** https://nearblocks.io/address/paice.near

The testnet contract is fully operational and used by all three demos. Attestations are signed
client-side via `near-api-js` (v4.0.4) with an embedded testnet keypair — testnet NEAR has zero
monetary value, so key exposure is safe. The mainnet account `paice.near` is registered and funded,
with the same contract deployed for production use.
