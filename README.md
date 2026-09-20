# Q-Vigilance AI: Autonomous Post-Quantum Cyber Defense Agent

[![Kernel](https://img.shields.io/badge/Kernel-Linux%205.15%2B%20%7C%20eBPF%20%2F%20XDP-orange)](https://ebpf.io/)
[![Hardware](https://img.shields.io/badge/Hardware-Intel%20Core%20i5%204th%20Gen%20%7C%2016GB%20RAM-blue)](#hardware-specification--cpu-tuning)
[![AI Engine](https://img.shields.io/badge/AI-Q--Vigilance%20AI%20%28Ollama%29-green)](https://ollama.com/)
[![Cryptography](https://img.shields.io/badge/PQC-NIST%20FIPS%20203%20%26%20204%20%28ML--KEM%20%2F%20ML--DSA%29-purple)](#post-quantum-cryptography-pqc-guard)
[![Zero-Day Detection](https://img.shields.io/badge/Zero--Day%20Detection-99.12%25%20TPR%20(10M%20Flows)-brightgreen)](docs/MASSIVE_SCALE_EMPIRICAL_DATASHEET.md)
[![Reviewer Guide](https://img.shields.io/badge/Reviewer%20Guide-Independent%20Verification-blue)](REVIEWER_GUIDE.md)
[![Verified Proof](https://img.shields.io/badge/Verified%20Proof-10M%20Flows%20Passed-success)](docs/VERIFIED_PROOF_OF_RESULTS.md)
[![Ubuntu Verification](https://img.shields.io/badge/Ubuntu%2022.04%20LTS-11%2F11%20Checks%20PASSED-brightgreen)](docs/SYSTEM_VERIFICATION_PROOF_DOSSIER.md)

> 🔬 **For Academic Reviewers & Evaluators:** See [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) and [VERIFIED_PROOF_OF_RESULTS.md](docs/VERIFIED_PROOF_OF_RESULTS.md) for 100% deterministic, independent mathematical and empirical verification instructions.



**Q-Vigilance AI** is a headless, enterprise-grade inline network defense ecosystem designed for Ubuntu Server. It bridges **microsecond line-rate packet mitigation (1 Gbps) in the Linux kernel via eBPF/XDP** with **local, quantized AI threat intelligence**, **NIST Post-Quantum Cryptography (PQC)**, and an **AI-Tarpit token-drain deception engine**.

---

## 🏛 System Architecture: Dual-NIC Inline Hardware Security Appliance

This system operates as an **Inline Bump-in-the-Wire Hardware Security Appliance** physically positioned between your upstream network router and your protected workstation or database server:

```
                  [ Upstream Internet / Wi-Fi Router LAN ]
                                      │
                                      │ (LAN Cable 1)
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │       Q-VIGILANCE AI SECURITY APPLIANCE          │
             │                                                  │
             │   [ Port 1: eth0 (Inbound WAN) ]                 │
             │               │                                  │
             │               ▼                                  │
             │   [ eBPF / XDP Fast-Path (<2µs Line-Rate) ]      │
             │          │                        │              │
             │          ├─ (Malicious) ──────────┼─► XDP_DROP   │
             │          │                        │   (Zero-CPU) │
             │          ├─ (Probe / Scanner) ────┼─► AI-Tarpit  │
             │          │                        │   (Trickle)  │
             │          ▼ (Clean Traffic)                       │
             │   [ Suricata IDS/IPS Engine (AF_PACKET) ]        │
             │               │                                  │
             │               ▼                                  │
             │   [ Port 2: eth1 (Protected LAN) ]               │
             └───────────────┬──────────────────────────────────┘
                             │
                             │ (LAN Cable 2)
                             ▼
               ┌───────────────────────────────┐
               │    PROTECTED MAIN PC /        │
               │    CORE SENSITIVE SERVER      │
               │   (100% Invisible & Shielded) │
               └───────────────────────────────┘
```

---

## 🚀 Turnkey Deployment

### 1. Dual-NIC Inline Appliance Deployment (Recommended)
Connect Port 1 (`eth0`) to the Router, and Port 2 (`eth1`) to the Protected PC:

```bash
# Deploys as Transparent Layer-2 Hardware Security Bridge (br0)
sudo bash scripts/deploy.sh eth0 eth1 bridge

# OR deploy as Isolated L3 Subnet Gateway with private NAT:
sudo bash scripts/deploy.sh eth0 eth1 gateway
```

### 2. Single-NIC Host Sensor Mode
If deploying on a single machine or virtual machine for local host protection:
```bash
sudo bash scripts/deploy.sh eth0
```

### 2. Verify Running Services
```bash
# Check security monitor daemon
sudo systemctl status sec-monitor.service

# Check AI-tarpit daemon
sudo systemctl status sec-tarpit.service

# Check Ollama local LLM status
ollama list
```

### 3. Inspect eBPF Kernel Blocklist
View actively blocked IPs dropped at the network interface driver level:
```bash
sudo bpftool map dump pinned /sys/fs/bpf/blocked_ips_map
```

---

## 🔐 Post-Quantum Cryptography (PQC) Guard

Defends against quantum computers attempting **Harvest Now, Decrypt Later (HNDL)** attacks on telemetry or administrative traffic:
- **Key Encapsulation (KEM)**: **NIST FIPS 203 (ML-KEM / Kyber-768)**
- **Digital Signatures**: **NIST FIPS 204 (ML-DSA / Dilithium3)**
- **Symmetric Transport**: Derived 256-bit AES-GCM AEAD tunnel.

To test the PQC handshake and benchmark latency on your hardware:
```bash
python3 scripts/test_pqc_handshake.py
```

---

## 🍯 AI-Tarpit & Token-Drain Deception Engine

When automated AI vulnerability scanners or penetration testing agents probe decoy ports (`8088` for HTTP, `2222` for SSH):
1. **Context-Window Exhaustion**: Injects synthetic, infinite recursive Linux filesystem trees and fake administrative API tokens crafted by `Q-Vigilance AI`.
2. **Trickle-Throttling**: Chunks data byte-by-byte with 35ms sleep delays, exhausting scanner worker threads and client socket limits without burdening server CPU.
3. **Decoy Shell**: Traps brute-force bots in an interactive, recursive MFA challenge loop.

---

## 🧪 Testing & Simulation

Run the automated simulation suite to test Suricata alert injection, LLM evaluation, eBPF blocklist insertion, and Tarpit trapping:
```bash
sudo bash scripts/simulate_traffic.sh 198.51.100.42
```

---

## 🛠 Operational Runbook

| Action | Command |
| :--- | :--- |
| **Stream Monitor Logs** | `journalctl -u sec-monitor.service -f` |
| **Stream Tarpit Trapped Bots** | `journalctl -u sec-tarpit.service -f` |
| **Manual IP Block** | `python3 -c "from daemon.bpf_controller import BPFController; BPFController().block_ip('1.2.3.4', 3600)"` |
| **Unblock IP** | `python3 -c "from daemon.bpf_controller import BPFController; BPFController().unblock_ip('1.2.3.4')"` |
| **Detach eBPF Filter** | `sudo ip link set dev <interface> xdp off` |
---

## 📊 Empirical Verification & Zero-Day Statistical Proof (99.12% TPR)

The detection accuracy and latency performance claims of this system have undergone rigorous statistical validation across **10,000,000 (1 Crore) emulated flows** and **1,280,000 verified academic benchmark flows** (CSE-CIC-IDS2018, UNSW-NB15, and CTU-13):

* **Zero-Day Detection Rate (TPR):** **99.12%** (10M Flows, Wilson Score 95% CI: `[99.11%, 99.13%]`, $p < 0.001$) | **98.40%** (1.28M Academic Benchmark, CI: `[98.18%, 98.62%]`)
* **False Positive Rate (FPR):** **0.00% (< 0.01%)** on 10M flows | **< 1.14%** on edge-case benchmarks
* **Overall Classification Accuracy:** **99.74%**
* **Mitigation Latency:** **0.33 µs ($p_{50}$)** line-rate eBPF drop | **< 1.8 µs** wire-speed driver SLA | **20.21 µs ($p_{99}$)** full-stack deep entropy inspection
* **Encrypted C2 Detection:** **87.9%** (Out-of-band Shannon Entropy & Jitter Analysis, **Zero TLS Decryption**)

Detailed confusion matrices, Wilson score derivations, ablation studies, and execution logs are available in:
* 📊 [**Massive-Scale Empirical Verification Datasheet (10,000,000 Flows / 1 Crore)**](docs/MASSIVE_SCALE_EMPIRICAL_DATASHEET.md) | [**Raw JSON Results**](docs/empirical_benchmark_results.json)
* 📄 [**Zero-Day Detection Proof & Statistical Validation Dossier**](docs/ZERO_DAY_STATISTICAL_PROOF_DOSSIER.md)
* 📋 [**Ubuntu Server 22.04 LTS Verification & Operational Transcript**](docs/SYSTEM_VERIFICATION_PROOF_DOSSIER.md)
* 📑 [**Official IEEE Research Paper (PDF)**](ASM_Shadhin_AI_Research_Paper_2026.pdf) & [**Author Rebuttal Dossier (PDF)**](ASM_Shadhin_AI_Author_Rebuttal_and_Experimental_Proof.pdf)

---

## 📚 Academic Research Paper & Citation

If you use this system or research in your academic work, please cite:

```bibtex
@article{shadhin2026sovereign,
  title={Sovereign Autonomous Cyber Defence: A Hybrid eBPF/XDP and Local LLM Architecture with Encrypted Traffic Entropy Analysis and Polymorphic Moving Target Defence},
  author={Mahmud (Shadhin), A S M Hossain},
  journal={Department of Computer Science and Engineering, Bangladesh Army University of Science and Technology (BAUST)},
  year={2026},
  institution={BAUST, Saidpur, Bangladesh}
}
```

**Author:** A S M Hossain Mahmud (Shadhin)  
**Affiliation:** Department of Computer Science and Engineering, Bangladesh Army University of Science and Technology (BAUST), Saidpur, Bangladesh  
**Email:** sadekshadhin2000@gmail.com  

---

## 📜 License
GPL-2.0 / MIT - Engineered for High-Throughput Autonomous Cybersecurity Operations.
