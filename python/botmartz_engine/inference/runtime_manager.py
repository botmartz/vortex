"""Runtime & Accelerator Orchestrator for vLLM, SGLang, llama.cpp, Ollama, and OpenAI.

Hardware-agnostic and horizontally scalable: adapts tensor-parallel configs dynamically
to the host operator's accelerator topology without hardcoding private workstation specs.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import httpx

from ..config import settings


class VortexRuntimeClusterManager:
    """Inspects host compute accelerators, local binaries, model artifacts, and serving profiles."""

    LLAMA_SERVER_CANDIDATES = [
        Path("/usr/local/bin/llama-server"),
        Path("/home/soham/llama.cpp/build/bin/llama-server"),
    ]

    def detect_cluster_hardware(self) -> Dict[str, Any]:
        gpus: List[Dict[str, Any]] = []
        total_vram_mib = 0
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.used,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                check=False,
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        mem_tot = int(parts[2])
                        mem_used = int(parts[3])
                        util = int(parts[4])
                        total_vram_mib += mem_tot
                        gpus.append(
                            {
                                "index": int(parts[0]),
                                "name": parts[1],
                                "memory_total_mib": mem_tot,
                                "memory_used_mib": mem_used,
                                "utilization_pct": util,
                            }
                        )
        except Exception:
            pass

        llama_bin = next((str(p) for p in self.LLAMA_SERVER_CANDIDATES if p.is_file()), shutil.which("llama-server"))
        return {
            "gpu_count": len(gpus),
            "total_vram_gb": round(total_vram_mib / 1024.0, 2),
            "gpus": gpus,
            "binaries": {
                "llama_server": bool(llama_bin),
                "ollama": bool(shutil.which("ollama")),
                "vllm": bool(shutil.which("vllm")),
                "sglang": bool(shutil.which("sglang")),
            },
        }

    def scan_ready_local_models(self) -> Dict[str, List[Dict[str, Any]]]:
        llm_gguf: List[Dict[str, Any]] = []
        embeddings_rerankers: List[Dict[str, Any]] = []
        multimodal_vision_audio: List[Dict[str, Any]] = []

        root = settings.ai_vault_models_dir
        if not root.exists():
            return {
                "llm_gguf": llm_gguf,
                "embeddings_rerankers": embeddings_rerankers,
                "multimodal_vision_audio": multimodal_vision_audio,
            }

        seen_paths: set[str] = set()
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            if p.name.endswith(".part") or p.suffix not in {".gguf", ".safetensors", ".bin"}:
                continue
            real_str = str(p.resolve())
            if real_str in seen_paths:
                continue
            seen_paths.add(real_str)

            size_gb = round(p.stat().st_size / (1024**3), 2)
            entry = {
                "name": p.name,
                "folder": p.parent.name,
                "path": str(p),
                "size_gb": size_gb,
            }
            low = str(p).lower()
            if "bge-m3" in low or "reranker" in low:
                embeddings_rerankers.append(entry)
            elif "whisper" in low or "vl" in low or "comfy" in low or "loras" in low or "vae" in low or "unet" in low:
                multimodal_vision_audio.append(entry)
            elif p.suffix == ".gguf":
                llm_gguf.append(entry)

        return {
            "llm_gguf": llm_gguf,
            "embeddings_rerankers": embeddings_rerankers,
            "multimodal_vision_audio": multimodal_vision_audio,
        }

    def _probe_http_endpoint(self, url: str) -> bool:
        try:
            with httpx.Client(timeout=1.0) as client:
                r = client.get(url)
                return r.status_code < 500
        except Exception:
            return False

    def get_runtime_profiles(self, gpu_count: int = 1) -> List[Dict[str, Any]]:
        tp = max(1, gpu_count)
        split_arg = ",".join(["1"] * tp)
        ollama_online = self._probe_http_endpoint(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        sglang_url = (settings.sglang_base_url or "http://127.0.0.1:30000").rstrip("/")
        vllm_url = (settings.vllm_base_url or "http://127.0.0.1:8001").rstrip("/")
        llamacpp_url = "http://127.0.0.1:8081"

        sglang_online = self._probe_http_endpoint(f"{sglang_url}/v1/models")
        vllm_online = self._probe_http_endpoint(f"{vllm_url}/v1/models")
        llamacpp_online = self._probe_http_endpoint(f"{llamacpp_url}/health")

        return [
            {
                "id": "sglang_radix",
                "name": f"SGLang RadixAttention Serving (TP={tp})",
                "role": "Primary CAG Radix KV-Cache + xgrammar Deterministic JSON",
                "status": "online" if sglang_online else "ready_to_launch",
                "endpoint": sglang_url,
                "command": (
                    f"python -m sglang.launch_server --model-path Qwen/Qwen3-30B-A3B-FP8 "
                    f"--tp {tp} --enable-radix-cache --grammar-backend xgrammar --port 30000"
                ),
                "recommended_for": "Sub-20ms CAG prefix reuse & multi-turn agent state machines",
            },
            {
                "id": "vllm_apc",
                "name": f"vLLM PagedAttention + APC (TP={tp})",
                "role": "High-Throughput Batch Serving + Speculative Decoding",
                "status": "online" if vllm_online else "ready_to_launch",
                "endpoint": vllm_url,
                "command": (
                    f"vllm serve Qwen/Qwen3-30B-A3B-FP8 --tensor-parallel-size {tp} "
                    f"--enable-prefix-caching --gpu-memory-utilization 0.90 --port 8001"
                ),
                "recommended_for": "High-concurrency enterprise serving & continuous batching",
            },
            {
                "id": "llamacpp_cuda",
                "name": "llama.cpp Server (Configurable Split)",
                "role": "Lightweight Local GGUF Runtime with KV Prefix Reuse",
                "status": "online" if llamacpp_online else "ready_to_launch",
                "endpoint": llamacpp_url,
                "command": (
                    f"llama-server -m <MODEL_PATH.gguf> -ngl 99 --split-mode layer "
                    f"--tensor-split {split_arg} -c 32768 --cache-reuse 256 --port 8081"
                ),
                "recommended_for": "Low-overhead quantized GGUF inference on operator hardware",
            },
            {
                "id": "ollama_local",
                "name": f"Ollama Endpoint ({settings.ollama_model})",
                "role": "Pluggable Local & Cloud Model Router",
                "status": "online" if ollama_online else "offline",
                "endpoint": settings.ollama_base_url,
                "command": f"ollama run {settings.ollama_model}",
                "recommended_for": "Instant BYO-Model connectivity & model discovery via /api/tags",
            },
            {
                "id": "openai_support",
                "name": f"OpenAI / Cloud API ({settings.openai_model})",
                "role": "Vision OCR + NL-to-SQL + Cloud Verification",
                "status": "online" if settings.openai_api_key else "unconfigured",
                "endpoint": "https://api.openai.com/v1",
                "command": "Configured via OPENAI_API_KEY / Custom Connector",
                "recommended_for": "Multimodal document OCR & cloud burst scaling",
            },
        ]

    def get_jax_assessment(self, gpu_count: int = 0) -> Dict[str, Any]:
        return {
            "jax_required": False,
            "verdict": "JAX Optional / Not Required for CUDA Workloads — Use PyTorch + Triton + FlashInfer",
            "hardware_target": (
                f"Detected {gpu_count} CUDA Accelerator(s) — Elastic BYO-GPU / BYO-Cloud Deployment"
                if gpu_count > 0
                else "Cloud / CPU / Operator-Managed GPU Cluster"
            ),
            "reasons": [
                "SGLang RadixAttention, vLLM PagedAttention, and FlashInfer are built on PyTorch, Triton, and CUDA C++.",
                "JAX / XLA excels primarily on Google Cloud TPUs, whereas GPU serving benefits from Paged/Radix KV kernels.",
                "Operators can plug in any OpenAI-compatible cluster URL (vLLM, SGLang, Ollama, or TGI/TPU gateway) per tenant.",
            ],
            "recommended_stack": [
                "PyTorch + Triton + FlashInfer (SGLang / vLLM)",
                "GGML / CUDA / Metal (llama.cpp & Ollama)",
                "Botmartz Rust + Arrow/LanceDB + DuckDB 2.0 + SmithDB",
            ],
        }

    def get_full_cluster_report(self) -> Dict[str, Any]:
        hw = self.detect_cluster_hardware()
        return {
            "hardware": hw,
            "local_models": self.scan_ready_local_models(),
            "runtime_profiles": self.get_runtime_profiles(gpu_count=hw.get("gpu_count", 1)),
            "jax_assessment": self.get_jax_assessment(gpu_count=hw.get("gpu_count", 0)),
        }
