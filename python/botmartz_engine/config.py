"""Runtime configuration loader for Botmartz VORTEX Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_candidates = [
        Path(__file__).resolve().parents[3] / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_candidates:
        if env_path.is_file():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
            break


_load_dotenv()


@dataclass(frozen=True)
class VortexSettings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    llamacpp_base_url: str = os.getenv("LLAMACPP_BASE_URL", "http://localhost:8081")
    vllm_base_url: str = os.getenv("VLLM_BASE_URL", "")
    vllm_model: str = os.getenv("VLLM_MODEL", "")
    sglang_base_url: str = os.getenv("SGLANG_BASE_URL", "")
    ai_vault_models_dir: Path = Path(os.getenv("AI_VAULT_MODELS_DIR", "/mnt/ai_vault/models"))
    data_dir: Path = Path(
        os.getenv(
            "VORTEX_DATA_DIR",
            str(Path(__file__).resolve().parents[3] / "data"),
        )
    )
    port: int = int(os.getenv("VORTEX_PORT", "8420"))


settings = VortexSettings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
