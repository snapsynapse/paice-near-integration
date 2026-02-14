#!/usr/bin/env python3
"""
Test NEAR AI Cloud inference.

Verifies that the API key is valid and TEE-protected models respond correctly.

Usage:
    export NEAR_AI_API_KEY=sk-your-key
    python test_near_ai.py
"""

import os
import sys
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from near_service import NearAIClient


def main():
    api_key = os.getenv("NEAR_AI_API_KEY")
    if not api_key:
        print("Error: NEAR_AI_API_KEY not set")
        sys.exit(1)

    client = NearAIClient(api_key=api_key)

    print("=" * 60)
    print("NEAR AI Cloud - Inference Test")
    print("=" * 60)

    # List models
    print("\n1. Listing available models...")
    models = client.list_models()
    for m in models:
        tee = " [TEE]" if m["id"] in client.TEE_MODELS else ""
        pricing = m.get("pricing", {})
        print(f"   {m['id']:50s} ${pricing.get('input', '?')}/M in{tee}")

    # Test with DeepSeek V3.1 (TEE-protected)
    test_model = "deepseek-ai/DeepSeek-V3.1"
    print(f"\n2. Testing {test_model} (TEE: {client.is_tee_protected(test_model)})...")

    start = time.time()
    response = client.chat(
        model=test_model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Respond in one sentence."},
            {"role": "user", "content": "What is NEAR Protocol?"},
        ],
        temperature=0.7,
        max_tokens=100,
    )
    elapsed = time.time() - start

    print(f"   Response: {response.content}")
    print(f"   Model: {response.model}")
    print(f"   Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"   Latency: {elapsed:.2f}s")
    print(f"   Finish: {response.finish_reason}")

    # Test with budget model
    budget_model = "Qwen/Qwen3-30B-A3B-Instruct-2507"
    print(f"\n3. Testing {budget_model} (TEE: {client.is_tee_protected(budget_model)})...")

    start = time.time()
    response = client.chat(
        model=budget_model,
        messages=[
            {"role": "user", "content": "In one sentence, what is a TEE in computing?"},
        ],
        temperature=0.5,
        max_tokens=100,
    )
    elapsed = time.time() - start

    print(f"   Response: {response.content}")
    print(f"   Tokens: {response.input_tokens} in / {response.output_tokens} out")
    print(f"   Latency: {elapsed:.2f}s")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    main()
