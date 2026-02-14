#!/usr/bin/env python3
"""
Test assessment attestation verification on NEAR testnet.

Verifies that the attestation contract is deployed and responsive.

Usage:
    export NEAR_CONTRACT_ID=your-contract.nearplay.testnet
    python test_attestation.py
"""

import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from near_service import AttestationService


def main():
    contract_id = os.getenv(
        "NEAR_CONTRACT_ID",
        "e756da-291226-1771097746.nearplay.testnet"  # Demo contract
    )
    network = os.getenv("NEAR_NETWORK", "testnet")

    print("=" * 60)
    print("NEAR Assessment Attestation - Verification Test")
    print("=" * 60)

    service = AttestationService(contract_id=contract_id, network=network)

    # 1. Check attestation count
    print(f"\n1. Contract: {contract_id}")
    print(f"   Network: {network}")
    count = service.get_attestation_count()
    print(f"   Attestation count: {count}")

    # 2. Test hash computation
    print("\n2. Testing hash computation...")
    test_payload = {
        "session_id": "test-session-001",
        "overall_score": 0.86,
        "tier": "Expert",
        "dimensions": {
            "Performance": 0.90,
            "Accountability": 0.85,
            "Integrity": 0.95,
            "Collaboration": 0.90,
            "Evolution": 0.70,
        },
        "timestamp": 1771097909397,
    }
    hash_val = service.compute_hash(test_payload)
    print(f"   Payload: {test_payload['session_id']} / {test_payload['tier']}")
    print(f"   Hash: {hash_val}")

    # 3. Verify existing attestation
    print("\n3. Verifying on-chain attestation for 'test-session-001'...")
    result = service.verify("test-session-001")
    if result.found:
        print(f"   Found: YES")
        print(f"   Attester: {result.attester}")
        print(f"   Score hash: {result.score_hash}")
        print(f"   Timestamp: {result.timestamp}")
    else:
        print(f"   Found: NO (session may not have been attested yet)")

    # 4. Explorer link
    print(f"\n4. Explorer URL: {service.get_explorer_url()}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
