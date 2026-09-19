"""
mtd_service.py - Moving Target Defense (MTD) Polymorphic Port Hopping Engine
Dynamically mutates external service exposure ports periodically based on a
cryptographic pseudo-random seed, rendering attacker port scans instantly obsolete.
"""

import time
import hmac
import hashlib
import struct
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("mtd_service")

class MovingTargetDefense:
    """
    Moving Target Defense engine that implements dynamic port & decoy mutation.
    Ensures that an attacker scanning the network sees a non-deterministic,
    ever-changing target space.
    """

    def __init__(self, secret_seed: bytes = b"ASM_SHADHIN_AI_QUANTUM_MTD_SEED_2026",
                 hop_interval_seconds: int = 60,
                 port_range_start: int = 10000,
                 port_range_end: int = 60000):
        self.secret_seed = secret_seed
        self.hop_interval = hop_interval_seconds
        self.port_min = port_range_start
        self.port_max = port_range_end
        self.port_range_span = self.port_max - self.port_min
        # Map: service_name -> real_port
        self.registered_services: Dict[str, int] = {
            "SSH": 22,
            "HTTPS": 443,
            "DATABASE": 5432
        }

    def _get_time_epoch_step(self, timestamp: Optional[float] = None) -> int:
        """Computes current discrete time window step."""
        t = timestamp if timestamp is not None else time.time()
        return int(t // self.hop_interval)

    def calculate_polymorphic_port(self, service_name: str, epoch_step: Optional[int] = None) -> int:
        """
        Derives the active polymorphic port for a given service and epoch step
        using HMAC-SHA256 for cryptographic non-determinism.
        """
        if epoch_step is None:
            epoch_step = self._get_time_epoch_step()

        # Input data: service name + epoch step
        data = f"{service_name}:{epoch_step}".encode()
        digest = hmac.new(self.secret_seed, data, hashlib.sha256).digest()
        
        # Take 4 bytes and project onto port range
        val = struct.unpack(">I", digest[:4])[0]
        active_port = self.port_min + (val % self.port_range_span)
        return active_port

    def get_active_defense_state(self) -> Dict[str, any]:
        """
        Returns the current MTD hopping state for all registered services.
        """
        current_step = self._get_time_epoch_step()
        seconds_remaining = self.hop_interval - int(time.time() % self.hop_interval)
        
        mappings = {}
        for srv, real_port in self.registered_services.items():
            current_port = self.calculate_polymorphic_port(srv, current_step)
            next_port = self.calculate_polymorphic_port(srv, current_step + 1)
            mappings[srv] = {
                "real_internal_port": real_port,
                "current_polymorphic_port": current_port,
                "next_polymorphic_port": next_port
            }

        return {
            "epoch_step": current_step,
            "seconds_until_next_hop": seconds_remaining,
            "services": mappings
        }

    def validate_incoming_packet(self, service_name: str, target_port: int) -> bool:
        """
        Validates if an incoming packet arrives on either the current or previous
        epoch's polymorphic port (allowing a 1-interval grace window for inflight connections).
        """
        current_step = self._get_time_epoch_step()
        cur_port = self.calculate_polymorphic_port(service_name, current_step)
        prev_port = self.calculate_polymorphic_port(service_name, current_step - 1)

        return target_port == cur_port or target_port == prev_port
