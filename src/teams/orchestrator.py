"""
CATERYA Agent Teams — LangGraph Stateful Orchestration
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

Multi-agent workflows using LangGraph with:
- Persistent checkpoints
- Human-in-the-loop support
- Conditional routing
- Ethics gating at every node
"""

from __future__ import annotations

import operator
from typing import Any, Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.agents import (
    LeadGenAgent, ResearchAgent, ContentWriterAgent,
    SalesCloserAgent, EthicsGuardAgent, get_agent
)
from src.core.state_manager import get_logger

logger = get_logger(__name__)


# ─── Shared State Schema ──────────────────────────────────────────────────────

class WorkflowState(TypedDict):
    task: str
    context: dict[str, Any]
    results: Annotated[list[dict], operator.add]
    current_agent: str
    ethics_approved: bool
    final_output: str | None
    error: str | None


# ─── Sales Pipeline Team ─────────────────────────────────────────────────────

def build_sales_pipeline() -> StateGraph:
    """
    Sales Pipeline: Research → LeadGen → ContentWriter → SalesCloser → EthicsCheck
    """

    def research_node(state: WorkflowState) -> WorkflowState:
        agent = ResearchAgent()
        out = agent.run(f"Research market for: {state['task']}", state.get("context"))
        return {
            **state,
            "results": [{"agent": "Research", "output": out.result}],
            "current_agent": "research",
        }

    def leadgen_node(state: WorkflowState) -> WorkflowState:
        agent = LeadGenAgent()
        research_ctx = {
            **state.get("context", {}),
            "research": state["results"][-1]["output"] if state["results"] else "",
        }
        out = agent.run(f"Generate leads for: {state['task']}", research_ctx)
        return {
            **state,
            "results": [{"agent": "LeadGen", "output": out.result}],
            "current_agent": "leadgen",
        }

    def content_node(state: WorkflowState) -> WorkflowState:
        agent = ContentWriterAgent()
        out = agent.run(f"Write outreach content for: {state['task']}", state.get("context"))
        return {
            **state,
            "results": [{"agent": "ContentWriter", "output": out.result}],
            "current_agent": "content",
        }

    def sales_node(state: WorkflowState) -> WorkflowState:
        agent = SalesCloserAgent()
        out = agent.run(state["task"], state.get("context"))
        return {
            **state,
            "results": [{"agent": "SalesCloser", "output": out.result}],
            "current_agent": "sales",
        }

    def ethics_node(state: WorkflowState) -> WorkflowState:
        agent = EthicsGuardAgent()
        all_content = "\n\n".join([r["output"] for r in state["results"]])
        out = agent.run("Review all outputs for ethics compliance", {"content": all_content})
        approved = "REJECT" not in out.result.upper()
        return {
            **state,
            "results": [{"agent": "EthicsGuard", "output": out.result}],
            "ethics_approved": approved,
            "final_output": all_content if approved else None,
            "current_agent": "ethics",
        }

    def route_after_ethics(state: WorkflowState) -> str:
        return "end" if state["ethics_approved"] else "end_blocked"

    # Build graph
    graph = StateGraph(WorkflowState)
    graph.add_node("research", research_node)
    graph.add_node("leadgen", leadgen_node)
    graph.add_node("content", content_node)
    graph.add_node("sales", sales_node)
    graph.add_node("ethics", ethics_node)
    graph.add_node("end_blocked", lambda s: {**s, "final_output": "[BLOCKED BY ETHICS]"})

    graph.set_entry_point("research")
    graph.add_edge("research", "leadgen")
    graph.add_edge("leadgen", "content")
    graph.add_edge("content", "sales")
    graph.add_edge("sales", "ethics")
    graph.add_conditional_edges("ethics", route_after_ethics, {
        "end": END,
        "end_blocked": "end_blocked",
    })
    graph.add_edge("end_blocked", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# ─── Generic Single-Agent Runner ─────────────────────────────────────────────

def run_agent(agent_id: str, task: str, context: dict | None = None) -> dict[str, Any]:
    """Run a single agent and return structured output."""
    try:
        agent = get_agent(agent_id)
        result = agent.run(task, context)
        return {
            "success": result.success,
            "agent_id": result.agent_id,
            "result": result.result,
            "ethics_verdict": result.ethics_verdict,
            "duration_ms": result.duration_ms,
            "metadata": result.metadata,
        }
    except Exception as e:
        logger.error(f"Agent {agent_id} failed: {e}")
        return {
            "success": False,
            "agent_id": agent_id,
            "result": f"Error: {e}",
            "ethics_verdict": "error",
            "duration_ms": 0,
            "metadata": {},
        }


# ─── Sales Pipeline Runner ────────────────────────────────────────────────────

_sales_pipeline = None


def get_sales_pipeline():
    global _sales_pipeline
    if _sales_pipeline is None:
        _sales_pipeline = build_sales_pipeline()
    return _sales_pipeline


def run_sales_pipeline(task: str, context: dict | None = None) -> dict[str, Any]:
    """Run the full sales pipeline."""
    pipeline = get_sales_pipeline()
    initial_state: WorkflowState = {
        "task": task,
        "context": context or {},
        "results": [],
        "current_agent": "start",
        "ethics_approved": False,
        "final_output": None,
        "error": None,
    }
    config = {"configurable": {"thread_id": f"sales_{hash(task)}"}}
    final = pipeline.invoke(initial_state, config)
    return {
        "final_output": final.get("final_output"),
        "ethics_approved": final.get("ethics_approved"),
        "steps": final.get("results", []),
    }
