use near_sdk::borsh::{self, BorshDeserialize, BorshSerialize};
use near_sdk::serde::{Serialize, Deserialize};
use near_sdk::{log, near, env, NearSchema};
use near_sdk::store::LookupMap;

/// Represents a single assessment attestation stored on-chain.
/// Contains the hash of the score payload, the block timestamp,
/// and the account that submitted the attestation.
#[derive(BorshDeserialize, BorshSerialize, Serialize, Deserialize, NearSchema, Clone)]
#[borsh(crate = "near_sdk::borsh")]
#[serde(crate = "near_sdk::serde")]
pub struct Attestation {
    pub score_hash: String,
    pub timestamp: u64,
    pub attester: String,
}

/// PAICE Assessment Attestation Contract
///
/// Stores SHA-256 hashes of assessment score payloads on NEAR testnet
/// as tamper-proof attestations. Each attestation links a session ID
/// to its score hash, enabling anyone to verify that assessment results
/// have not been modified after the fact.
#[near(contract_state)]
pub struct Contract {
    attestations: LookupMap<String, Attestation>,
    attestation_count: u64,
}

impl Default for Contract {
    fn default() -> Self {
        Self {
            attestations: LookupMap::new(b"a"),
            attestation_count: 0,
        }
    }
}

#[near]
impl Contract {
    /// Store an assessment attestation on-chain.
    ///
    /// # Arguments
    /// * `session_id` - Unique identifier for the assessment session
    /// * `score_hash` - SHA-256 hash of the canonical score payload
    ///
    /// The attestation records the hash, the block timestamp, and the
    /// calling account as the attester.
    pub fn attest(&mut self, session_id: String, score_hash: String) {
        assert!(!session_id.is_empty(), "session_id cannot be empty");
        assert!(!score_hash.is_empty(), "score_hash cannot be empty");

        let attestation = Attestation {
            score_hash: score_hash.clone(),
            timestamp: env::block_timestamp(),
            attester: env::predecessor_account_id().to_string(),
        };

        self.attestations.insert(session_id.clone(), attestation);
        self.attestation_count += 1;

        log!(
            "Attestation stored for session: {}, hash: {}",
            session_id,
            score_hash
        );
    }

    /// Verify an attestation by session ID.
    ///
    /// Returns the attestation data if found, or None if no attestation
    /// exists for the given session ID. Callers can compare the returned
    /// score_hash against a locally-computed hash to verify integrity.
    pub fn verify(&self, session_id: String) -> Option<Attestation> {
        self.attestations.get(&session_id).cloned()
    }

    /// Get the total number of attestations stored in this contract.
    pub fn get_attestation_count(&self) -> u64 {
        self.attestation_count
    }
}
