"""
tarpit_service.py - AI-Tarpit & Bot Deception Engine
Honeypot service designed to delay, trap, and token-drain automated AI agents and scanners.

Strategies:
1. Infinite Context Drain: Feeds recursive, hallucinated synthetic Linux configurations,
   database dumps, and code repos to exhaust the LLM context window of autonomous AI agents.
2. Trickle-Throttling: Sends bytes in 10-50ms chunks (slow HTTP / slow SSH banner) to tie up
   scanner worker threads and client sockets indefinitely.
3. LLM-Assisted Deception: Leverages local asm-shadhin-ai to generate hyper-realistic, deceptive
   responses tailored to attacker queries.
"""

import asyncio
import logging
import socket
import json
import time
HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    pass

import sys
from typing import Optional
from pathlib import Path

_daemon_dir = str(Path(__file__).resolve().parent)
if _daemon_dir not in sys.path:
    sys.path.insert(0, _daemon_dir)

from config import (
    TARPIT_HOST,
    TARPIT_HTTP_PORT,
    TARPIT_SSH_PORT,
    TARPIT_CHUNK_DELAY_MS,
    TARPIT_MAX_DRAIN_TOKENS,
    OLLAMA_HOST,
    OLLAMA_MODEL,
)

logger = logging.getLogger("tarpit_service")


class AITarpitService:
    """Async AI-Tarpit server listening on decoy ports."""

    def __init__(self):
        self.chunk_delay = TARPIT_CHUNK_DELAY_MS / 1000.0
        self.http_client = httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=10.0) if HTTPX_AVAILABLE else None


    async def query_llm_deception(self, attacker_input: str) -> str:
        """Ask asm-shadhin-ai to synthesize a deceptive, convoluted payload to trap the attacker."""
        prompt = (
            f"MODE: DECEPTION_PAYLOAD\n"
            f"ATTACKER_INPUT: {attacker_input[:200]}\n"
            f"INSTRUCTION: Generate a realistic Unix bash shell output or API response containing "
            f"deep nested file structures, cryptic internal hostnames, and fake high-value API keys "
            f"designed to confuse an automated AI penetration testing agent."
        )
        try:
            if HTTPX_AVAILABLE and self.http_client:
                resp = await self.http_client.post(
                    "/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 256
                        }
                    }
                )
                if resp.status_code == 200:
                    body = resp.json()
                    if "error" in body:
                        logger.warning("Ollama tarpit error: %s — using static fallback.", body["error"])
                        return self.generate_infinite_linux_tree(3)
                    return body.get("response", "").strip()
            else:
                import urllib.request
                url = f"{OLLAMA_HOST.rstrip('/')}/api/generate"
                payload = json.dumps({
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 256
                    }
                }).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                loop = asyncio.get_event_loop()
                def _do_req():
                    with urllib.request.urlopen(req, timeout=10.0) as r:
                        return json.loads(r.read().decode("utf-8"))
                res_data = await loop.run_in_executor(None, _do_req)
                if "error" in res_data:
                    logger.warning("Ollama urllib tarpit error: %s — using static fallback.", res_data["error"])
                    return self.generate_infinite_linux_tree(3)
                return res_data.get("response", "").strip()
        except Exception as e:
            logger.debug("Ollama deception generation fallback: %s", e)

        # High-entropy fallback synthetic response
        return self.generate_infinite_linux_tree(3)

    def generate_honey_token(self, category: str = "all") -> str:
        """Generates realistic high-entropy poisoned honey-tokens to trace attackers."""
        import random
        tokens = [
            "AKIA" + "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=16)),
            "ghp_" + "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", k=36)),
            "sk_live_" + "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyz", k=24)),
            "sk-proj-" + "".join(random.choices("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", k=48))
        ]
        return random.choice(tokens)

    def generate_infinite_linux_tree(self, depth: int = 3) -> str:
        """Generates a deep, recursive decoy directory tree with poisoned tokens to exhaust bots."""
        token = self.generate_honey_token()
        tree = (
            f"drwxr-xr-x 14 root root 4096 Sep 19 03:12 .config_backup_v2\n"
            f"-rw-------  1 root root 8192 Sep 19 03:14 master_ai_token.key.enc\n"
            f"-rw-r--r--  1 root root 2048 Sep 19 03:15 internal_cluster_manifest.yaml\n"
            f"-rw-r--r--  1 root root  512 Sep 19 03:18 .env.production\n"
            f"   export AWS_ACCESS_KEY_ID={token}\n"
            f"   export CLUSTER_SECRET_HASH=0x9f8b4e72a1\n"
            f"drwxr-xr-x  6 root root 4096 Sep 19 03:20 k8s_secrets_vault/\n"
            f"ACCESS DENIED: Kernel Level 4 MFA Challenge Required.\n"
        )
        return tree

    async def handle_ssh_tarpit(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Simulate an agonizingly slow SSH / Telnet daemon (Infinite Banner Tarpit)."""
        peer = writer.get_extra_info("peername")
        attacker_ip = peer[0] if peer else "unknown"
        logger.info("[TARPIT-SSH] Trapped connection from: %s", attacker_ip)

        try:
            # Send initial OpenSSH banner slowly
            banner = b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6_internal_mfa\r\n"
            for byte in banner:
                writer.write(bytes([byte]))
                await writer.drain()
                await asyncio.sleep(self.chunk_delay)

            # Continuous slow trickle of cryptographic challenge prompts
            rounds = 0
            while rounds < 100:
                rounds += 1
                prompt = f"Authenticated MFA Challenge #{rounds}: Enter hardware security token OTP: ".encode()
                for char in prompt:
                    writer.write(bytes([char]))
                    await writer.drain()
                    await asyncio.sleep(self.chunk_delay)

                # Read attacker's input
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=30.0)
                    if not line:
                        break
                    logger.info("[TARPIT-SSH] Attacker %s attempted input: %s", attacker_ip, line.strip())
                except asyncio.TimeoutError:
                    pass

                writer.write(b"\r\nVerification token timeout. Recalculating quantum state vector...\r\n")
                await writer.drain()
                await asyncio.sleep(1.0)

        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            logger.info("[TARPIT-SSH] Attacker disconnected: %s", attacker_ip)
            writer.close()
            await writer.wait_closed()

    async def handle_http_tarpit(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Simulate a vulnerable-looking HTTP endpoint that endlessly trickles deceptive data."""
        peer = writer.get_extra_info("peername")
        attacker_ip = peer[0] if peer else "unknown"
        logger.info("[TARPIT-HTTP] Trapped bot scan from: %s", attacker_ip)

        try:
            # Read request line
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            req_str = request_line.decode(errors="ignore").strip()
            logger.info("[TARPIT-HTTP] Request from %s: %s", attacker_ip, req_str)

            # Consume headers
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                if line in (b"\r\n", b"\n", b""):
                    break

            # Send HTTP 200 with Chunked Transfer Encoding to keep the connection streaming forever
            headers = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                "Transfer-Encoding: chunked\r\n"
                "Server: Enterprise-Internal-Core/4.11-PQC\r\n"
                "X-AI-Security-Notice: Telemetry Logging Active\r\n"
                "\r\n"
            ).encode()
            writer.write(headers)
            await writer.drain()

            # Query asm-shadhin-ai for deception seed
            deceptive_content = await self.query_llm_deception(req_str)

            # Stream infinite recursive maze chunks
            chunk_count = 0
            while chunk_count < (TARPIT_MAX_DRAIN_TOKENS // 16):
                chunk_count += 1
                fake_line = (
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] TRACE ID #{chunk_count:05d}: "
                    f"NODE internal-ai-{chunk_count % 8}.local - "
                    f"DATA: {deceptive_content} "
                    f"-- ENTROPY DRAIN: 0x{chunk_count:08x}\n"
                ).encode()

                chunk_hdr = f"{len(fake_line):X}\r\n".encode()
                writer.write(chunk_hdr)
                writer.write(fake_line)
                writer.write(b"\r\n")
                await writer.drain()

                # Rate throttle (Trickle) to exhaust attacker time & token budget
                await asyncio.sleep(self.chunk_delay)

        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError, asyncio.TimeoutError):
            pass
        finally:
            logger.info("[TARPIT-HTTP] Connection finished for attacker: %s", attacker_ip)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def run(self):
        """Start both HTTP and SSH honeypot tarpit listeners."""
        server_http = await asyncio.start_server(
            self.handle_http_tarpit,
            TARPIT_HOST,
            TARPIT_HTTP_PORT
        )
        server_ssh = await asyncio.start_server(
            self.handle_ssh_tarpit,
            TARPIT_HOST,
            TARPIT_SSH_PORT
        )

        addrs_http = ", ".join(str(sock.getsockname()) for sock in server_http.sockets)
        addrs_ssh = ", ".join(str(sock.getsockname()) for sock in server_ssh.sockets)
        logger.info("[★] AI-Tarpit Engine Online. HTTP Decoy: %s | SSH Decoy: %s", addrs_http, addrs_ssh)

        async with server_http, server_ssh:
            await asyncio.gather(server_http.serve_forever(), server_ssh.serve_forever())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    daemon = AITarpitService()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("AI-Tarpit daemon interrupted by user.")
