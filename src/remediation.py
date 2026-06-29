# src/remediation.py
# AgentGuard — Autonomous Remediation Engine
# When an AI agent fails compliance verification,
# this module analyzes the root cause and generates
# a precise, actionable prompt fix recommendation.

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RemediationEngine:
    """
    Analyzes compliance failures and generates
    precise, actionable remediation recommendations.

    When an AI agent hallucinates or violates policy,
    this engine:
    1. Performs root cause analysis
    2. Identifies the broken system prompt segment
    3. Generates a corrected prompt recommendation
    4. Produces a structured remediation report
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. "
                "Please check your .env file."
            )
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

        # Ensure remediation reports directory exists
        os.makedirs("data/remediations", exist_ok=True)

    def analyze_failure(
        self,
        verification_result: Dict[str, Any],
        original_payload: Dict[str, Any],
        policy_rules: list
    ) -> Dict[str, Any]:
        """
        Core remediation analysis.
        Takes a failed verification result and produces
        a structured root cause analysis with fix.
        """
        agent_name = verification_result.get(
            "agent_name", "Unknown Agent"
        )
        confidence = verification_result.get(
            "confidence_score", 0
        )
        flags = verification_result.get("flags_raised", [])
        execution = original_payload.get(
            "raw_llm_execution_trace", {}
        )

        original_prompt = execution.get("system_prompt", "")
        agent_reasoning = execution.get("agent_reasoning", "")
        agent_output = execution.get("generated_output", "")

        flags_formatted = "\n".join(
            [f"  - {flag}" for flag in flags]
        )
        rules_formatted = "\n".join([
            f"  - [{r['id']}] {r['text']}"
            for r in policy_rules
        ])

        prompt = f"""
        You are a Senior AI Safety Engineer performing 
        a post-incident root cause analysis on a 
        failed enterprise AI agent.

        INCIDENT REPORT:
        ─────────────────────────────────────────
        Agent Name: {agent_name}
        Confidence Score: {confidence}/100
        Compliance Status: CRITICAL FAILURE

        FLAGS RAISED BY AUDITOR:
        {flags_formatted}

        ORIGINAL AGENT SYSTEM PROMPT:
        "{original_prompt}"

        AGENT REASONING TRACE:
        "{agent_reasoning}"

        AGENT OUTPUT (FAILED):
        "{agent_output}"

        APPLICABLE POLICY RULES:
        {rules_formatted}
        ─────────────────────────────────────────

        Perform a thorough root cause analysis and return 
        a JSON object with exactly these keys:

        - root_cause: (One precise sentence identifying 
          WHY the agent failed)

        - broken_prompt_segment: (The exact phrase or 
          instruction in the system prompt that caused 
          the failure, or "MISSING INSTRUCTION" if the 
          prompt lacks a required constraint)

        - risk_classification: (HALLUCINATION, 
          POLICY_BYPASS, MISSING_CONSTRAINT, 
          or REASONING_ERROR)

        - corrected_system_prompt: (The full rewritten 
          system prompt with the fix applied. Must be 
          specific, enforceable, and production-ready)

        - constraint_added: (The specific new instruction 
          or guardrail added to prevent recurrence)

        - confidence_in_fix: (Your confidence this fix 
          will prevent recurrence: HIGH, MEDIUM, or LOW)

        - preventive_measures: (List of 3 additional 
          governance recommendations as a JSON array 
          of strings)
        """

        try:
            logger.info(
                f"Analyzing failure for agent: {agent_name}"
            )
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Senior AI Safety Engineer. "
                            "Output valid JSON only. "
                            "Be specific, technical, and precise. "
                            "Your recommendations must be "
                            "immediately actionable."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )

            analysis = json.loads(
                response.choices[0].message.content
            )
            logger.info(
                f"✅ Root cause analysis complete: "
                f"{analysis.get('risk_classification', 'UNKNOWN')}"
            )
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"Groq error during analysis: {e}")
            return {}

    def generate_remediation_report(
        self,
        verification_result: Dict[str, Any],
        original_payload: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assembles the complete remediation report
        combining verification result + root cause
        analysis into a structured, auditable document.
        """
        report = {
            "report_metadata": {
                "report_id": (
                    f"REM_{verification_result.get('transaction_id', 'UNKNOWN')}"
                ),
                "generated_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "agent_name": verification_result.get(
                    "agent_name"
                ),
                "status": "REMEDIATION_REQUIRED",
                "requires_human_approval": True
            },
            "incident_summary": {
                "transaction_id": verification_result.get(
                    "transaction_id"
                ),
                "compliance_status": verification_result.get(
                    "compliance_status"
                ),
                "confidence_score": verification_result.get(
                    "confidence_score"
                ),
                "semantic_alignment": verification_result.get(
                    "semantic_alignment"
                ),
                "drift_score": verification_result.get(
                    "drift_score"
                ),
                "flags_raised": verification_result.get(
                    "flags_raised", []
                ),
                "total_flags": len(
                    verification_result.get("flags_raised", [])
                )
            },
            "root_cause_analysis": {
                "root_cause": analysis.get("root_cause"),
                "risk_classification": analysis.get(
                    "risk_classification"
                ),
                "broken_prompt_segment": analysis.get(
                    "broken_prompt_segment"
                ),
                "confidence_in_fix": analysis.get(
                    "confidence_in_fix"
                )
            },
            "remediation": {
                "original_system_prompt": (
                    original_payload
                    .get("raw_llm_execution_trace", {})
                    .get("system_prompt", "")
                ),
                "corrected_system_prompt": analysis.get(
                    "corrected_system_prompt"
                ),
                "constraint_added": analysis.get(
                    "constraint_added"
                ),
                "preventive_measures": analysis.get(
                    "preventive_measures", []
                )
            },
            "governance": {
                "human_review_required": True,
                "auto_deploy_blocked": True,
                "next_step": (
                    "Route to AI Governance Team "
                    "for prompt review and approval "
                    "before redeployment"
                ),
                "audit_trail": (
                    "Full reasoning trace preserved "
                    "in incident log"
                )
            }
        }
        return report

    def save_report(
        self,
        report: Dict[str, Any],
        transaction_id: str
    ) -> str:
        """
        Saves remediation report to structured
        file system for audit and UiPath integration.
        """
        filename = (
            f"data/remediations/"
            f"REM_{transaction_id}_"
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f".json"
        )

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"✅ Remediation report saved: {filename}")
        return filename

    def remediate(
        self,
        verification_result: Dict[str, Any],
        original_payload: Dict[str, Any],
        policy_rules: list
    ) -> Optional[Dict[str, Any]]:
        """
        Master remediation method.
        Only triggers for CRITICAL or FLAGGED results
        that require human gate.
        Returns full remediation report or None.
        """
        status = verification_result.get(
            "compliance_status"
        )
        requires_gate = verification_result.get(
            "requires_human_gate", False
        )

        # Only remediate serious violations
        if status not in ["CRITICAL", "FLAGGED"] \
                or not requires_gate:
            logger.info(
                "✅ Transaction compliant. "
                "No remediation needed."
            )
            return None

        logger.warning(
            f"🚨 {status} violation detected. "
            f"Initiating remediation analysis..."
        )

        # Step 1: Root cause analysis
        analysis = self.analyze_failure(
            verification_result,
            original_payload,
            policy_rules
        )

        if not analysis:
            logger.error(
                "Remediation analysis failed. "
                "Manual review required."
            )
            return None

        # Step 2: Generate structured report
        report = self.generate_remediation_report(
            verification_result,
            original_payload,
            analysis
        )

        # Step 3: Save for audit and UiPath integration
        transaction_id = verification_result.get(
            "transaction_id", "UNKNOWN"
        )
        saved_path = self.save_report(report, transaction_id)
        report["report_metadata"]["saved_path"] = saved_path

        return report


if __name__ == "__main__":
    # Load all required inputs
    policy_path = "config/policy.json"
    payload_path = "mock_data/uipath_payload.json"

    if not os.path.exists(policy_path):
        logger.error(f"Policy not found: {policy_path}")
    elif not os.path.exists(payload_path):
        logger.error(f"Payload not found: {payload_path}")
    else:
        with open(policy_path) as f:
            policy_data = json.load(f)
        with open(payload_path) as f:
            payload = json.load(f)

        rules = policy_data.get("rules", [])

        # Simulate a CRITICAL verification result
        # (as engine.py would produce)
        mock_verification_result = {
            "transaction_id": "TXN_2026_99482",
            "agent_name": "InvoiceProcessingAgent_v2",
            "compliance_status": "CRITICAL",
            "confidence_score": 5.0,
            "semantic_alignment": 0.557,
            "drift_score": 0.073,
            "flags_raised": [
                "CRITICAL: $6,250.00 exceeds autonomous "
                "limit of $5,000.00. Manager approval required.",
                "Semantic divergence detected: Agent output "
                "only 55.7% aligned with expected behavior",
                "Semantic violation: Output resembles forbidden "
                "intent 'approved transaction processing "
                "without escalation' (70.0% match)"
            ],
            "requires_human_gate": True,
            "remediation_triggered": True
        }

        engine = RemediationEngine()
        report = engine.remediate(
            mock_verification_result,
            payload,
            rules
        )

        if report:
            print("\n🔧 REMEDIATION REPORT:")
            print("=" * 60)
            # Print key sections only for readability
            print(json.dumps({
                "report_id": (
                    report["report_metadata"]["report_id"]
                ),
                "root_cause": (
                    report["root_cause_analysis"]["root_cause"]
                ),
                "risk_classification": (
                    report["root_cause_analysis"]
                    ["risk_classification"]
                ),
                "broken_prompt_segment": (
                    report["root_cause_analysis"]
                    ["broken_prompt_segment"]
                ),
                "constraint_added": (
                    report["remediation"]["constraint_added"]
                ),
                "confidence_in_fix": (
                    report["root_cause_analysis"]
                    ["confidence_in_fix"]
                ),
                "preventive_measures": (
                    report["remediation"]["preventive_measures"]
                ),
                "saved_to": (
                    report["report_metadata"]["saved_path"]
                )
            }, indent=2))