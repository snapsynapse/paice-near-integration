"""
NEAR Integration Configuration for PAICE
==========================================

Environment variables:
    NEAR_AI_API_KEY                  - API key from cloud.near.ai
    NEAR_AI_ENABLED                  - Enable NEAR AI Cloud inference (true/false)
    NEAR_AI_TIMEOUT                  - Request timeout in seconds

    NEAR_CASCADE_CHAT_MODEL          - Primary chat model
    NEAR_CASCADE_CHAT_FALLBACK       - Fallback chat model
    NEAR_CASCADE_MIDDLEWARE_MODEL     - Primary middleware model
    NEAR_CASCADE_MIDDLEWARE_FALLBACK  - Fallback middleware model
    NEAR_CASCADE_MIDDLEWARE_ENABLED   - Enable middleware QA layer (true/false)
    NEAR_CASCADE_EVAL_MODEL          - Primary evaluation model
    NEAR_CASCADE_EVAL_FALLBACK       - Fallback evaluation model
    NEAR_CASCADE_EVAL_MAX_TOKENS     - Max tokens for evaluation (default 2000)

    NEAR_CONTRACT_ID                 - Assessment attestation contract address
    NEAR_NETWORK                     - Network to use (testnet/mainnet)
    NEAR_PREFER_TEE                  - Prefer TEE-protected models (true/false)
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CascadeLayerConfig:
    """Configuration for a single cascade layer."""
    primary: str
    fallback: str
    temperature: float = 0.7
    max_tokens: int = 500


@dataclass
class CascadeConfig:
    """Configuration for the three-layer model cascade."""
    chat: CascadeLayerConfig = field(default_factory=lambda: CascadeLayerConfig(
        primary="openai/gpt-oss-120b",
        fallback="deepseek-ai/DeepSeek-V3.1",
        temperature=0.7,
        max_tokens=500,
    ))
    middleware: CascadeLayerConfig = field(default_factory=lambda: CascadeLayerConfig(
        primary="Qwen/Qwen3-30B-A3B-Instruct-2507",
        fallback="deepseek-ai/DeepSeek-V3.1",
        temperature=0.2,
        max_tokens=200,
    ))
    eval: CascadeLayerConfig = field(default_factory=lambda: CascadeLayerConfig(
        primary="zai-org/GLM-4.7",
        fallback="openai/gpt-oss-120b",
        temperature=0.3,
        max_tokens=2000,
    ))
    middleware_enabled: bool = True


@dataclass
class NearConfig:
    """Configuration for NEAR Protocol integration."""

    # NEAR AI Cloud (Private Inference)
    ai_api_key: str = ""
    ai_enabled: bool = False
    ai_timeout: float = 30.0

    # Model Cascade
    cascade: CascadeConfig = field(default_factory=CascadeConfig)

    # Assessment Attestation (On-Chain)
    contract_id: str = ""
    network: str = "testnet"

    # TEE preference
    prefer_tee: bool = True

    @classmethod
    def from_env(cls) -> "NearConfig":
        """Load configuration from environment variables."""
        cascade = CascadeConfig(
            chat=CascadeLayerConfig(
                primary=os.getenv("NEAR_CASCADE_CHAT_MODEL", "openai/gpt-oss-120b"),
                fallback=os.getenv("NEAR_CASCADE_CHAT_FALLBACK", "deepseek-ai/DeepSeek-V3.1"),
                temperature=0.7,
                max_tokens=500,
            ),
            middleware=CascadeLayerConfig(
                primary=os.getenv("NEAR_CASCADE_MIDDLEWARE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"),
                fallback=os.getenv("NEAR_CASCADE_MIDDLEWARE_FALLBACK", "deepseek-ai/DeepSeek-V3.1"),
                temperature=0.2,
                max_tokens=200,
            ),
            eval=CascadeLayerConfig(
                primary=os.getenv("NEAR_CASCADE_EVAL_MODEL", "zai-org/GLM-4.7"),
                fallback=os.getenv("NEAR_CASCADE_EVAL_FALLBACK", "openai/gpt-oss-120b"),
                temperature=0.3,
                max_tokens=int(os.getenv("NEAR_CASCADE_EVAL_MAX_TOKENS", "2000")),
            ),
            middleware_enabled=os.getenv("NEAR_CASCADE_MIDDLEWARE_ENABLED", "true").lower() == "true",
        )

        return cls(
            ai_api_key=os.getenv("NEAR_AI_API_KEY", ""),
            ai_enabled=os.getenv("NEAR_AI_ENABLED", "false").lower() == "true",
            ai_timeout=float(os.getenv("NEAR_AI_TIMEOUT", "30.0")),
            cascade=cascade,
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
NEAR_AI_TIMEOUT=30.0

# Cascade
NEAR_CASCADE_CHAT_MODEL=openai/gpt-oss-120b
NEAR_CASCADE_CHAT_FALLBACK=deepseek-ai/DeepSeek-V3.1
NEAR_CASCADE_MIDDLEWARE_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
NEAR_CASCADE_MIDDLEWARE_FALLBACK=deepseek-ai/DeepSeek-V3.1
NEAR_CASCADE_MIDDLEWARE_ENABLED=true
NEAR_CASCADE_EVAL_MODEL=zai-org/GLM-4.7
NEAR_CASCADE_EVAL_FALLBACK=openai/gpt-oss-120b
NEAR_CASCADE_EVAL_MAX_TOKENS=2000

# Contract
NEAR_CONTRACT_ID=your-contract.nearplay.testnet
NEAR_NETWORK=testnet
NEAR_PREFER_TEE=true
"""
