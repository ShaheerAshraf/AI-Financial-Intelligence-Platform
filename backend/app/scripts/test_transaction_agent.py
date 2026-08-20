"""
Independent smoke test for the Gemini transaction analysis agent.

Run from the backend directory:

    python -m app.scripts.test_transaction_agent
"""

from app.agents.transaction_agent import analyze_transaction


SAMPLE_EVIDENCE = """
Transaction ID: 3028
Amount: €107,199.73
Vendor: 41
Category: 22
Date: 2026-08-19

Anomaly score: -0.196859
Status: HIGH
Model version: isolation_forest_v1

Vendor historical average: €4,850.12
Vendor historical std: €1,210.45
Category historical average: €5,320.88

Amount vs vendor historical average: 22.1x
Amount vs category historical average: 20.1x

Reasons:
- Amount much higher than vendor historical average
- Amount much higher than category historical average
- Outside normal vendor historical spend variation
""".strip()


def main() -> None:
    print("Sending sample ML evidence to the transaction agent...\n")
    print(SAMPLE_EVIDENCE)
    print("\n" + "=" * 60 + "\n")

    analysis = analyze_transaction(SAMPLE_EVIDENCE)

    print("Structured AgentAnalysis:\n")
    print(analysis.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
