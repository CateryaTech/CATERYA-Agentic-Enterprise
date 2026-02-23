"""
CATERYA Base Agent — All agents inherit from this.
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.core.ethics_wrapper import get_ethics_guard, EthicsVerdict
from src.core.llm_router import get_llm, TaskType
from src.core.state_manager import get_logger


@dataclass
class AgentOutput:
    agent_id: str
    task: str
    result: str
    ethics_verdict: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None


class BaseAgent(ABC):
    """
    Base class for all CATERYA agents.
    Every output automatically passes through the ethics guard.
    """

    agent_id: str = "base"
    task_type: TaskType = TaskType.REASONING
    description: str = "Base CATERYA Agent"

    def __init__(self):
        self.logger = get_logger(f"agent.{self.agent_id}")
        self._ethics = get_ethics_guard()
        self._llm = None

    @property
    def llm(self):
        # Always re-route — picks up any keys set in session state since last call
        self._llm = get_llm(self.task_type)
        return self._llm

    @abstractmethod
    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        """Execute the agent's primary task."""
        ...

    def _checked_run(self, task: str, raw_output: str, context: dict | None = None) -> AgentOutput:
        """Wrap raw output through ethics check and return AgentOutput."""
        t0 = time.monotonic()
        ethics_result = self._ethics.check(raw_output, agent_id=self.agent_id, context=context)

        if not ethics_result.is_safe:
            self.logger.warning(f"Output BLOCKED by ethics guard. Flags: {ethics_result.flags}")

        return AgentOutput(
            agent_id=self.agent_id,
            task=task,
            result=ethics_result.sanitized,
            ethics_verdict=ethics_result.verdict.value,
            duration_ms=(time.monotonic() - t0) * 1000,
            metadata={
                "flags": ethics_result.flags,
                "pillar_scores": ethics_result.pillar_scores,
                "audit_hash": ethics_result.audit_hash,
            },
            success=ethics_result.is_safe,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return string response. Graceful fallback if unavailable."""
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            if hasattr(response, "content"):
                return response.content
            return str(response)
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            # On Streamlit Cloud without Ollama, return informative message
            if "connection" in str(e).lower() or "refused" in str(e).lower():
                return (
                    "⚠️ **Ollama not available on Streamlit Cloud.**\n\n"
                    "This dashboard is a **demo/preview**. For full AI functionality:\n"
                    "- Run locally with Docker: `docker-compose up -d`\n"
                    "- Or set free API keys (GROQ_API_KEY) in Streamlit secrets\n\n"
                    f"Task received: _{prompt[:200]}_"
                )
            raise

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.agent_id}>"
