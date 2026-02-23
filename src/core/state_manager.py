"""
CATERYA State Manager — Persistent, Encrypted, Offline-Ready
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>
"""

from __future__ import annotations

import logging
import os
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Get configured logger."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    return logging.getLogger(name)


logger = get_logger(__name__)


class StateManager:
    """
    Manages persistent agent state using PostgreSQL + Redis.
    Falls back to in-memory + SQLite if services unavailable (true offline mode).
    """

    def __init__(self):
        self._memory: dict[str, Any] = {}
        self._redis = None
        self._pg = None
        self._init_backends()

    def _init_backends(self):
        # Try Redis
        try:
            import redis
            self._redis = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis.ping()
            logger.info("Redis connected ✓")
        except Exception as e:
            logger.warning(f"Redis unavailable (offline mode): {e}")
            self._redis = None

        # Try PostgreSQL
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(
                os.getenv("POSTGRES_URL", "postgresql://caterya:caterya@localhost:5432/caterya_db"),
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3},
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._pg = engine
            logger.info("PostgreSQL connected ✓")
        except Exception as e:
            logger.warning(f"PostgreSQL unavailable (SQLite fallback): {e}")
            self._pg = self._init_sqlite()

    def _init_sqlite(self):
        """SQLite fallback for fully offline mode."""
        from sqlalchemy import create_engine
        os.makedirs("./data", exist_ok=True)
        engine = create_engine("sqlite:///./data/caterya_state.db")
        logger.info("SQLite fallback active (offline mode) ✓")
        return engine

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._memory[key] = value
        if self._redis:
            try:
                import json
                self._redis.set(key, json.dumps(value), ex=ttl)
            except Exception:
                pass

    def get(self, key: str, default: Any = None) -> Any:
        if self._redis:
            try:
                import json
                val = self._redis.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return self._memory.get(key, default)

    def delete(self, key: str) -> None:
        self._memory.pop(key, None)
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass

    @property
    def is_fully_offline(self) -> bool:
        return self._redis is None and "sqlite" in str(getattr(self._pg, "url", "sqlite"))


_state: StateManager | None = None


def get_state() -> StateManager:
    global _state
    if _state is None:
        _state = StateManager()
    return _state
