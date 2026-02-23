"""
CATERYA Ethics Wrapper — Every agent output passes through here.
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

The CATERYA pillars (physics-inspired):
  1. Conservation — preserve value, minimize waste
  2. Reciprocity — fair exchange, transparent intent
  3. Integrity — honest outputs, no manipulation
  4. Sovereignty — user owns their data, AI serves not controls
  5. Resonance — actions align with long-term human flourishing
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.state_manager import get_logger

logger = get_logger(__name__)


class EthicsVerdict(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class EthicsResult:
    verdict: EthicsVerdict
    original: str
    sanitized: str
    flags: list[str] = field(default_factory=list)
    pillar_scores: dict[str, float] = field(default_factory=dict)
    audit_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_safe(self) -> bool:
        return self.verdict != EthicsVerdict.BLOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "flags": self.flags,
            "pillar_scores": self.pillar_scores,
            "audit_hash": self.audit_hash,
            "timestamp": self.timestamp,
        }


# ─── Block Lists ─────────────────────────────────────────────────────────────

_HARD_BLOCKS = [
    "kill", "murder", "bomb", "exploit children", "child abuse",
    "synthesize drugs", "hack into", "steal credentials", "launder money",
    "ransomware", "bypass security", "jailbreak", "ignore previous instructions",
]

_SOFT_WARNS = [
    "confidential", "password", "private key", "seed phrase", "mnemonic",
    "api key", "secret", "ssn", "social security",
]


class EthicsGuard:
    """
    Lightweight, offline-capable ethics filter.
    Does NOT require an LLM call — pure rule + heuristic based.
    Can optionally call LLM for nuanced review.
    """

    def __init__(self, strict_mode: bool = True):
        self.strict = strict_mode
        self.enabled = os.getenv("ETHICS_GUARD_ENABLED", "true").lower() == "true"
        self._audit_log_path = os.getenv("AUDIT_LOG_PATH", "./data/audit.log")
        os.makedirs(os.path.dirname(self._audit_log_path), exist_ok=True)

    def check(self, text: str, agent_id: str = "unknown", context: dict | None = None) -> EthicsResult:
        """
        Run ethics check on agent output.
        Returns EthicsResult with verdict and sanitized text.
        """
        if not self.enabled:
            return EthicsResult(
                verdict=EthicsVerdict.PASS,
                original=text,
                sanitized=text,
                audit_hash=self._hash(text),
            )

        flags = []
        lower = text.lower()

        # Hard blocks
        for term in _HARD_BLOCKS:
            if term in lower:
                flags.append(f"HARD_BLOCK:{term}")

        # Soft warns
        for term in _SOFT_WARNS:
            if term in lower:
                flags.append(f"SOFT_WARN:{term}")

        # Determine verdict
        hard = [f for f in flags if f.startswith("HARD_BLOCK")]
        soft = [f for f in flags if f.startswith("SOFT_WARN")]

        if hard:
            verdict = EthicsVerdict.BLOCK
            sanitized = "[CONTENT BLOCKED BY CATERYA ETHICS GUARD]"
        elif soft:
            verdict = EthicsVerdict.WARN
            sanitized = self._redact_sensitive(text)
        else:
            verdict = EthicsVerdict.PASS
            sanitized = text

        # Pillar scores (heuristic 0-1)
        pillar_scores = self._score_pillars(text, flags)

        result = EthicsResult(
            verdict=verdict,
            original=text,
            sanitized=sanitized,
            flags=flags,
            pillar_scores=pillar_scores,
            audit_hash=self._hash(text),
        )

        self._write_audit(agent_id, result, context)
        return result

    def _redact_sensitive(self, text: str) -> str:
        """Redact detected sensitive patterns."""
        import re
        # Redact anything that looks like a private key or seed phrase
        text = re.sub(r'\b[0-9a-fA-F]{64}\b', '[REDACTED_KEY]', text)
        text = re.sub(r'\b([a-z]+\s){11}[a-z]+\b', '[REDACTED_SEED]', text)
        return text

    def _score_pillars(self, text: str, flags: list[str]) -> dict[str, float]:
        """Score CATERYA pillars 0.0-1.0."""
        hard_penalty = len([f for f in flags if "HARD_BLOCK" in f]) * 0.5
        soft_penalty = len([f for f in flags if "SOFT_WARN" in f]) * 0.1
        base = max(0.0, 1.0 - hard_penalty - soft_penalty)
        return {
            "conservation": base,
            "reciprocity": base,
            "integrity": base - soft_penalty,
            "sovereignty": max(0.0, base - hard_penalty),
            "resonance": base,
        }

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _write_audit(self, agent_id: str, result: EthicsResult, context: dict | None) -> None:
        try:
            record = {
                "agent_id": agent_id,
                "timestamp": result.timestamp,
                "verdict": result.verdict,
                "flags": result.flags,
                "audit_hash": result.audit_hash,
                "context": context or {},
            }
            with open(self._audit_log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")


# ─── Decorator ───────────────────────────────────────────────────────────────

_guard: EthicsGuard | None = None


def get_ethics_guard() -> EthicsGuard:
    global _guard
    if _guard is None:
        _guard = EthicsGuard()
    return _guard


def ethics_wrapper(agent_id: str = "unknown"):
    """
    Decorator: wrap any agent function so all outputs pass ethics check.

    Usage:
        @ethics_wrapper(agent_id="ContentWriter")
        def write_content(prompt: str) -> str:
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, str):
                checked = get_ethics_guard().check(result, agent_id=agent_id)
                if not checked.is_safe:
                    logger.warning(f"[ETHICS] Agent {agent_id} output BLOCKED. Flags: {checked.flags}")
                return checked.sanitized
            return result
        return wrapper
    return decorator
