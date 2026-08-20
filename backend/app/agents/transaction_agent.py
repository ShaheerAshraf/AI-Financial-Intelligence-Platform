from app.agents.base import generate_structured
from app.schemas.agent import AgentAnalysis

AGENT_VERSION = "transaction_agent_v1"

SYSTEM_INSTRUCTIONS = """
You are a financial transaction analysis agent.

Analyze only the evidence provided to you.

Do not invent vendor information, invoices, financial history, or business context.

Explain why the transaction is suspicious based solely on the supplied evidence.

Return a structured risk assessment with:
- risk_level: HIGH, MEDIUM, or LOW
- summary: short overview of the risk
- findings: bullet-style analytical conclusions derived from the evidence
- evidence: key facts taken from the provided input (do not invent facts)
- recommendation: concrete next review step

If the evidence is insufficient, explicitly say so in the summary and recommendation,
and keep findings/evidence limited to what was actually provided.
""".strip()


def analyze_transaction(evidence: str) -> AgentAnalysis:
    """
    Agent 1 — analyze ML anomaly evidence for a single transaction.
    """
    return generate_structured(
        system_instruction=SYSTEM_INSTRUCTIONS,
        user_content=evidence,
        response_model=AgentAnalysis,
    )
