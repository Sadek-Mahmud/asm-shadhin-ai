#!/usr/bin/env python3
"""
run_live_llm_inference_benchmark.py
Runs a live end-to-end evaluation of the asm-shadhin-ai model (via Ollama)
under 5 diverse cybersecurity threat vectors:
1. Volumetric TCP SYN Flood (DDoS)
2. Stealthy Port Scan / OS Fingerprinting (Reconnaissance)
3. High-Entropy Encrypted Payload (Exfiltration / Ransomware C2)
4. Post-Quantum Cryptography Handshake Anomaly (Downgrade Attack)
5. Benign HTTP/HTTPS E-Commerce Traffic (False Positive Validation)
"""

import json
import time
import urllib.request
import urllib.error
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "asm-shadhin-ai:latest"

test_scenarios = [
    {
        "id": "SCN-01",
        "name": "Volumetric TCP SYN Flood (DDoS)",
        "event": {
            "src_ip": "198.51.100.44",
            "dest_port": 443,
            "proto": "TCP",
            "signature": "ET DOS Possible SYN Flood Inbound to Web Server",
            "severity": 1,
            "category": "Denial of Service",
            "packet_rate_pps": 842000,
            "entropy": 3.12
        },
        "expected_verdict": "MALICIOUS",
        "expected_action": "XDP_DROP"
    },
    {
        "id": "SCN-02",
        "name": "Stealthy SYN/FIN Port Scan",
        "event": {
            "src_ip": "203.0.113.89",
            "dest_port": 22,
            "proto": "TCP",
            "signature": "ET SCAN Suspicious Rapid Port Sweep Across High Ports",
            "severity": 2,
            "category": "Attempted Information Leak",
            "packet_rate_pps": 4500,
            "entropy": 4.05
        },
        "expected_verdict": "MALICIOUS",
        "expected_action": "XDP_DROP"
    },
    {
        "id": "SCN-03",
        "name": "High-Entropy Exfiltration Payload",
        "event": {
            "src_ip": "192.0.2.145",
            "dest_port": 8080,
            "proto": "TCP",
            "signature": "ET TROJAN High-Entropy Outbound Stream Anomaly (Possible C2)",
            "severity": 1,
            "category": "Command and Control",
            "packet_rate_pps": 12000,
            "entropy": 7.94
        },
        "expected_verdict": "MALICIOUS",
        "expected_action": "XDP_DROP"
    },
    {
        "id": "SCN-04",
        "name": "PQC Handshake Downgrade Attack",
        "event": {
            "src_ip": "198.51.100.210",
            "dest_port": 50051,
            "proto": "TCP",
            "signature": "ASM-PQC Invalid ML-KEM-1024 Encapsulation / Ciphertext Forgery",
            "severity": 1,
            "category": "Cryptographic Integrity Anomaly",
            "packet_rate_pps": 180,
            "entropy": 7.82
        },
        "expected_verdict": "MALICIOUS",
        "expected_action": "XDP_DROP"
    },
    {
        "id": "SCN-05",
        "name": "Benign HTTP REST API Traffic",
        "event": {
            "src_ip": "10.0.4.55",
            "dest_port": 443,
            "proto": "TCP",
            "signature": "SURICATA HTTP Normal GET Request /api/v1/checkout",
            "severity": 3,
            "category": "Normal Web Transaction",
            "packet_rate_pps": 650,
            "entropy": 4.88
        },
        "expected_verdict": "BENIGN",
        "expected_action": "XDP_PASS"
    }
]

def query_llm(scenario):
    ev = scenario["event"]
    prompt = (
        f"INPUT_SECURITY_EVENT:\n"
        f"Source IP: {ev['src_ip']}\n"
        f"Target Port: {ev['dest_port']}\n"
        f"Protocol: {ev['proto']}\n"
        f"Signature: {ev['signature']}\n"
        f"Severity: {ev['severity']}\n"
        f"Category: {ev['category']}\n"
        f"Packet Rate: {ev['packet_rate_pps']} pps\n"
        f"Payload Shannon Entropy: {ev['entropy']}\n\n"
        f"Analyze the threat event. If legitimate benign traffic, verdict must be BENIGN and action XDP_PASS. "
        f"If malicious, classify threat, assign confidence (0.00-1.00), specify action (XDP_DROP, RATE_LIMIT, TARPIT) "
        f"and return JSON matching the schema:\n"
        f'{{"verdict": "MALICIOUS|BENIGN", "threat_type": "string", "confidence": 0.95, "action": "XDP_DROP|XDP_PASS|TARPIT", '
        f'"source_ip": "{ev["src_ip"]}", "target_port": {ev["dest_port"]}, "reason": "string", "ttl_seconds": 300}}'
    )
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.05,
            "top_p": 0.9,
            "num_predict": 256
        }
    }
    
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        lat_ms = (time.perf_counter() - t0) * 1000.0
        resp_text = data.get("response", "").strip()
        parsed = json.loads(resp_text)
        return True, lat_ms, parsed
    except Exception as e:
        lat_ms = (time.perf_counter() - t0) * 1000.0
        return False, lat_ms, {"error": str(e)}

def main():
    print("=" * 80)
    print("🚀 LIVE EVALUATION OF ASM-SHADHIN-AI AUTONOMOUS THREAT INFERENCE ENGINE")
    print(f"Target Model: {MODEL_NAME} | Host: {OLLAMA_URL}")
    print("=" * 80)
    
    results = []
    for scn in test_scenarios:
        print(f"\nEvaluating {scn['id']}: {scn['name']}...")
        ok, lat, parsed = query_llm(scn)
        if not ok:
            print(f"  ❌ FAILED: {parsed.get('error')}")
            continue
        
        verdict = parsed.get("verdict", "UNKNOWN")
        action = parsed.get("action", parsed.get("ebpf_rule", {}).get("action", "UNKNOWN"))
        confidence = parsed.get("confidence", 0.0)
        threat_type = parsed.get("threat_type", "N/A")
        reason = parsed.get("reason", "N/A")
        
        # Verify alignment
        match = (verdict.upper() == scn["expected_verdict"])
        status = "✅ PASS" if match else "⚠️ MISMATCH"
        
        print(f"  Result: {status} | Verdict: {verdict} | Action: {action} | Conf: {confidence*100:.1f}% | Latency: {lat:.1f} ms")
        print(f"  Reason: {reason[:80]}...")
        
        results.append({
            "id": scn["id"],
            "name": scn["name"],
            "src_ip": scn["event"]["src_ip"],
            "dest_port": scn["event"]["dest_port"],
            "verdict": verdict,
            "action": action,
            "confidence": confidence,
            "threat_type": threat_type,
            "latency_ms": round(lat, 2),
            "status": status,
            "reason": reason
        })
    
    out_json = "testbed/live_llm_inference_results.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved live inference dataset to {out_json}")

if __name__ == "__main__":
    main()
