"""
Configuration module for AI-Driven Security Monitoring & Defense System.
Optimized for headless Ubuntu Server on Intel Core i5 4th Gen (Haswell, 16GB RAM).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Network & eBPF Configuration ---
INTERFACE_NAME = os.getenv("SEC_INTERFACE", "eth0")
WAN_INTERFACE = os.getenv("WAN_INTERFACE", INTERFACE_NAME)
LAN_INTERFACE = os.getenv("LAN_INTERFACE", "eth1")
BRIDGE_INTERFACE = os.getenv("BRIDGE_INTERFACE", "br0")
INLINE_MODE = os.getenv("INLINE_MODE", "bridge")  # 'bridge', 'gateway', or 'single'
BPF_FS_PATH = Path("/sys/fs/bpf")
BPF_BLOCKED_MAP = BPF_FS_PATH / "blocked_ips_map"
BPF_TARPIT_MAP = BPF_FS_PATH / "tarpit_ips_map"
BPF_RINGBUF_MAP = BPF_FS_PATH / "packet_metrics_rb"
BPF_OBJECT_PATH = BASE_DIR / "ebpf" / "ebpf_filter.o"

# Default TTL for automatically blocked IPs (seconds)
DEFAULT_BLOCK_TTL_SECONDS = int(os.getenv("SEC_BLOCK_TTL", "3600"))  # 1 hour
MAX_BLOCK_ENTRIES = 65536

# --- Suricata IDS Configuration ---
SURICATA_EVE_PATH = Path(os.getenv("SURICATA_EVE_PATH", "/var/log/suricata/eve.json"))
SURICATA_MIN_SEVERITY = int(os.getenv("SURICATA_MIN_SEVERITY", "2"))  # 1=High, 2=Medium, 3=Low

# --- Ollama & Local LLM Configuration ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "asm-shadhin-ai")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT", "15.0"))
OLLAMA_MAX_RETRIES = 2

# CPU inference throttling (prevent starving eBPF / Suricata)
LLM_QUEUE_MAX_SIZE = 100
LLM_CONCURRENT_REQUESTS = 1

# --- AI-Tarpit & Deception Configuration ---
TARPIT_HOST = os.getenv("TARPIT_HOST", "0.0.0.0")
TARPIT_HTTP_PORT = int(os.getenv("TARPIT_HTTP_PORT", "8088"))
TARPIT_SSH_PORT = int(os.getenv("TARPIT_SSH_PORT", "2222"))
TARPIT_CHUNK_DELAY_MS = int(os.getenv("TARPIT_CHUNK_DELAY_MS", "35"))  # Throttle throughput
TARPIT_MAX_DRAIN_TOKENS = int(os.getenv("TARPIT_MAX_DRAIN_TOKENS", "4096"))

# --- Post-Quantum Cryptography (PQC) Configuration ---
PQC_KEM_ALGORITHM = os.getenv("PQC_KEM_ALG", "ML-KEM-1024")    # NIST FIPS 203 Category 5 (Kyber-1024)
PQC_SIG_ALGORITHM = os.getenv("PQC_SIG_ALG", "ML-DSA-65")      # NIST FIPS 204 (Dilithium3)
PQC_TUNNEL_PORT = int(os.getenv("PQC_TUNNEL_PORT", "8443"))
PQC_CERT_DIR = BASE_DIR / "certs" / "pqc"

# --- Authentication & Immutable Audit Trail (RFC 9106 & FIPS 180-4) ---
AUTH_ARGON2_MEMORY_KIB = int(os.getenv("AUTH_ARGON2_MEMORY_KIB", "65536"))  # 64 MiB
AUTH_ARGON2_TIME_COST = int(os.getenv("AUTH_ARGON2_TIME_COST", "3"))        # 3 iterations
AUTH_ARGON2_PARALLELISM = int(os.getenv("AUTH_ARGON2_PARALLELISM", "4"))    # 4 threads
AUDIT_LOG_CHAIN_PATH = BASE_DIR / "logs" / "audit_chain.jsonl"

# --- Logging & Telemetry ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = Path("/var/log/sec_monitor.log")
