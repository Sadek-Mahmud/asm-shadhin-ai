"""
bpf_controller.py - Kernel eBPF Map Management & Fast-Path Controller
Manages pinned BPF maps via bpftool CLI and atomic system operations.
Zero-downtime, line-rate updates without resetting the XDP hook.
"""

import subprocess
import socket
import struct
import time
import logging
import json
from typing import Dict, List, Optional
import sys
from pathlib import Path

_daemon_dir = str(Path(__file__).resolve().parent)
if _daemon_dir not in sys.path:
    sys.path.insert(0, _daemon_dir)

from config import (
    BPF_BLOCKED_MAP,
    BPF_TARPIT_MAP,
    DEFAULT_BLOCK_TTL_SECONDS,
)

logger = logging.getLogger("bpf_controller")


class BPFController:
    """Interface to Linux Kernel eBPF Maps using bpftool."""

    def __init__(self, blocked_map_path: Path = BPF_BLOCKED_MAP, tarpit_map_path: Path = BPF_TARPIT_MAP):
        self.blocked_map_path = blocked_map_path
        self.tarpit_map_path = tarpit_map_path
        # In-memory tracking for TTL expiry management: {ip_str: (expiry_timestamp, reason_code)}
        self._active_blocks: Dict[str, tuple] = {}
        self._active_tarpits: Dict[str, int] = {}

    @staticmethod
    def _ip_to_bytes(ip_str: str) -> List[str]:
        """Convert IPv4 string to space-separated hex bytes in network order for bpftool."""
        packed = socket.inet_aton(ip_str)
        return [f"0x{b:02x}" for b in packed]

    @staticmethod
    def _pack_block_entry(timestamp_ns: int, drop_count: int, ttl_seconds: int, reason_code: int) -> List[str]:
        """
        Pack struct block_entry:
            __u64 timestamp_ns (8 bytes)
            __u64 drop_count    (8 bytes)
            __u32 ttl_seconds   (4 bytes)
            __u8  reason_code   (1 byte)
            __u8  reserved[3]   (3 bytes)
        Total = 24 bytes
        """
        fmt = "<QQIB3x"  # little-endian x86_64 kernel representation
        packed = struct.pack(fmt, timestamp_ns, drop_count, ttl_seconds, reason_code)
        return [f"0x{b:02x}" for b in packed]

    @staticmethod
    def _pack_tarpit_entry(timestamp_ns: int, packet_count: int, redirect_port: int, active: int = 1) -> List[str]:
        """
        Pack struct tarpit_entry:
            __u64 timestamp_ns   (8 bytes)
            __u64 packet_count   (8 bytes)
            __u16 redirect_port  (2 bytes)
            __u8  active         (1 byte)
            __u8  reserved[5]    (5 bytes)
        Total = 24 bytes
        """
        fmt = "<QQHB5x"
        packed = struct.pack(fmt, timestamp_ns, packet_count, redirect_port, active)
        return [f"0x{b:02x}" for b in packed]

    def is_map_available(self, map_path: Path) -> bool:
        """Check if pinned BPF map exists in /sys/fs/bpf."""
        return map_path.exists()

    def block_ip(self, ip_str: str, ttl_seconds: int = DEFAULT_BLOCK_TTL_SECONDS, reason_code: int = 3) -> bool:
        """
        Insert or update an IP in the eBPF blocked_ips_map.
        Zero overhead: packets will be immediately dropped by XDP_DROP at NIC/driver level.
        """
        try:
            # Validate IP format
            socket.inet_aton(ip_str)
        except socket.error:
            logger.error("Invalid IPv4 address format: %s", ip_str)
            return False

        if not self.is_map_available(self.blocked_map_path):
            logger.warning("BPF Map not pinned at %s. Simulating in-memory block for %s", self.blocked_map_path, ip_str)
            self._active_blocks[ip_str] = (time.time() + ttl_seconds, reason_code)
            return True

        now_ns = int(time.time() * 1e9)
        key_bytes = self._ip_to_bytes(ip_str)
        val_bytes = self._pack_block_entry(now_ns, 0, ttl_seconds, reason_code)

        cmd = [
            "bpftool", "map", "update",
            "pinned", str(self.blocked_map_path),
            "key", *key_bytes,
            "value", *val_bytes
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                self._active_blocks[ip_str] = (time.time() + ttl_seconds, reason_code)
                logger.info("[+] Fast-Path eBPF Block ACTIVATED for IP: %s (TTL: %ds, Reason: %d)", ip_str, ttl_seconds, reason_code)
                return True
            else:
                logger.error("Failed to update BPF map for %s: %s", ip_str, res.stderr.strip())
                return False
        except Exception as e:
            logger.exception("Subprocess error executing bpftool: %s", e)
            return False

    def unblock_ip(self, ip_str: str) -> bool:
        """Remove an IP from the eBPF blocked_ips_map."""
        try:
            socket.inet_aton(ip_str)
        except socket.error:
            return False

        if self.is_map_available(self.blocked_map_path):
            key_bytes = self._ip_to_bytes(ip_str)
            cmd = ["bpftool", "map", "delete", "pinned", str(self.blocked_map_path), "key", *key_bytes]
            subprocess.run(cmd, capture_output=True, text=True, check=False)

        self._active_blocks.pop(ip_str, None)
        logger.info("[-] IP Unblocked from eBPF fast-path: %s", ip_str)
        return True

    def divert_to_tarpit(self, ip_str: str, redirect_port: int = 8088) -> bool:
        """Route offending scanner IP to the local AI-Tarpit Deception service."""
        try:
            socket.inet_aton(ip_str)
        except socket.error:
            return False

        if not self.is_map_available(self.tarpit_map_path):
            self._active_tarpits[ip_str] = redirect_port
            logger.warning("Tarpit BPF map unavailable. Tracking %s in-memory.", ip_str)
            return True

        now_ns = int(time.time() * 1e9)
        key_bytes = self._ip_to_bytes(ip_str)
        val_bytes = self._pack_tarpit_entry(now_ns, 0, redirect_port, 1)

        cmd = [
            "bpftool", "map", "update",
            "pinned", str(self.tarpit_map_path),
            "key", *key_bytes,
            "value", *val_bytes
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            self._active_tarpits[ip_str] = redirect_port
            logger.info("[★] IP Diverted to AI-Tarpit honeypot: %s -> port %d", ip_str, redirect_port)
            return True
        return False

    def sweep_expired_ttls(self) -> int:
        """Iterate over active blocks and remove those past their TTL."""
        now = time.time()
        expired = [ip for ip, (expiry, _) in self._active_blocks.items() if expiry > 0 and now >= expiry]
        for ip in expired:
            self.unblock_ip(ip)
        return len(expired)

    def get_stats(self) -> Dict:
        """Retrieve count of actively blocked IPs and memory state."""
        return {
            "active_blocked_count": len(self._active_blocks),
            "active_tarpit_count": len(self._active_tarpits),
            "bpf_blocked_map_available": self.is_map_available(self.blocked_map_path),
            "bpf_tarpit_map_available": self.is_map_available(self.tarpit_map_path),
        }
