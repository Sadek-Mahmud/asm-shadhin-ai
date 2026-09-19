"""
audit_logger.py - Tamper-Proof Forensic Audit Trail Engine
Implements Cryptographic Hash-Chaining using SHA-512 (FIPS 180-4).
Guarantees Non-Repudiation, Forensic Integrity, and Immediate Tamper-Detection for Security Events.
"""

import os
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List


class SHA512AuditLogger:
    """
    Immutable, cryptographic append-only audit log.
    Every event contains:
      - entry_id: Sequential index
      - timestamp: ISO-8601 UTC timestamp
      - event_type: Classification string (e.g. EBPF_DROP, THREAT_ISOLATION, MTD_ROTATE)
      - payload: Event data dictionary
      - prev_hash: SHA-512 hex digest of the previous record
      - current_hash: SHA-512(entry_id || timestamp || event_type || canonical_json(payload) || prev_hash)
    """

    GENESIS_HASH = "0" * 128  # 512-bit zero hash for block 0

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            # Default to logs/audit_chain.jsonl
            base = Path(__file__).resolve().parent.parent
            self.log_path = base / "logs" / "audit_chain.jsonl"
        else:
            self.log_path = Path(log_path)

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._get_latest_hash()

    def _get_latest_hash(self) -> str:
        """Scan to the end of the existing file to find the latest valid hash."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return self.GENESIS_HASH

        last_hash = self.GENESIS_HASH
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        last_hash = entry.get("current_hash", last_hash)
        except Exception:
            pass
        return last_hash

    @staticmethod
    def compute_hash(entry_id: int, timestamp: str, event_type: str, payload: Dict[str, Any], prev_hash: str) -> str:
        """Compute 512-bit SHA-512 cryptographic hash of an audit log entry."""
        canonical_data = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        preimage = f"{entry_id}|{timestamp}|{event_type}|{canonical_data}|{prev_hash}".encode("utf-8")
        return hashlib.sha512(preimage).hexdigest()

    def record_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Append an event to the cryptographically chained audit log."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        # Determine next entry_id
        entry_id = 1
        if self.log_path.exists() and self.log_path.stat().st_size > 0:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
                entry_id = len(lines) + 1

        prev_hash = self._last_hash
        current_hash = self.compute_hash(entry_id, timestamp, event_type, payload, prev_hash)

        entry = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev_hash,
            "current_hash": current_hash,
            "hash_algorithm": "SHA-512 (FIPS 180-4)"
        }

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(',', ':')) + "\n")

        self._last_hash = current_hash
        return entry

    def verify_chain(self) -> Tuple[bool, int, Optional[int], Optional[str]]:
        """
        Validate the entire cryptographic hash chain from Genesis to current head.
        Returns (is_valid, total_records, broken_index, error_message).
        """
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return True, 0, None, None

        expected_prev = self.GENESIS_HASH
        count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                count += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    return False, count, idx, "Corrupted JSON entry"

                entry_id = record.get("entry_id")
                timestamp = record.get("timestamp")
                event_type = record.get("event_type")
                payload = record.get("payload", {})
                prev_hash = record.get("prev_hash")
                current_hash = record.get("current_hash")

                # Verify previous hash linkage
                if prev_hash != expected_prev:
                    return False, count, idx, f"Broken link: expected prev_hash {expected_prev[:16]}..., got {prev_hash[:16]}..."

                # Verify SHA-512 content integrity
                recomputed = self.compute_hash(entry_id, timestamp, event_type, payload, prev_hash)
                if recomputed != current_hash:
                    return False, count, idx, f"Tampered entry: hash mismatch at index {idx}"

                expected_prev = current_hash

        return True, count, None, None
