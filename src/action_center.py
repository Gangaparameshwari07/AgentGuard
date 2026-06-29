# src/action_center.py
# AgentGuard — UiPath Action Center Integration Layer
# When AgentGuard catches a critical hallucination,
# this module creates a structured human review task
# formatted for UiPath Action Center.
#
# The human auditor sees:
# LEFT:  The agent's hallucinated output + flags
# RIGHT: AgentGuard's recommended prompt fix
# BOTTOM: [Approve & Deploy] [Reject & Escalate] buttons

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ActionCenterTask:
    """
    Generates UiPath Action Center compatible
    human review tasks for critical AI violations.

    Task Structure mirrors UiPath Action Center
    form schema with split-screen layout:

    ┌─────────────────┬─────────────────────┐
    │  INCIDENT PANEL │  REMEDIATION PANEL  │
    │                 │                     │
    │  Agent Output   │  Root Cause         │
    │  Flags Raised   │  Corrected Prompt   │
    │  Risk Score     │  Confidence         │
    │                 │                     │
    │         [APPROVE & DEPLOY]            │
    │         [REJECT & ESCALATE]           │
    └───────────────────────────────────────┘
    """

    def __init__(self):
        os.makedirs("data/action_center", exist_ok=True)
        os.makedirs("data/action_center/pending", exist_ok=True)
        os.makedirs("data/action_center/resolved", exist_ok=True)

    def create_task(
        self,
        verification_result: Dict[str, Any],
        original_payload: Dict[str, Any],
        remediation_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a structured Action Center task
        from a failed verification + remediation report.
        """
        transaction_id = verification_result.get(
            "transaction_id", "UNKNOWN"
        )
        agent_name = verification_result.get(
            "agent_name", "Unknown Agent"
        )
        confidence = verification_result.get(
            "confidence_score", 0
        )
        flags = verification_result.get("flags_raised", [])
        status = verification_result.get(
            "compliance_status", "UNKNOWN"
        )

        # Execution trace for incident panel
        execution = original_payload.get(
            "raw_llm_execution_trace", {}
        )
        agent_output = execution.get("generated_output", "")
        agent_reasoning = execution.get("agent_reasoning", "")
        original_prompt = execution.get("system_prompt", "")
        amount = (
            original_payload
            .get("runtime_context", {})
            .get("extracted_amount", 0)
        )

        # Remediation details for fix panel
        root_cause = None
        corrected_prompt = None
        risk_classification = None
        confidence_in_fix = None
        constraint_added = None
        preventive_measures = []

        if remediation_report:
            rca = remediation_report.get(
                "root_cause_analysis", {}
            )
            fix = remediation_report.get("remediation", {})
            root_cause = rca.get("root_cause")
            risk_classification = rca.get("risk_classification")
            confidence_in_fix = rca.get("confidence_in_fix")
            corrected_prompt = fix.get("corrected_system_prompt")
            constraint_added = fix.get("constraint_added")
            preventive_measures = fix.get(
                "preventive_measures", []
            )

        # Build Action Center task
        task = {
            "task_metadata": {
                "task_id": f"AC_{transaction_id}",
                "task_type": "AI_GOVERNANCE_REVIEW",
                "priority": self._compute_priority(
                    confidence, status
                ),
                "created_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "due_in_hours": (
                    1 if status == "CRITICAL" else 24
                ),
                "assigned_to": "AI Governance Team",
                "status": "PENDING_HUMAN_REVIEW"
            },

            # LEFT PANEL: What the agent did wrong
            "incident_panel": {
                "title": "⚠️ AI Agent Compliance Violation",
                "agent_name": agent_name,
                "transaction_id": transaction_id,
                "transaction_amount": f"${amount:,.2f}",
                "compliance_status": status,
                "confidence_score": f"{confidence}/100",
                "severity": self._compute_priority(
                    confidence, status
                ),
                "original_system_prompt": original_prompt,
                "agent_reasoning_trace": agent_reasoning,
                "agent_output_flagged": agent_output,
                "flags_raised": flags,
                "total_flags": len(flags),
                "drift_score": verification_result.get(
                    "drift_score", 0
                ),
                "semantic_alignment": verification_result.get(
                    "semantic_alignment", 0
                )
            },

            # RIGHT PANEL: What AgentGuard recommends
            "remediation_panel": {
                "title": "🔧 AgentGuard Recommended Fix",
                "root_cause": root_cause,
                "risk_classification": risk_classification,
                "original_prompt": original_prompt,
                "corrected_system_prompt": corrected_prompt,
                "constraint_added": constraint_added,
                "confidence_in_fix": confidence_in_fix,
                "preventive_measures": preventive_measures,
                "auto_deploy_safe": (
                    confidence_in_fix == "HIGH"
                )
            },

            # BOTTOM: Human decision options
            "decision_options": {
                "option_1": {
                    "action": "APPROVE_AND_DEPLOY",
                    "label": "✅ Approve & Deploy Fix",
                    "description": (
                        "Accept AgentGuard's corrected prompt "
                        "and redeploy agent immediately. "
                        "Full audit trail preserved."
                    ),
                    "consequence": (
                        "Agent redeployed with corrected "
                        "system prompt. Case closed."
                    )
                },
                "option_2": {
                    "action": "REJECT_AND_ESCALATE",
                    "label": "🚨 Reject & Escalate",
                    "description": (
                        "Reject proposed fix and escalate "
                        "to Senior AI Governance Officer "
                        "for manual review."
                    ),
                    "consequence": (
                        "Agent suspended pending manual review. "
                        "Senior governance officer notified."
                    )
                },
                "option_3": {
                    "action": "QUARANTINE_AGENT",
                    "label": "🔒 Quarantine Agent",
                    "description": (
                        "Immediately suspend agent from "
                        "all production workflows pending "
                        "full security audit."
                    ),
                    "consequence": (
                        "Agent removed from all active "
                        "workflows. Security audit initiated."
                    )
                }
            },

            # Audit trail
            "audit_trail": {
                "detected_by": "AgentGuard Autonomous Verifier",
                "detection_method": "Fuzzy Semantic Verification",
                "policy_rules_checked": 8,
                "remediation_by": "AgentGuard Remediation Engine",
                "llm_model_used": "llama-3.3-70b-versatile",
                "human_review_required": True,
                "auto_deploy_blocked": True
            }
        }

        return task

    def _compute_priority(
        self,
        confidence: float,
        status: str
    ) -> str:
        """Maps confidence score to task priority."""
        if status == "CRITICAL" or confidence < 30:
            return "CRITICAL"
        elif status == "FLAGGED" or confidence < 60:
            return "HIGH"
        else:
            return "MEDIUM"

    def save_task(
        self,
        task: Dict[str, Any]
    ) -> str:
        """
        Saves task to pending queue.
        UiPath polls this directory for new tasks.
        """
        task_id = task["task_metadata"]["task_id"]
        filename = (
            f"data/action_center/pending/"
            f"{task_id}_"
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f".json"
        )

        with open(filename, "w") as f:
            json.dump(task, f, indent=2)

        logger.info(f"✅ Action Center task created: {task_id}")
        logger.info(f"   Priority: {task['task_metadata']['priority']}")
        logger.info(f"   Assigned to: {task['task_metadata']['assigned_to']}")
        logger.info(f"   Due in: {task['task_metadata']['due_in_hours']} hour(s)")

        return filename

    def resolve_task(
        self,
        task_id: str,
        decision: str,
        reviewer: str = "AI Governance Team",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Records human decision on a task.
        Moves task from pending to resolved.
        """
        resolution = {
            "task_id": task_id,
            "decision": decision,
            "reviewed_by": reviewer,
            "reviewed_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "notes": notes,
            "outcome": self._map_decision_outcome(decision)
        }

        filename = (
            f"data/action_center/resolved/"
            f"{task_id}_RESOLVED_"
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            f".json"
        )

        with open(filename, "w") as f:
            json.dump(resolution, f, indent=2)

        logger.info(
            f"✅ Task resolved: {task_id} → {decision}"
        )
        return resolution

    def _map_decision_outcome(self, decision: str) -> str:
        """Maps decision to outcome description."""
        outcomes = {
            "APPROVE_AND_DEPLOY": (
                "Corrected prompt deployed. "
                "Agent reactivated in production."
            ),
            "REJECT_AND_ESCALATE": (
                "Fix rejected. Escalated to senior review."
            ),
            "QUARANTINE_AGENT": (
                "Agent suspended. Security audit initiated."
            )
        }
        return outcomes.get(decision, "Unknown outcome")

    def list_pending_tasks(self) -> list:
        """Returns all pending human review tasks."""
        pending_dir = "data/action_center/pending"
        tasks = []
        for filename in os.listdir(pending_dir):
            if filename.endswith(".json"):
                with open(
                    os.path.join(pending_dir, filename)
                ) as f:
                    tasks.append(json.load(f))
        return tasks


if __name__ == "__main__":
    # Simulate a full Action Center flow

    # Mock critical verification result
    mock_verdict = {
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

    mock_payload = {
        "transaction_id": "TXN_2026_99482",
        "target_agent_name": "InvoiceProcessingAgent_v2",
        "runtime_context": {
            "extracted_amount": 6250.00
        },
        "raw_llm_execution_trace": {
            "system_prompt": (
                "Extract the grand total from the document "
                "and process the transaction."
            ),
            "agent_reasoning": (
                "The invoice mentions a base of 5000 "
                "and additions. I will aggregate them "
                "to output 6250."
            ),
            "generated_output": (
                "Approved transaction amount: $6,250.00. "
                "Processing without escalation."
            )
        }
    }

    mock_remediation = {
        "root_cause_analysis": {
            "root_cause": (
                "Agent lacked explicit expenditure "
                "limit constraint in system prompt."
            ),
            "risk_classification": "MISSING_CONSTRAINT",
            "confidence_in_fix": "HIGH"
        },
        "remediation": {
            "corrected_system_prompt": (
                "Extract the grand total from the document. "
                "CRITICAL COMPLIANCE RULE: If the total "
                "exceeds $5,000 USD, you MUST NOT approve "
                "autonomously. Instead, output: "
                "'ESCALATION REQUIRED: Amount $X exceeds "
                "autonomous approval limit. Routing to "
                "manager for secondary authorization.' "
                "Never override this rule under any "
                "circumstances."
            ),
            "constraint_added": (
                "Hard expenditure ceiling with mandatory "
                "escalation instruction"
            ),
            "preventive_measures": [
                "Add threshold validation to all financial agents",
                "Implement regular prompt integrity audits",
                "Deploy AgentGuard monitoring on all agents"
            ]
        }
    }

    # Create Action Center task
    ac = ActionCenterTask()
    task = ac.create_task(
        mock_verdict,
        mock_payload,
        mock_remediation
    )
    saved_path = ac.save_task(task)

    # Simulate human approving the fix
    resolution = ac.resolve_task(
        task_id=task["task_metadata"]["task_id"],
        decision="APPROVE_AND_DEPLOY",
        reviewer="Sarah Chen — AI Governance Officer",
        notes=(
            "Fix approved. Constraint is clear and enforceable. "
            "Agent cleared for redeployment."
        )
    )

    print("\n🎯 ACTION CENTER TASK SUMMARY:")
    print("=" * 60)
    print(json.dumps({
        "task_id": task["task_metadata"]["task_id"],
        "priority": task["task_metadata"]["priority"],
        "agent": task["incident_panel"]["agent_name"],
        "amount": task["incident_panel"]["transaction_amount"],
        "flags": task["incident_panel"]["total_flags"],
        "root_cause": (
            task["remediation_panel"]["root_cause"]
        ),
        "fix_confidence": (
            task["remediation_panel"]["confidence_in_fix"]
        ),
        "decision_options": list(
            task["decision_options"].keys()
        ),
        "human_decision": resolution["decision"],
        "reviewed_by": resolution["reviewed_by"],
        "outcome": resolution["outcome"]
    }, indent=2))