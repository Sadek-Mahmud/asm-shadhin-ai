"""
auth_guard.py - Enterprise-Grade SOC Authentication Guard Module
Implements RFC 9106 Argon2id Memory-Hard Password Hashing & HMAC-SHA512 Session Management.
OWASP-Compliant Defense against GPU/ASIC Distributed Dictionary & Brute-Force Attacks.
"""

import os
import time
import hmac
import hashlib
import base64
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("auth_guard")

ARGON2_AVAILABLE = False
try:
    import argon2
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
    logger.info("[AUTH] Native Argon2id (RFC 9106) engine active.")
except ImportError:
    logger.warning("[AUTH] argon2-cffi not installed. Using High-Security SHA-512 PBKDF2 fallback.")


class Argon2idAuthGuard:
    """
    Argon2id authentication guard complying with RFC 9106 and OWASP recommendations:
    - Type: Argon2id (hybrid resistant against side-channel and GPU-memory cracking)
    - Memory cost: 65,536 KiB (64 MiB)
    - Time cost (iterations): 3
    - Parallelism: 4 threads
    - Hash length: 32 bytes (256 bits)
    """

    def __init__(self, memory_cost: int = 65536, time_cost: int = 3, parallelism: int = 4):
        self.memory_cost = memory_cost
        self.time_cost = time_cost
        self.parallelism = parallelism

        if ARGON2_AVAILABLE:
            self._hasher = PasswordHasher(
                time_cost=self.time_cost,
                memory_cost=self.memory_cost,
                parallelism=self.parallelism,
                hash_len=32,
                type=argon2.Type.ID
            )
        else:
            self._hasher = None

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using Argon2id (or secure SHA-512 PBKDF2 fallback)."""
        if not password:
            raise ValueError("Password cannot be empty")

        if ARGON2_AVAILABLE and self._hasher:
            return self._hasher.hash(password)
        else:
            # Fallback: PBKDF2-HMAC-SHA512 with 600,000 rounds (OWASP 2024 spec)
            salt = os.urandom(16)
            kdf = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, iterations=600000)
            salt_b64 = base64.b64encode(salt).decode("ascii")
            hash_b64 = base64.b64encode(kdf).decode("ascii")
            return f"$pbkdf2-sha512$i=600000${salt_b64}${hash_b64}"

    def verify_password(self, stored_hash: str, password: str) -> bool:
        """Cryptographically verify plaintext password against stored hash."""
        if not stored_hash or not password:
            return False

        if stored_hash.startswith("$argon2id$") and ARGON2_AVAILABLE and self._hasher:
            try:
                return self._hasher.verify(stored_hash, password)
            except VerifyMismatchError:
                return False
            except Exception as e:
                logger.error(f"[AUTH] Argon2 verification exception: {e}")
                return False

        elif stored_hash.startswith("$pbkdf2-sha512$"):
            try:
                parts = stored_hash.split("$")
                # format: ['', 'pbkdf2-sha512', 'i=600000', salt_b64, hash_b64]
                iterations = int(parts[2].replace("i=", ""))
                salt = base64.b64decode(parts[3])
                expected_hash = base64.b64decode(parts[4])
                computed_hash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, iterations=iterations)
                return hmac.compare_digest(computed_hash, expected_hash)
            except Exception as e:
                logger.error(f"[AUTH] PBKDF2-SHA512 verification exception: {e}")
                return False

        return False

    @staticmethod
    def create_session_token(username: str, secret_key: bytes, ttl_seconds: int = 3600) -> str:
        """
        Generate a cryptographically tamper-proof session token using HMAC-SHA512.
        Token format: <base64_payload>.<base64_sha512_signature>
        """
        expires_at = int(time.time()) + ttl_seconds
        payload = {
            "sub": username,
            "exp": expires_at,
            "nonce": os.urandom(16).hex(),
            "alg": "HMAC-SHA512"
        }
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")

        sig = hmac.new(secret_key, payload_b64.encode("ascii"), hashlib.sha512).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")

        return f"{payload_b64}.{sig_b64}"

    @staticmethod
    def verify_session_token(token: str, secret_key: bytes) -> Optional[Dict[str, Any]]:
        """
        Verify HMAC-SHA512 session token integrity and expiration.
        Returns decoded payload dict if valid; None otherwise.
        """
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None

            payload_b64, sig_b64 = parts

            # Recompute HMAC-SHA512
            expected_sig = hmac.new(secret_key, payload_b64.encode("ascii"), hashlib.sha512).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")

            if not hmac.compare_digest(sig_b64, expected_sig_b64):
                return None

            # Decode payload
            padding = "=" * ((4 - len(payload_b64) % 4) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
            payload = json.loads(payload_json)

            if time.time() > payload.get("exp", 0):
                return None  # Expired

            return payload
        except Exception:
            return None
