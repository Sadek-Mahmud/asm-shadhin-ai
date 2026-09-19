/* SPDX-License-Identifier: GPL-2.0 */
/*
 * ebpf_common.h - Shared kernel and userspace definitions for AI-Driven Security Monitoring
 */

#ifndef __EBPF_COMMON_H__
#define __EBPF_COMMON_H__

#include <linux/types.h>

#define MAX_BLOCKED_IPS       65536
#define MAX_TARPIT_IPS        16384
#define RINGBUF_OUTPUT_SIZE   (1024 * 1024) /* 1MB RingBuffer */

/* Action / Reason codes */
enum block_reason_code {
    REASON_MANUAL_ADMIN       = 1,
    REASON_SURICATA_SEV1      = 2,
    REASON_OLLAMA_AI_INLINE   = 3,
    REASON_SYN_FLOOD          = 4,
    REASON_PORT_SCAN          = 5,
    REASON_TINYML_ANOMALY     = 6,
    REASON_AI_BOT_DECEPTION   = 7,
    REASON_XMAS_SCAN          = 8,
    REASON_NULL_SCAN          = 9,
    REASON_C2_BEACON          = 10,
    REASON_MTD_PROBE          = 11,
};

/* Value for blocked_ips_map */
struct block_entry {
    __u64 timestamp_ns;       /* Time when blocked */
    __u64 drop_count;         /* Number of packets dropped in kernel */
    __u32 ttl_seconds;        /* TTL in seconds; 0 means permanent */
    __u8  reason_code;        /* enum block_reason_code */
    __u8  reserved[3];
};

/* Value for tarpit_redirect_map */
struct tarpit_entry {
    __u64 timestamp_ns;
    __u64 packet_count;
    __u16 redirect_port;      /* Local decoy port (e.g. 8088 / 2222) */
    __u8  active;
    __u8  reserved[5];
};

/* Packet metric event exported via RingBuffer to TinyML / Userspace */
struct packet_metric_event {
    __u64 timestamp_ns;
    __u32 src_ip;             /* Network byte order */
    __u32 dst_ip;             /* Network byte order */
    __u16 src_port;
    __u16 dst_port;
    __u16 packet_length;
    __u8  protocol;           /* IPPROTO_TCP, IPPROTO_UDP, IPPROTO_ICMP */
    __u8  tcp_flags;          /* SYN, ACK, FIN, RST, PSH, URG */
    __u32 inter_arrival_delta_us; /* Delta from previous packet on same CPU */
    __u8  payload_entropy_hint;   /* Fast approximation of byte entropy */
    __u8  pad[3];
};

#endif /* __EBPF_COMMON_H__ */
