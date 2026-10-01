#!/usr/bin/env python3
"""
ASM-Shadhin-AI: Pure-Python Synthetic PCAP Generator
Generates realistic multi-vector security benchmark PCAP files without external dependencies.
Vectors included:
- Benign HTTP GET / DNS traffic
- TCP SYN Flood (DDoS simulation)
- UDP Flood (DDoS simulation)
- Port Scan (SYN scan pattern)
"""

import sys
import struct
import time
import socket
import random
import argparse

PCAP_GLOBAL_HEADER = struct.pack(
    '<IHHiIII',
    0xa1b2c3d4,  # Magic number (standard microsecond resolution)
    2, 4,        # Version 2.4
    0,           # GMT to local correction
    0,           # Accuracy of timestamps
    65535,       # Snaplen (max packet size)
    1            # Link-Layer type: 1 = LINKTYPE_ETHERNET
)

def checksum(data: bytes) -> int:
    if len(data) % 2 == 1:
        data += b'\x00'
    s = sum(struct.unpack(f'!{len(data)//2}H', data))
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

def build_eth(src_mac: bytes, dst_mac: bytes, eth_type: int = 0x0800) -> bytes:
    return dst_mac + src_mac + struct.pack('!H', eth_type)

def build_ipv4(src_ip: str, dst_ip: str, proto: int, payload_len: int, ttl: int = 64) -> bytes:
    ver_ihl = (4 << 4) | 5
    tos = 0
    total_len = 20 + payload_len
    ident = random.randint(1000, 65000)
    flags_frag = 0x4000  # DF flag
    chk = 0
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    header_without_chk = struct.pack('!BBHHHBBH4s4s', ver_ihl, tos, total_len, ident, flags_frag, ttl, proto, chk, src_bytes, dst_bytes)
    chk = checksum(header_without_chk)
    return struct.pack('!BBHHHBBH4s4s', ver_ihl, tos, total_len, ident, flags_frag, ttl, proto, chk, src_bytes, dst_bytes)

def build_tcp(src_ip: str, dst_ip: str, sport: int, dport: int, seq: int, ack: int, flags: int, payload: bytes = b'') -> bytes:
    offset_res = (5 << 4)  # 5 32-bit words, no options
    window = 64240
    urg_ptr = 0
    chk = 0
    header_no_chk = struct.pack('!HHIIBBHHH', sport, dport, seq, ack, offset_res, flags, window, chk, urg_ptr)
    # TCP pseudo-header for checksum
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    proto = 6
    tcp_len = len(header_no_chk) + len(payload)
    pseudo = struct.pack('!4s4sBBH', src_bytes, dst_bytes, 0, proto, tcp_len)
    chk = checksum(pseudo + header_no_chk + payload)
    return struct.pack('!HHIIBBHHH', sport, dport, seq, ack, offset_res, flags, window, chk, urg_ptr) + payload

def build_udp(src_ip: str, dst_ip: str, sport: int, dport: int, payload: bytes = b'') -> bytes:
    length = 8 + len(payload)
    chk = 0
    header_no_chk = struct.pack('!HHHH', sport, dport, length, chk)
    src_bytes = socket.inet_aton(src_ip)
    dst_bytes = socket.inet_aton(dst_ip)
    proto = 17
    pseudo = struct.pack('!4s4sBBH', src_bytes, dst_bytes, 0, proto, length)
    chk = checksum(pseudo + header_no_chk + payload)
    return struct.pack('!HHHH', sport, dport, length, chk) + payload

def generate_pcap(output_path: str, count: int = 50000, target_ip: str = "10.100.0.2"):
    src_mac = b'\x52\x54\x00\x12\x34\x01'
    dst_mac = b'\x52\x54\x00\x12\x34\x02'
    
    current_time = time.time()
    dt = 0.0001
    
    print(f"[+] Generating synthetic benchmark PCAP: {output_path}")
    print(f"[+] Total packets: {count}, Target SUT: {target_ip}")
    
    with open(output_path, 'wb') as f:
        f.write(PCAP_GLOBAL_HEADER)
        
        for i in range(count):
            current_time += dt
            ts_sec = int(current_time)
            ts_usec = int((current_time - ts_sec) * 1_000_000)
            
            # Mix attack types and benign
            category = random.choices(['benign_http', 'syn_flood', 'udp_flood', 'port_scan'], weights=[40, 30, 20, 10])[0]
            
            if category == 'benign_http':
                src_ip = f"10.100.0.{random.randint(10, 200)}"
                sport = random.randint(1024, 65535)
                payload = b"GET /index.html HTTP/1.1\r\nHost: 10.100.0.2\r\nUser-Agent: curl/7.81.0\r\nAccept: */*\r\n\r\n"
                tcp = build_tcp(src_ip, target_ip, sport, 80, seq=random.randint(1, 1000000), ack=0, flags=0x18, payload=payload)  # PSH+ACK
                ip = build_ipv4(src_ip, target_ip, proto=6, payload_len=len(tcp))
                pkt = build_eth(src_mac, dst_mac) + ip + tcp
                
            elif category == 'syn_flood':
                # Malicious high-frequency SYN packets with spoofed source IPs
                src_ip = f"198.51.100.{random.randint(1, 254)}"
                sport = random.randint(1024, 65535)
                dport = random.choice([80, 443, 8080, 22])
                tcp = build_tcp(src_ip, target_ip, sport, dport, seq=random.randint(1, 1000000), ack=0, flags=0x02)  # SYN
                ip = build_ipv4(src_ip, target_ip, proto=6, payload_len=len(tcp))
                pkt = build_eth(src_mac, dst_mac) + ip + tcp
                
            elif category == 'udp_flood':
                src_ip = f"203.0.113.{random.randint(1, 254)}"
                sport = random.randint(1024, 65535)
                dport = random.randint(10000, 60000)
                payload = b"\xde\xad\xbe\xef" * 32  # 128 bytes garbage
                udp = build_udp(src_ip, target_ip, sport, dport, payload=payload)
                ip = build_ipv4(src_ip, target_ip, proto=17, payload_len=len(udp))
                pkt = build_eth(src_mac, dst_mac) + ip + udp
                
            else:  # port_scan
                scanner_ip = "192.0.2.77"
                sport = random.randint(40000, 50000)
                dport = (i % 1024) + 1  # Sequential scan
                tcp = build_tcp(scanner_ip, target_ip, sport, dport, seq=random.randint(1, 1000000), ack=0, flags=0x02)  # SYN
                ip = build_ipv4(scanner_ip, target_ip, proto=6, payload_len=len(tcp))
                pkt = build_eth(src_mac, dst_mac) + ip + tcp
                
            pcap_pkt_hdr = struct.pack('<IIII', ts_sec, ts_usec, len(pkt), len(pkt))
            f.write(pcap_pkt_hdr + pkt)
            
            if (i + 1) % 10000 == 0:
                print(f"  -> Generated {i + 1}/{count} packets...")
                
    print(f"[✔] Successfully generated {output_path} ({count} packets).")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Synthetic PCAP benchmark generator")
    parser.add_argument("--output", "-o", default="benchmark_traffic.pcap", help="Output PCAP filename")
    parser.add_argument("--count", "-n", type=int, default=50000, help="Number of packets")
    parser.add_argument("--target", "-t", default="10.100.0.2", help="Target SUT IP")
    args = parser.parse_args()
    
    generate_pcap(args.output, count=args.count, target_ip=args.target)
