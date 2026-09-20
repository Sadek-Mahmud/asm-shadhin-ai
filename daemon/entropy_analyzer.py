"""
entropy_analyzer.py - Encrypted Traffic & C2 Beacon Analyzer (Zero-Decryption)
Analyzes TLS 1.3 / QUIC flow telemetry using Shannon entropy and inter-arrival jitter
to spot Command-and-Control (C2) beaconing without breaking end-to-end encryption.
"""

import math
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

class EncryptedTrafficAnalyzer:
    """
    Evaluates packet payload entropy and inter-arrival timing to detect:
    - Encrypted C2 reverse shells (Cobalt Strike, Sliver, Metasploit)
    - Data exfiltration over encrypted tunnels
    - Ransomware key-exchange beaconing
    """

    def __init__(self, c2_jitter_threshold_pct: float = 0.15, min_entropy_threshold: float = 7.1):
        self.c2_jitter_threshold_pct = c2_jitter_threshold_pct
        self.min_entropy_threshold = min_entropy_threshold
        # Tracks flow history: flow_key -> list of arrival timestamps
        self.flow_history: Dict[str, List[float]] = {}

    @staticmethod
    def calculate_shannon_entropy(data: bytes) -> float:
        """
        Computes Shannon entropy in bits per byte:
        H(X) = - sum(P(x) * log2(P(x))) for all byte values 0..255
        Returns value in range [0.0, 8.0]
        """
        if not data:
            return 0.0

        length = len(data)
        frequencies = Counter(data)
        entropy = 0.0

        for count in frequencies.values():
            p_x = count / length
            entropy -= p_x * math.log2(p_x)

        return round(entropy, 4)

    def evaluate_c2_beaconing(self, flow_key: str, arrival_time: float) -> Tuple[bool, float, float]:
        """
        Evaluates inter-arrival timing jitter for a flow.
        Returns: (is_beacon, avg_interval_sec, jitter_pct)
        """
        # Bounded memory protection: prune inactive flows when capacity exceeds 5,000
        if len(self.flow_history) >= 5000:
            prune_time = arrival_time - 300.0  # 5 minutes idle
            stale_keys = [k for k, v in self.flow_history.items() if v and v[-1] < prune_time]
            for k in stale_keys[:1000]:
                del self.flow_history[k]

        if flow_key not in self.flow_history:
            self.flow_history[flow_key] = [arrival_time]
            return (False, 0.0, 1.0)

        history = self.flow_history[flow_key]
        history.append(arrival_time)

        # Retain last 20 arrivals
        if len(history) > 20:
            history.pop(0)

        if len(history) < 5:
            return (False, 0.0, 1.0)

        # Compute intervals
        intervals = [history[i] - history[i - 1] for i in range(1, len(history))]
        avg_interval = sum(intervals) / len(intervals)

        if avg_interval < 0.05:  # Ignore bursty bulk data transfer
            return (False, avg_interval, 1.0)

        # Compute variance and jitter
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = math.sqrt(variance)
        jitter_pct = std_dev / avg_interval if avg_interval > 0 else 1.0

        # Periodic beacon signature: low jitter (<= threshold) with consistent interval
        is_beacon = jitter_pct <= self.c2_jitter_threshold_pct
        return (is_beacon, round(avg_interval, 3), round(jitter_pct, 4))

    def analyze_packet_sample(self, src_ip: str, dst_ip: str, dst_port: int,
                              payload_bytes: bytes, arrival_time: Optional[float] = None) -> Dict[str, any]:
        """
        Comprehensive evaluation of an encrypted packet sample.
        """
        if arrival_time is None:
            arrival_time = time.time()

        entropy = self.calculate_shannon_entropy(payload_bytes)
        flow_key = f"{src_ip}->{dst_ip}:{dst_port}"
        is_beacon, avg_interval, jitter_pct = self.evaluate_c2_beaconing(flow_key, arrival_time)

        verdict = "BENIGN"
        threat_score = 0.0
        details = []

        # High entropy indicates strong encryption or packing
        if entropy >= self.min_entropy_threshold:
            details.append(f"High Shannon entropy: {entropy:.2f}/8.0 (Fully encrypted payload)")

        if is_beacon and entropy >= self.min_entropy_threshold:
            verdict = "MALICIOUS_C2_BEACON"
            threat_score = 0.95
            details.append(f"Periodic C2 beaconing detected (Interval: {avg_interval}s, Jitter: {jitter_pct*100:.1f}%)")
        elif entropy >= 7.8:
            verdict = "SUSPICIOUS_ENCRYPTED_TUNNEL"
            threat_score = 0.65
            details.append("Very high entropy tunnel stream")

        return {
            "flow_key": flow_key,
            "entropy": entropy,
            "is_beacon": is_beacon,
            "avg_interval_sec": avg_interval,
            "jitter_pct": jitter_pct,
            "verdict": verdict,
            "threat_score": threat_score,
            "details": details
        }
