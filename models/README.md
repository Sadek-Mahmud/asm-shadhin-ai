# Bundled Local Models Directory (Air-Gapped / Offline Deployment)

This directory stores offline GGUF quantized AI models so the security system can run immediately without internet access.

## Expected File:
- `asm-shadhin-ai-q4_k_m.gguf` (~1.9 GB)

## How to populate:
1. **Automated**: Run `bash scripts/package_offline_release.sh` on any PC with internet.
2. **Manual**: Download the GGUF file from Hugging Face:
   - Place `asm-shadhin-ai-q4_k_m.gguf` in this `models/` directory.

