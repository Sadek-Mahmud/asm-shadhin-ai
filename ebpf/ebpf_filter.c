// SPDX-License-Identifier: GPL-2.0
/*
 * ebpf_filter.c - High-Throughput Line-Rate XDP Packet Filter & AI Telemetry Hook
 * Target: Intel Core i5 4th Gen, PCIe 1Gbps NIC, Linux 5.15+ / 6.x
 *
 * Architecture:
 * 1. Fast-Path Drop: Zero-copy hardware/driver XDP inspection against blocked_ips_map.
 * 2. Tarpit Divert: Matches scanner/bot IPs to pass to local AI-Tarpit honey-ports.
 * 3. TinyML Telemetry: Streams sampled packet features to userspace via BPF RingBuffer.
 */

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#include "ebpf_common.h"

char _license[] SEC("license") = "GPL";

/* -------------------------------------------------------------------------
 * BPF MAP DEFINITIONS
 * ------------------------------------------------------------------------- */

/* Primary Hash Map for IP Blocking (Microsecond Fast-Path) */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_BLOCKED_IPS);
    __type(key, __u32);                 /* IPv4 Address in Network Byte Order */
    __type(value, struct block_entry);  /* Metadata & Drop Counter */
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} blocked_ips_map SEC(".maps");

/* Tarpit / Deception Redirection Map for Bot Trapping */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_TARPIT_IPS);
    __type(key, __u32);                 /* IPv4 Address */
    __type(value, struct tarpit_entry);
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} tarpit_ips_map SEC(".maps");

/* RingBuffer for Exporting Telemetry to TinyML Classifier / Daemon */
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, RINGBUF_OUTPUT_SIZE);
    __uint(pinning, LIBBPF_PIN_BY_NAME);
} packet_metrics_rb SEC(".maps");

/* Per-CPU timestamp tracking for packet arrival delta (jitter/entropy analysis) */
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} last_packet_time SEC(".maps");

/* -------------------------------------------------------------------------
 * HELPER FUNCTIONS
 * ------------------------------------------------------------------------- */

static __always_inline __u8 calculate_quick_entropy(const void *data, const void *data_end)
{
    /* Fast, verifier-safe byte diversity estimator for payload anomaly detection */
    const unsigned char *p = (const unsigned char *)data;
    __u32 count = 0;
    __u32 non_zero = 0;

    #pragma unroll
    for (int i = 0; i < 32; i++) {
        if ((const void *)(p + i + 1) > data_end)
            break;
        if (p[i] != 0x00 && p[i] != 0x20)
            non_zero++;
        count++;
    }

    if (count == 0)
        return 0;

    return (__u8)((non_zero * 100) / count);
}

/* -------------------------------------------------------------------------
 * XDP ENTRYPOINT
 * ------------------------------------------------------------------------- */

SEC("xdp")
int xdp_security_filter(struct xdp_md *ctx)
{
    void *data_end = (void *)(long)ctx->data_end;
    void *data     = (void *)(long)ctx->data;
    __u64 now_ns   = bpf_ktime_get_ns();

    /* 1. Parse Ethernet Header */
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS; /* Pass non-IPv4 traffic (ARP, IPv6, etc.) */

    /* 2. Parse IPv4 Header */
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    /* Enforce basic IPv4 header sanity */
    if (ip->ihl < 5 || (void *)((unsigned char *)ip + (ip->ihl * 4)) > data_end)
        return XDP_DROP;

    __u32 src_ip = ip->saddr;
    __u32 dst_ip = ip->daddr;
    __u8 proto   = ip->protocol;

    /* ---------------------------------------------------------------------
     * STEP 1: FAST-PATH BLOCKLIST LOOKUP (Zero-Copy Drop)
     * --------------------------------------------------------------------- */
    struct block_entry *b_entry = bpf_map_lookup_elem(&blocked_ips_map, &src_ip);
    if (b_entry) {
        /* Atomic counter increment for observability */
        __sync_fetch_and_add(&b_entry->drop_count, 1);
        return XDP_DROP;
    }

    /* ---------------------------------------------------------------------
     * STEP 2: TARPIT / DECEPTION CHECK
     * --------------------------------------------------------------------- */
    struct tarpit_entry *t_entry = bpf_map_lookup_elem(&tarpit_ips_map, &src_ip);
    if (t_entry && t_entry->active) {
        __sync_fetch_and_add(&t_entry->packet_count, 1);
        /* Allow packet to pass through to Linux networking stack where
         * iptables/nftables PREROUTING directs it to the AI-Tarpit port */
        return XDP_PASS;
    }

    /* ---------------------------------------------------------------------
     * STEP 3: TELEMETRY EXTRACTION FOR TINYML / DETECTOR
     * --------------------------------------------------------------------- */
    __u16 src_port = 0;
    __u16 dst_port = 0;
    __u8  tcp_flags = 0;
    void *transport_hdr = (void *)((unsigned char *)ip + (ip->ihl * 4));

    if (proto == IPPROTO_TCP) {
        struct tcphdr *tcp = transport_hdr;
        if ((void *)(tcp + 1) <= data_end) {
            src_port  = bpf_ntohs(tcp->source);
            dst_port  = bpf_ntohs(tcp->dest);
            tcp_flags = ((unsigned char *)tcp)[13]; /* Flags byte in standard TCP header */

            /* -------------------------------------------------------------
             * IN-KERNEL ANOMALY CLASSIFIER: IMMEDIATE WIRE-SPEED MITIGATION
             * ------------------------------------------------------------- */
            /* 1. Null Scan: TCP packet with 0 flags (RFC 793 violation, Nmap -sN) */
            if (tcp_flags == 0) {
                return XDP_DROP;
            }

            /* 2. Xmas Tree Scan: FIN + PSH + URG (0x29) (Nmap -sX) */
            if ((tcp_flags & 0x29) == 0x29) {
                return XDP_DROP;
            }

            /* 3. SYN + FIN: Illegal simultaneous connection open + teardown */
            if ((tcp_flags & 0x03) == 0x03) {
                return XDP_DROP;
            }
        }
    } else if (proto == IPPROTO_UDP) {
        struct udphdr *udp = transport_hdr;
        if ((void *)(udp + 1) <= data_end) {
            src_port = bpf_ntohs(udp->source);
            dst_port = bpf_ntohs(udp->dest);
        }
    }

    /* Calculate per-core inter-arrival jitter delta */
    __u32 zero = 0;
    __u64 *prev_time = bpf_map_lookup_elem(&last_packet_time, &zero);
    __u32 delta_us = 0;
    if (prev_time) {
        if (*prev_time > 0 && now_ns > *prev_time) {
            delta_us = (__u32)((now_ns - *prev_time) / 1000);
        }
        *prev_time = now_ns;
    }

    /* Selective Sampling to avoid RingBuffer contention at 1Gbps:
     * - Export ALL TCP SYN / FIN / RST connection attempts
     * - Export suspicious port scans (ports < 1024 or common proxy/honeypot targets)
     * - Sample 1 in 64 normal data packets */
    int should_sample = 0;
    if (proto == IPPROTO_TCP && (tcp_flags & (0x02 | 0x01 | 0x04))) { /* SYN, FIN, RST */
        should_sample = 1;
    } else if (dst_port == 22 || dst_port == 80 || dst_port == 443 || dst_port == 8080 || dst_port == 3389) {
        should_sample = 1;
    } else if ((now_ns & 0x3F) == 0) { /* 1-in-64 sampling mask */
        should_sample = 1;
    }

    if (should_sample) {
        struct packet_metric_event *event;
        event = bpf_ringbuf_reserve(&packet_metrics_rb, sizeof(*event), 0);
        if (event) {
            event->timestamp_ns          = now_ns;
            event->src_ip                = src_ip;
            event->dst_ip                = dst_ip;
            event->src_port              = src_port;
            event->dst_port              = dst_port;
            event->packet_length         = (__u16)(data_end - data);
            event->protocol              = proto;
            event->tcp_flags             = tcp_flags;
            event->inter_arrival_delta_us = delta_us;
            event->payload_entropy_hint  = calculate_quick_entropy(transport_hdr, data_end);

            bpf_ringbuf_submit(event, 0);
        }
    }

    return XDP_PASS;
}
