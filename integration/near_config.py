"""
NEAR Integration Configuration for PAICE
==========================================

Environment variables:
    NEAR_AI_API_KEY     - API key from cloud.near.ai
    NEAR_AI_ENABLED     - Enable NEAR AI Cloud inference (true/false)
    NEAR_CONTRACT_ID    - Assessment attestation contract address
    NEAR_NETWORK        - Network to use (testnet/mainnet)
    NEAR_AI_MODEL       - Default model for inference
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NearConfig:
    """Configuration for NEAR Protocol integration."""

    # NEAR AI Cloud (Private Inference)
    ai_api_key: str = ""
    ai_enabled: bool = False
    ai_model: str = "deepseek-ai/DeepSeek-V3.1"
    ai_fallback_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    ai_timeout: float = 30.0

    # Assessment Attestation (On-Chain)
    contract_id: str = ""
    network: str = "testnet"

    # TEE preference
    prefer_tee: bool = True

    @classmethod
    def from_env(cls) -> "NearConfig":
        """Load configuration from environment variables."""
        return cls(
            ai_api_key=os.getenv("NEAR_AI_API_KEY", ""),
            ai_enabled=os.getenv("NEAR_AI_ENABLED", "false").lower() == "true",
            ai_model=os.getenv("NEAR_AI_MODEL", "deepseek-ai/DeepSeek-V3.1"),
            ai_fallback_model=os.getenv(
                "NEAR_AI_FALLBACK_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"
            ),
            ai_timeout=float(os.getenv("NEAR_AI_TIMEOUT", "30.0")),
            contract_id=os.getenv("NEAR_CONTRACT_ID", ""),
            network=os.getenv("NEAR_NETWORK", "testnet"),
            prefer_tee=os.getenv("NEAR_PREFER_TEE", "true").lower() == "true",
        )

    @property
    def is_configured(self) -> bool:
        """Check if minimum configuration is present."""
        return bool(self.ai_api_key and self.contract_id)

    @property
    def env_template(self) -> str:
        """Generate .env template for this configuration."""
        return """# NEAR Protocol Integration
NEAR_AI_API_KEY=sk-your-api-key-here
NEAR_AI_ENABLED=true
NEAR_AI_MODEL=deepseek-ai/DeepSeek-V3.1
NEAR_AI_FALLBACK_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
NEAR_AI_TIMEOUT=30.0
NEAR_CONTRACT_ID=your-contract.nearplay.testnet
NEAR_NETWORK=testnet
NEAR_PREFER_TEE=true
"""
