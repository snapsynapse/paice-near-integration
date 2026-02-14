"""
NEAR Integration Service for PAICE
===================================

Provides three capabilities:
1. Private inference via NEAR AI Cloud (TEE-protected)
2. Assessment attestation on NEAR blockchain
3. Three-layer model cascade (chat, middleware, evaluation)

Usage:
    from near_service import NearAIClient, AttestationService, CascadeController

    # Direct inference
    client = NearAIClient(api_key="sk-...")
    response = client.chat("openai/gpt-oss-120b", messages)

    # Cascade (chat -> middleware -> eval)
    cascade = CascadeController(client, config)
    chat_result = cascade.chat(messages)
    mw_result = cascade.middleware_check(ai_response)
    eval_result = cascade.evaluate(messages)

    # Attestation
    attestation = AttestationService(contract_id="...", network="testnet")
    result = attestation.attest(session_id, score_payload)
    verified = attestation.verify(session_id)
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# =========================================================
# NEAR AI Cloud - Private Inference
# =========================================================

@dataclass
class NearAIResponse:
    """Response from NEAR AI Cloud inference."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


class NearAIClient:
    """
    OpenAI-compatible client for NEAR AI Cloud.

    All inference runs inside TEE (Trusted Execution Environment)
    enclaves on NVIDIA H100/H200 hardware. Conversations are
    processed in hardware-secured memory that is inaccessible
    to the cloud provider, NEAR, or anyone else.
    """

    BASE_URL = "https://cloud-api.near.ai/v1"

    # TEE-protected ("Private") models (verified as of Feb 2026)
    TEE_MODELS = {
        "deepseek-ai/DeepSeek-V3.1",
        "openai/gpt-oss-120b",
        "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "zai-org/GLM-4.7",
    }

    # Anonymised models (proxied, not TEE-protected)
    ANONYMISED_MODELS = {
        "anthropic/claude-opus-4-6",
        "anthropic/claude-sonnet-4-5",
        "openai/gpt-5.2",
        "google/gemini-3-pro",
    }

    # All available models with pricing (per million tokens)
    AVAILABLE_MODELS = {
        "deepseek-ai/DeepSeek-V3.1": {"input": 1.05, "output": 3.10, "ctx": 128_000, "tee": True},
        "openai/gpt-oss-120b": {"input": 0.15, "output": 0.55, "ctx": 131_000, "tee": True},
        "Qwen/Qwen3-30B-A3B-Instruct-2507": {"input": 0.15, "output": 0.55, "ctx": 262_144, "tee": True},
        "zai-org/GLM-4.7": {"input": 0.85, "output": 3.30, "ctx": 131_072, "tee": True},
        "anthropic/claude-opus-4-6": {"input": 5.00, "output": 25.00, "ctx": 200_000, "tee": False},
        "anthropic/claude-sonnet-4-5": {"input": 3.00, "output": 15.50, "ctx": 200_000, "tee": False},
        "openai/gpt-5.2": {"input": 1.80, "output": 15.50, "ctx": 400_000, "tee": False},
        "google/gemini-3-pro": {"input": 1.25, "output": 15.00, "ctx": 1_000_000, "tee": False},
    }

    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> NearAIResponse:
        """
        Send a chat completion request via NEAR AI Cloud.

        Args:
            model: Model ID (e.g., "openai/gpt-oss-120b")
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response

        Returns:
            NearAIResponse with content and usage metadata
        """
        is_tee = model in self.TEE_MODELS
        logger.info(
            f"NEAR AI Cloud request: model={model}, "
            f"tee={'yes' if is_tee else 'no'}, "
            f"messages={len(messages)}"
        )

        resp = self.client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        content = choice["message"].get("content")

        # Handle reasoning models (GLM 4.7) that may exhaust tokens on thinking
        if not content:
            reasoning = choice["message"].get("reasoning_content", "")
            raise ValueError(
                f"Model {model} returned empty content "
                f"(reasoning tokens: {len(reasoning.split())} words). "
                f"Increase max_tokens or use a different model."
            )

        return NearAIResponse(
            content=content,
            model=data.get("model", model),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "unknown"),
        )

    def is_tee_protected(self, model: str) -> bool:
        """Check if a model runs inside a TEE enclave."""
        return model in self.TEE_MODELS

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models on NEAR AI Cloud."""
        resp = self.client.get("/models")
        resp.raise_for_status()
        return resp.json()["data"]

    def close(self):
        self.client.close()


# =========================================================
# Cascade Controller
# =========================================================

@dataclass
class CascadeResult:
    """Result from a cascade layer call."""
    content: str
    model: str
    model_id: str
    used_fallback: bool
    input_tokens: int
    output_tokens: int
    latency: float
    cost: float


@dataclass
class CascadeStats:
    """Statistics for cascade layer usage."""
    calls: int = 0
    fallbacks: int = 0
    flagged: int = 0  # middleware only
    last_model: Optional[str] = None


class CascadeController:
    """
    Three-layer model cascade for PAICE assessment.

    Layers:
    - Chat: Conducts the assessment conversation (GPT OSS 120B)
    - Middleware: QA validation of AI responses (Qwen3 30B)
    - Evaluation: Scores the conversation (GLM 4.7)

    Each layer has a primary and fallback model. If the primary
    fails, the fallback is automatically tried.
    """

    def __init__(self, client: NearAIClient, config=None):
        """
        Initialize the cascade controller.

        Args:
            client: NearAIClient instance
            config: CascadeConfig from near_config.py (or None for defaults)
        """
        self.client = client

        if config is None:
            from near_config import CascadeConfig
            config = CascadeConfig()

        self.config = config
        self.stats = {
            "chat": CascadeStats(),
            "middleware": CascadeStats(),
            "eval": CascadeStats(),
        }

    def _call_with_fallback(
        self,
        layer: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        primary_model: str,
        fallback_model: str,
    ) -> CascadeResult:
        """
        Call a model with automatic fallback.

        Tries the primary model first. If it fails (API error,
        empty content, timeout), falls back to the secondary model.
        """
        pricing = self.client.AVAILABLE_MODELS

        # Try primary
        start = time.time()
        try:
            logger.info(f"[{layer}] Calling primary: {primary_model}")
            response = self.client.chat(
                model=primary_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start

            p = pricing.get(primary_model, {"input": 1.0, "output": 3.0})
            cost = (response.input_tokens * p["input"] + response.output_tokens * p["output"]) / 1e6

            self.stats[layer].calls += 1
            self.stats[layer].last_model = primary_model.split("/")[-1]

            logger.info(f"[{layer}] Primary responded in {elapsed:.1f}s")

            return CascadeResult(
                content=response.content,
                model=primary_model.split("/")[-1],
                model_id=primary_model,
                used_fallback=False,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency=elapsed,
                cost=cost,
            )

        except Exception as primary_err:
            logger.warning(f"[{layer}] Primary failed: {primary_err}")

            # Try fallback
            start = time.time()
            try:
                logger.info(f"[{layer}] Falling back to: {fallback_model}")
                response = self.client.chat(
                    model=fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.time() - start

                p = pricing.get(fallback_model, {"input": 1.0, "output": 3.0})
                cost = (response.input_tokens * p["input"] + response.output_tokens * p["output"]) / 1e6

                self.stats[layer].calls += 1
                self.stats[layer].fallbacks += 1
                self.stats[layer].last_model = fallback_model.split("/")[-1]

                logger.info(f"[{layer}] Fallback responded in {elapsed:.1f}s")

                return CascadeResult(
                    content=response.content,
                    model=fallback_model.split("/")[-1],
                    model_id=fallback_model,
                    used_fallback=True,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency=elapsed,
                    cost=cost,
                )

            except Exception as fallback_err:
                raise RuntimeError(
                    f"[{layer}] Both models failed. "
                    f"Primary ({primary_model}): {primary_err}. "
                    f"Fallback ({fallback_model}): {fallback_err}"
                )

    def chat(self, messages: List[Dict[str, str]]) -> CascadeResult:
        """
        Chat layer: conduct the assessment conversation.

        Uses GPT OSS 120B (primary) or DeepSeek V3.1 (fallback).
        """
        cfg = self.config.chat
        return self._call_with_fallback(
            layer="chat",
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            primary_model=cfg.primary,
            fallback_model=cfg.fallback,
        )

    def middleware_check(self, ai_response: str, exchange_count: int) -> Optional[Dict]:
        """
        Middleware layer: QA validation of AI response.

        Uses Qwen3 30B (primary) or DeepSeek V3.1 (fallback).

        Returns:
            Dict with {"pass": bool, "note": str} or None if middleware disabled.
        """
        if not self.config.middleware_enabled:
            return None

        mw_messages = [
            {
                "role": "system",
                "content": (
                    "You are a PAICE quality assurance middleware. "
                    "Analyze the AI assessor's latest response and check for: "
                    "1. Did the assessor ask a relevant probing question? "
                    "2. Is the response staying on-topic for AI collaboration assessment? "
                    "3. Did the assessor avoid giving away scoring criteria? "
                    "4. Is the response appropriately concise (not too long/short)? "
                    'Respond with brief JSON: {"pass": true/false, "note": "brief reason"}.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f'AI assessor\'s latest response: "{ai_response}"\n\n'
                    f"Context: This is exchange #{exchange_count} of a PAICE "
                    f"AI collaboration assessment. Evaluate quality."
                ),
            },
        ]

        try:
            cfg = self.config.middleware
            result = self._call_with_fallback(
                layer="middleware",
                messages=mw_messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                primary_model=cfg.primary,
                fallback_model=cfg.fallback,
            )

            import re
            json_match = re.search(r"\{[\s\S]*\}", result.content)
            if json_match:
                mw_data = json.loads(json_match.group())
                passed = mw_data.get("pass", True)
                if not passed:
                    self.stats["middleware"].flagged += 1
                return mw_data

        except Exception as err:
            logger.warning(f"[middleware] Skipped: {err}")

        return None

    def evaluate(self, messages: List[Dict[str, str]]) -> CascadeResult:
        """
        Evaluation layer: score the conversation across 5 PAICE dimensions.

        Uses GLM 4.7 (primary) or GPT OSS 120B (fallback).
        GLM 4.7 needs max_tokens=2000 for its reasoning process.
        """
        eval_prompt = {
            "role": "user",
            "content": (
                "You are the PAICE Evaluator. Analyze the conversation and "
                "score 5 collaboration dimensions on a 0-100 scale.\n\n"
                "SCORING CALIBRATION (critical - do not inflate):\n"
                "- 0-29: Constrained - minimal engagement, no iteration\n"
                "- 30-49: Informed - some task clarity, occasional verification\n"
                "- 50-69: Proficient - regular iteration, consistent verification\n"
                "- 70-89: Advanced - systematic verification, proactive refinement\n"
                "- 90-100: Exceptional - catches subtle issues, innovative approaches\n\n"
                "IMPORTANT: Most typical conversations score 20-40. Productive "
                "conversations score 40-55. Score only demonstrated behaviors. "
                "Absence of evidence = default to 30. Short conversations with "
                "only 1-3 exchanges should rarely exceed 40 overall. "
                "Do NOT artificially inflate.\n\n"
                "DIMENSIONS:\n"
                "- Performance: How they frame tasks and evaluate results\n"
                "- Accountability: How they verify outputs and handle errors\n"
                "- Integrity: How they maintain accuracy and context\n"
                "- Collaboration: How they iterate and refine with AI\n"
                "- Evolution: How they learn and adapt their approach\n\n"
                "Return ONLY valid JSON in this exact format:\n"
                '{"overall_score": 35, "dimensions": {"Performance": 38, '
                '"Accountability": 30, "Integrity": 35, "Collaboration": 32, '
                '"Evolution": 30}, "summary": "Brief 1-sentence assessment summary"}'
            ),
        }

        cfg = self.config.eval
        return self._call_with_fallback(
            layer="eval",
            messages=[*messages, eval_prompt],
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            primary_model=cfg.primary,
            fallback_model=cfg.fallback,
        )

    def get_cascade_info(self) -> Dict[str, Any]:
        """Get current cascade configuration and statistics."""
        return {
            "layers": {
                "chat": {
                    "primary": self.config.chat.primary,
                    "fallback": self.config.chat.fallback,
                    "stats": {
                        "calls": self.stats["chat"].calls,
                        "fallbacks": self.stats["chat"].fallbacks,
                        "last_model": self.stats["chat"].last_model,
                    },
                },
                "middleware": {
                    "primary": self.config.middleware.primary,
                    "fallback": self.config.middleware.fallback,
                    "enabled": self.config.middleware_enabled,
                    "stats": {
                        "calls": self.stats["middleware"].calls,
                        "fallbacks": self.stats["middleware"].fallbacks,
                        "flagged": self.stats["middleware"].flagged,
                        "last_model": self.stats["middleware"].last_model,
                    },
                },
                "eval": {
                    "primary": self.config.eval.primary,
                    "fallback": self.config.eval.fallback,
                    "stats": {
                        "calls": self.stats["eval"].calls,
                        "fallbacks": self.stats["eval"].fallbacks,
                        "last_model": self.stats["eval"].last_model,
                    },
                },
            },
        }


# =========================================================
# PAICE Scoring Utilities
# =========================================================

def get_tier(stored_score: float) -> Dict[str, Any]:
    """
    Convert a stored score (0-100) to PAICE display scale (0-1000) and tier.

    Args:
        stored_score: Score on 0-100 scale

    Returns:
        Dict with code, label, and display score
    """
    display = round(stored_score * 10)
    if display >= 900:
        return {"code": "E", "label": "Exceptional", "display": display}
    if display >= 700:
        return {"code": "A", "label": "Advanced", "display": display}
    if display >= 500:
        return {"code": "P", "label": "Proficient", "display": display}
    if display >= 300:
        return {"code": "I", "label": "Informed", "display": display}
    return {"code": "C", "label": "Constrained", "display": display}


# =========================================================
# Assessment Attestation
# =========================================================

@dataclass
class AttestationResult:
    """Result of writing an attestation to NEAR."""
    session_id: str
    score_hash: str
    contract_id: str
    network: str
    timestamp: str


@dataclass
class VerificationResult:
    """Result of verifying an on-chain attestation."""
    found: bool
    attester: Optional[str] = None
    score_hash: Optional[str] = None
    timestamp: Optional[int] = None


class AttestationService:
    """
    Writes and verifies assessment attestations on NEAR blockchain.

    Each attestation stores a SHA-256 hash of the score payload,
    making it impossible to modify assessment results after the fact
    without detection. The payload includes cascade metadata (which
    models were used for chat, middleware, and evaluation).
    """

    RPC_URLS = {
        "testnet": "https://rpc.testnet.near.org",
        "mainnet": "https://rpc.mainnet.near.org",
    }

    def __init__(self, contract_id: str, network: str = "testnet"):
        self.contract_id = contract_id
        self.network = network
        self.rpc_url = self.RPC_URLS[network]

    @staticmethod
    def compute_hash(score_payload: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of a canonical score payload.

        The payload is JSON-serialized with sorted keys to ensure
        deterministic hashing regardless of dict ordering.

        Args:
            score_payload: Dict containing session_id, dimensional_scores,
                          tier, overall_score, cascade info, and timestamp

        Returns:
            Hash string in format "sha256:<hex>"
        """
        canonical = json.dumps(score_payload, sort_keys=True, separators=(",", ":"))
        hash_hex = hashlib.sha256(canonical.encode()).hexdigest()
        return f"sha256:{hash_hex}"

    def verify(self, session_id: str) -> VerificationResult:
        """
        Verify an attestation exists on-chain for a given session.

        Makes a view call to the smart contract (no gas required).

        Args:
            session_id: The assessment session ID to verify

        Returns:
            VerificationResult with attestation data if found
        """
        import base64

        args = json.dumps({"session_id": session_id})
        args_b64 = base64.b64encode(args.encode()).decode()

        resp = httpx.post(
            self.rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "verify",
                "method": "query",
                "params": {
                    "request_type": "call_function",
                    "finality": "final",
                    "account_id": self.contract_id,
                    "method_name": "verify",
                    "args_base64": args_b64,
                },
            },
        )

        data = resp.json()
        if "result" in data and "result" in data["result"]:
            raw = bytes(data["result"]["result"]).decode()
            attestation = json.loads(raw)
            if attestation:
                return VerificationResult(
                    found=True,
                    attester=attestation["attester"],
                    score_hash=attestation["score_hash"],
                    timestamp=attestation["timestamp"],
                )

        return VerificationResult(found=False)

    def get_attestation_count(self) -> int:
        """Get the total number of attestations on the contract."""
        import base64

        args_b64 = base64.b64encode(b"{}").decode()

        resp = httpx.post(
            self.rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "count",
                "method": "query",
                "params": {
                    "request_type": "call_function",
                    "finality": "final",
                    "account_id": self.contract_id,
                    "method_name": "get_attestation_count",
                    "args_base64": args_b64,
                },
            },
        )

        data = resp.json()
        if "result" in data and "result" in data["result"]:
            raw = bytes(data["result"]["result"]).decode()
            return int(raw)

        return 0

    def get_explorer_url(self, tx_hash: Optional[str] = None) -> str:
        """Get the block explorer URL for the contract or a transaction."""
        base = (
            "https://testnet.nearblocks.io"
            if self.network == "testnet"
            else "https://nearblocks.io"
        )
        if tx_hash:
            return f"{base}/txns/{tx_hash}"
        return f"{base}/address/{self.contract_id}"
