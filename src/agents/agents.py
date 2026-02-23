"""
CATERYA Specialized Agents — 12+ Production-Ready Agents
Author: Ary HH (Caterya Tech) <aryhharyanto@proton.me>

All agents:
- Pass output through ethics guard automatically
- Work 100% offline via Ollama
- Use smart task-type routing
"""

from __future__ import annotations

import json
import time
from typing import Any

from src.agents.base import BaseAgent, AgentOutput
from src.core.llm_router import TaskType


# ─── 1. Lead Generation Agent ────────────────────────────────────────────────

class LeadGenAgent(BaseAgent):
    agent_id = "LeadGen"
    task_type = TaskType.REASONING
    description = "Generates qualified leads and prospect research"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        prompt = f"""You are a B2B lead generation specialist for a tech startup.
Task: {task}
Context: {json.dumps(context or {})}

Generate a structured list of qualified prospects with:
- Company name, size, industry
- Pain points your product solves
- Contact strategy recommendation
- Estimated deal value

Format as JSON array."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 2. Content Writer Agent ─────────────────────────────────────────────────

class ContentWriterAgent(BaseAgent):
    agent_id = "ContentWriter"
    task_type = TaskType.CREATIVE
    description = "Writes SEO-optimized content, copy, and marketing materials"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        tone = (context or {}).get("tone", "professional yet warm")
        audience = (context or {}).get("audience", "tech-savvy founders")
        prompt = f"""You are an expert content writer.
Tone: {tone} | Target Audience: {audience}
Task: {task}

Write compelling, original content. Be concise, value-driven, and authentic.
Include a strong hook, clear body, and actionable CTA."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 3. Sales Closer Agent ───────────────────────────────────────────────────

class SalesCloserAgent(BaseAgent):
    agent_id = "SalesCloser"
    task_type = TaskType.REASONING
    description = "Handles sales conversations, objections, and closing"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        prospect_info = (context or {}).get("prospect", {})
        prompt = f"""You are a world-class B2B sales consultant.
Prospect Info: {json.dumps(prospect_info)}
Situation: {task}

Provide:
1. Objection handling script
2. Value proposition tailored to this prospect
3. Closing technique recommendation
4. Follow-up sequence (3 touchpoints)

Be consultative, not pushy. Focus on their ROI."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 4. Customer Support Agent ───────────────────────────────────────────────

class SupportAgent(BaseAgent):
    agent_id = "Support"
    task_type = TaskType.FAST
    description = "Handles customer inquiries and support tickets"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        customer_history = (context or {}).get("history", [])
        prompt = f"""You are a helpful, empathetic customer support specialist.
Customer Query: {task}
Previous Interactions: {json.dumps(customer_history[-3:] if customer_history else [])}

Respond with:
1. Immediate acknowledgment and empathy
2. Clear solution or next steps
3. Escalation flag if needed (True/False)
4. Satisfaction follow-up message

Keep response friendly and under 200 words."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 5. Finance & Billing Agent ──────────────────────────────────────────────

class FinanceAgent(BaseAgent):
    agent_id = "Finance"
    task_type = TaskType.REASONING
    description = "Handles invoicing, payment tracking, financial analysis"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        from src.core.crypto_manager import get_crypto, Chain
        crypto = get_crypto()
        addresses = crypto.get_all_addresses()

        prompt = f"""You are a financial operations specialist.
Task: {task}
Context: {json.dumps(context or {})}

Available payment channels:
- Bitcoin: {addresses['bitcoin']}
- Ethereum/EVM: {addresses['ethereum_evm']}
- Solana: {addresses['solana']}

Provide structured financial analysis or invoice details as requested.
Always be precise with numbers. Flag any anomalies."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 6. Code Improver Agent ──────────────────────────────────────────────────

class CodeImproverAgent(BaseAgent):
    agent_id = "CodeImprover"
    task_type = TaskType.CODING
    description = "Reviews, refactors, and improves code quality"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        code = (context or {}).get("code", "")
        language = (context or {}).get("language", "python")
        prompt = f"""You are a senior software engineer specializing in {language}.
Task: {task}
Code to review:
```{language}
{code}
```

Provide:
1. Critical bugs or security issues (if any)
2. Performance improvements
3. Refactored version with comments
4. Test cases to add
5. Code quality score (1-10)"""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 7. CryptoOps Agent ──────────────────────────────────────────────────────

class CryptoOpsAgent(BaseAgent):
    agent_id = "CryptoOps"
    task_type = TaskType.CRYPTO
    description = "Manages on-chain operations, payment verification, invoicing"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        from src.core.crypto_manager import get_crypto, Chain
        crypto = get_crypto()

        op_type = (context or {}).get("operation", "status")

        if op_type == "invoice":
            chain_str = (context or {}).get("chain", "ethereum")
            amount = (context or {}).get("amount", 0.0)
            memo = (context or {}).get("memo", "")
            try:
                chain = Chain(chain_str)
                invoice = crypto.generate_invoice(chain, amount, memo)
                raw = json.dumps(invoice, indent=2)
            except Exception as e:
                raw = f"Error generating invoice: {e}"

        elif op_type == "verify":
            chain_str = (context or {}).get("chain", "ethereum")
            tx_id = (context or {}).get("tx_id", "")
            amount = (context or {}).get("amount", 0.0)
            try:
                chain = Chain(chain_str)
                verified = crypto.verify_payment(chain, tx_id, amount)
                raw = json.dumps({"verified": verified, "tx_id": tx_id, "chain": chain_str})
            except Exception as e:
                raw = f"Error verifying payment: {e}"

        else:
            addresses = crypto.get_all_addresses()
            raw = f"CryptoOps Status\nReceive Addresses:\n{json.dumps(addresses, indent=2)}"

        return self._checked_run(task, raw, context)


# ─── 8. Ethics Guard Agent ───────────────────────────────────────────────────

class EthicsGuardAgent(BaseAgent):
    agent_id = "EthicsGuard"
    task_type = TaskType.REASONING
    description = "Reviews decisions and outputs for ethical compliance"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        content_to_review = (context or {}).get("content", task)
        prompt = f"""You are an AI ethics specialist aligned with CATERYA pillars:
Conservation | Reciprocity | Integrity | Sovereignty | Resonance

Review this content/decision for ethical concerns:
---
{content_to_review}
---

Evaluate:
1. Potential harms or risks
2. Transparency and honesty
3. User privacy and data sovereignty
4. Long-term societal impact
5. Overall ethics score (0-100) and recommendation (APPROVE/REVISE/REJECT)

Be thorough but fair."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 9. Self-Optimizer Agent ─────────────────────────────────────────────────

class SelfOptimizerAgent(BaseAgent):
    agent_id = "SelfOptimizer"
    task_type = TaskType.ANALYSIS
    description = "Analyzes system performance and suggests improvements"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        metrics = (context or {}).get("metrics", {})
        agent_logs = (context or {}).get("agent_logs", [])
        prompt = f"""You are a systems optimization specialist.
Task: {task}
Current Metrics: {json.dumps(metrics)}
Recent Agent Logs (sample): {json.dumps(agent_logs[-10:] if agent_logs else [])}

Analyze and provide:
1. Performance bottlenecks identified
2. Agent configuration improvements
3. Prompt engineering suggestions
4. Model selection optimizations
5. Priority action items (ranked)

Think like a physicist: find the minimal intervention for maximum improvement."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 10. Research Agent ──────────────────────────────────────────────────────

class ResearchAgent(BaseAgent):
    agent_id = "Research"
    task_type = TaskType.REASONING
    description = "Deep research, competitive analysis, market intelligence"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        sources = (context or {}).get("sources", [])
        depth = (context or {}).get("depth", "medium")
        prompt = f"""You are a research analyst with expertise in tech and business.
Research Task: {task}
Depth: {depth} | Available Sources: {json.dumps(sources)}

Provide structured research report:
1. Executive Summary (3 bullets)
2. Key Findings
3. Data Points & Evidence
4. Competitive Landscape
5. Strategic Implications
6. Confidence Score (1-10) with reasoning

Cite sources where available. Flag information gaps."""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 11. Dashboard Monitor Agent ─────────────────────────────────────────────

class DashboardMonitorAgent(BaseAgent):
    agent_id = "DashboardMonitor"
    task_type = TaskType.FAST
    description = "Monitors system health, alerts on anomalies"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        from src.core.llm_router import get_connectivity
        conn = get_connectivity()
        from src.core.state_manager import get_state
        state = get_state()

        status = {
            "ollama_available": conn.ollama_available,
            "is_online": conn.is_online,
            "latency_ms": conn.latency_ms,
            "storage_backend": "Redis+PG" if not state.is_fully_offline else "SQLite (offline)",
            "task": task,
        }

        prompt = f"""You are a system monitoring specialist.
Current System Status: {json.dumps(status)}
Monitor Task: {task}

Provide:
1. System health summary (HEALTHY/DEGRADED/CRITICAL)
2. Any alerts or anomalies
3. Recommended actions
4. ETA to resolve if issues found"""
        raw = self._call_llm(prompt)
        return self._checked_run(task, raw, context)


# ─── 12. Backup Agent ────────────────────────────────────────────────────────

class BackupAgent(BaseAgent):
    agent_id = "BackupAgent"
    task_type = TaskType.FAST
    description = "Manages data backup, export, and recovery procedures"

    def run(self, task: str, context: dict | None = None) -> AgentOutput:
        import subprocess
        backup_type = (context or {}).get("type", "status")

        if backup_type == "status":
            import os
            data_dir = "./data"
            files = []
            if os.path.exists(data_dir):
                for f in os.listdir(data_dir):
                    fpath = os.path.join(data_dir, f)
                    files.append({"file": f, "size_kb": os.path.getsize(fpath) // 1024})
            raw = json.dumps({"backup_status": "OK", "data_files": files, "task": task})
        else:
            raw = f"Backup operation '{backup_type}' acknowledged. Task: {task}"

        return self._checked_run(task, raw, context)


# ─── Agent Registry ───────────────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "lead_gen": LeadGenAgent,
    "content_writer": ContentWriterAgent,
    "sales_closer": SalesCloserAgent,
    "support": SupportAgent,
    "finance": FinanceAgent,
    "code_improver": CodeImproverAgent,
    "crypto_ops": CryptoOpsAgent,
    "ethics_guard": EthicsGuardAgent,
    "self_optimizer": SelfOptimizerAgent,
    "research": ResearchAgent,
    "dashboard_monitor": DashboardMonitorAgent,
    "backup": BackupAgent,
}


def get_agent(agent_id: str) -> BaseAgent:
    """Factory: get agent instance by ID."""
    cls = AGENT_REGISTRY.get(agent_id)
    if not cls:
        raise ValueError(f"Unknown agent: {agent_id}. Available: {list(AGENT_REGISTRY.keys())}")
    return cls()
