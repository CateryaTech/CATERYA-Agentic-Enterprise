"""
CATERYA LLM Router — Offline-First, Privacy-Native
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

Architecture:
  1. Always try Ollama first (100% offline, local)
  2. Auto-detect internet connectivity
  3. If online, fall back to free-tier cloud APIs (no paid key)
  4. Smart model selection per task type
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
from enum import Enum
from typing import Any

import httpx
from langchain_core.language_models import BaseLLM, BaseLanguageModel
from pydantic import BaseModel

from src.core.state_manager import get_logger

logger = get_logger(__name__)


def _env(key: str, default: str = "") -> str:
    """Get env var, fallback to Streamlit secrets if on cloud."""
    val = os.getenv(key, default)
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, default)
        except Exception:
            pass
    return val or default


class TaskType(str, Enum):
    REASONING = "reasoning"
    CODING = "coding"
    FAST = "fast"
    MULTIMODAL = "multimodal"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    CRYPTO = "crypto"


class LLMConfig(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096
    supports_function_calling: bool = True
    supports_vision: bool = False


# ─── Model Registry ──────────────────────────────────────────────────────────

OLLAMA_MODELS: dict[TaskType, LLMConfig] = {
    TaskType.REASONING: LLMConfig(
        provider="ollama",
        model=_env("OLLAMA_DEFAULT_MODEL", "qwen2.5:72b"),
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
    ),
    TaskType.CODING: LLMConfig(
        provider="ollama",
        model=_env("OLLAMA_CODE_MODEL", "deepseek-coder:latest"),
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
    ),
    TaskType.FAST: LLMConfig(
        provider="ollama",
        model=_env("OLLAMA_FAST_MODEL", "phi4:latest"),
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.1,
        max_tokens=2048,
    ),
    TaskType.MULTIMODAL: LLMConfig(
        provider="ollama",
        model=_env("OLLAMA_VISION_MODEL", "llama4:vision"),
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        supports_vision=True,
    ),
    TaskType.CREATIVE: LLMConfig(
        provider="ollama",
        model="mistral:latest",
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.7,
    ),
    TaskType.ANALYSIS: LLMConfig(
        provider="ollama",
        model="qwen2.5:32b",
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
    ),
    TaskType.CRYPTO: LLMConfig(
        provider="ollama",
        model="llama3.3:latest",
        base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.0,
    ),
}

FREE_CLOUD_MODELS: dict[TaskType, list[LLMConfig]] = {
    TaskType.REASONING: [
        LLMConfig(
            provider="groq",
            model=_env("GROQ_MODEL", "llama-3.3-70b-versatile"),
            base_url="https://api.groq.com/openai/v1",
            api_key=_env("GROQ_API_KEY"),
        ),
        LLMConfig(
            provider="together",
            model=_env("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            base_url="https://api.together.xyz/v1",
            api_key=_env("TOGETHER_API_KEY"),
        ),
    ],
    TaskType.CODING: [
        LLMConfig(
            provider="fireworks",
            model=_env("FIREWORKS_MODEL", "accounts/fireworks/models/deepseek-coder-v2-lite-instruct"),
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=_env("FIREWORKS_API_KEY"),
        ),
    ],
    TaskType.FAST: [
        LLMConfig(
            provider="groq",
            model="gemma2-9b-it",
            base_url="https://api.groq.com/openai/v1",
            api_key=_env("GROQ_API_KEY"),
        ),
    ],
}


# ─── Connectivity Detection ──────────────────────────────────────────────────

class ConnectivityStatus(BaseModel):
    is_online: bool
    ollama_available: bool
    latency_ms: float | None = None
    checked_at: float = 0.0


_connectivity_cache: ConnectivityStatus | None = None
_cache_ttl: float = 30.0  # seconds


def check_ollama(base_url: str = "http://localhost:11434", timeout: float = 2.0) -> bool:
    """Check if Ollama is running locally."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


def check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """Check internet connectivity via DNS socket."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def get_connectivity() -> ConnectivityStatus:
    """Get connectivity status with caching."""
    global _connectivity_cache
    now = time.monotonic()
    if _connectivity_cache and (now - _connectivity_cache.checked_at) < _cache_ttl:
        return _connectivity_cache

    t0 = time.monotonic()
    ollama_ok = check_ollama(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    is_online = check_internet()
    latency = (time.monotonic() - t0) * 1000

    status = ConnectivityStatus(
        is_online=is_online,
        ollama_available=ollama_ok,
        latency_ms=latency,
        checked_at=now,
    )
    _connectivity_cache = status
    logger.info(
        f"Connectivity: online={is_online}, ollama={ollama_ok}, latency={latency:.1f}ms"
    )
    return status


# ─── LLM Router ──────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Smart LLM Router — Physics-inspired: always find the path of least resistance
    to the most capable local model first.
    """

    def __init__(self):
        self._connectivity: ConnectivityStatus | None = None

    def route(
        self,
        task_type: TaskType = TaskType.REASONING,
        force_local: bool = False,
        temperature: float | None = None,
    ) -> BaseLanguageModel:
        """
        Route to best available model for the given task.
        Priority: Ollama local > Free cloud (only if online)
        Reads API keys from: env vars → Streamlit session state → Streamlit secrets
        """
        conn = get_connectivity()
        self._connectivity = conn

        # Always try Ollama first
        if conn.ollama_available:
            config = OLLAMA_MODELS.get(task_type, OLLAMA_MODELS[TaskType.REASONING])
            logger.info(f"[ROUTER] → Ollama/{config.model} (offline-safe)")
            return self._build_ollama(config, temperature)

        if force_local:
            raise RuntimeError(
                "CRITICAL: Ollama is not running. Start Ollama: `ollama serve`"
            )

        # Online fallback → check for any available free cloud key
        # Re-read keys at call time (may have been set in session state after startup)
        available_fallbacks = self._get_available_fallbacks(task_type)
        if available_fallbacks:
            config = available_fallbacks[0]
            logger.info(f"[ROUTER] → {config.provider}/{config.model} (free cloud fallback)")
            return self._build_openai_compat(config, temperature)

        raise RuntimeError(
            "No LLM available. Options:\n"
            "1. Start Ollama: ollama serve && ollama pull phi4\n"
            "2. Set a free API key in Settings tab (Groq/Together/Fireworks)\n"
            "3. Add GROQ_API_KEY to Streamlit Secrets (App Settings → Secrets)"
        )

    def _get_available_fallbacks(self, task_type: TaskType) -> list[LLMConfig]:
        """Get fallback configs that actually have keys available right now."""
        # Collect keys from all sources: env, streamlit session, streamlit secrets
        live_keys: dict[str, str] = {}

        # 1. Environment variables
        for k in ("GROQ_API_KEY", "TOGETHER_API_KEY", "FIREWORKS_API_KEY", "HF_TOKEN"):
            v = os.environ.get(k, "")
            if v:
                live_keys[k] = v

        # 2. Streamlit session state (set via Settings UI)
        try:
            import streamlit as st
            session_keys = st.session_state.get("runtime_keys", {})
            live_keys.update({k: v for k, v in session_keys.items() if v})
        except Exception:
            pass

        # 3. Streamlit secrets (set in cloud dashboard)
        try:
            import streamlit as st
            for k in ("GROQ_API_KEY", "TOGETHER_API_KEY", "FIREWORKS_API_KEY", "HF_TOKEN"):
                if k not in live_keys:
                    v = st.secrets.get(k, "")
                    if v:
                        live_keys[k] = v
        except Exception:
            pass

        # Map to configs
        all_fallbacks = FREE_CLOUD_MODELS.get(task_type, FREE_CLOUD_MODELS.get(TaskType.REASONING, []))
        result = []
        for cfg in all_fallbacks:
            # Find the right env key for this provider
            key_map = {
                "groq": "GROQ_API_KEY",
                "together": "TOGETHER_API_KEY",
                "fireworks": "FIREWORKS_API_KEY",
                "huggingface": "HF_TOKEN",
            }
            env_key = key_map.get(cfg.provider, "")
            key_val = live_keys.get(env_key, "")
            if key_val:
                result.append(LLMConfig(
                    provider=cfg.provider,
                    model=cfg.model,
                    base_url=cfg.base_url,
                    api_key=key_val,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                ))

        # If no task-specific fallback found, try Groq for any task
        if not result and "GROQ_API_KEY" in live_keys:
            result.append(LLMConfig(
                provider="groq",
                model="llama-3.3-70b-versatile",
                base_url="https://api.groq.com/openai/v1",
                api_key=live_keys["GROQ_API_KEY"],
            ))

        return result

    def _build_ollama(self, config: LLMConfig, temperature: float | None):
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config.model,
                base_url=config.base_url or "http://localhost:11434",
                temperature=temperature if temperature is not None else config.temperature,
                num_predict=config.max_tokens,
            )
        except ImportError:
            raise RuntimeError("langchain-ollama not installed. Run: pip install langchain-ollama")

    def _build_openai_compat(self, config: LLMConfig, temperature: float | None):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=temperature if temperature is not None else config.temperature,
            max_tokens=config.max_tokens,
        )

    @property
    def is_offline(self) -> bool:
        conn = get_connectivity()
        return not conn.is_online

    @property
    def ollama_models(self) -> list[str]:
        """List locally available Ollama models."""
        try:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{base_url}/api/tags")
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def pull_required_models(self) -> None:
        """Pull all required Ollama models if not present."""
        import shutil
        if not shutil.which("ollama"):
            raise RuntimeError(
                "ollama binary not found. Install from https://ollama.ai/install\n"
                "On Streamlit Cloud, run models locally and expose via Tailscale/ngrok."
            )
        required = [
            "llama3.3:latest",
            "qwen2.5:7b",
            "phi4:latest",
            "deepseek-coder:latest",
            "mistral:latest",
            "gemma3:latest",
        ]
        present = self.ollama_models
        for model in required:
            name = model.split(":")[0]
            if not any(name in p for p in present):
                logger.info(f"Pulling Ollama model: {model}")
                import subprocess
                subprocess.run(["ollama", "pull", model], check=False)


# ─── Singleton ───────────────────────────────────────────────────────────────

_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def get_llm(task_type: TaskType = TaskType.REASONING, **kwargs) -> BaseLanguageModel:
    """Convenience function — get best available LLM for task."""
    return get_router().route(task_type=task_type, **kwargs)
