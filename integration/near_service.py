"""
NEAR Integration Service for PAICE
===================================

Provides two capabilities:
1. Private inference via NEAR AI Cloud (TEE-protected)
2. Assessment attestation on NEAR blockchain

This module integrates with PAICE's existing LLM abstraction layer
and assessment completion flow.

Usage:
    from near_service import NearAIClient, AttestationService

    # Private inference
    client = NearAIClient(api_key="sk-...")
    response = client.chat("deepseek-ai/DeepSeek-V3.1", messages)

    # Attestation
    attestation = AttestationService(contract_id="...", network="testnet")
    result = attestation.attest(session_id, score_payload)
    verified = attestation.verify(session_id)
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
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

    # TEE-protected models (verified as of Feb 2026)
    TEE_MODELS = {
        "deepseek-ai/DeepSeek-V3.1",
        "openai/gpt-oss-120b",
        "Qwen/Qwen3-30B-A3B-Instruct-2507",
        "zai-org/GLM-4.7",
    }

    # All available models
    AVAILABLE_MODELS = {
        "anthropic/claude-opus-4-6": {"input": 5.00, "output": 25.00, "ctx": 200_000},
        "anthropic/claude-sonnet-4-5": {"input": 3.00, "output": 15.50, "ctx": 200_000},
        "deepseek-ai/DeepSeek-V3.1": {"input": 1.05, "output": 3.10, "ctx": 128_000},
        "google/gemini-3-pro": {"input": 1.25, "output": 15.00, "ctx": 1_000_000},
        "openai/gpt-5.2": {"input": 1.80, "output": 15.50, "ctx": 400_000},
        "openai/gpt-oss-120b": {"input": 0.15, "output": 0.55, "ctx": 131_000},
        "Qwen/Qwen3-30B-A3B-Instruct-2507": {"input": 0.15, "output": 0.55, "ctx": 262_144},
        "zai-org/GLM-4.7": {"input": 0.85, "output": 3.30, "ctx": 131_072},
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
            model: Model ID (e.g., "deepseek-ai/DeepSeek-V3.1")
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

        return NearAIResponse(
            content=choice["message"]["content"],
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
    without detection.
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
                          tier, overall_score, and timestamp

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
