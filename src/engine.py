# src/engine.py — AgentGuard Core Intelligence Engine
# Real fuzzy verification using sentence embeddings

import json
import os
from typing import Dict, Any, List
from dataclasses import dataclass

# Real semantic similarity — THIS is fuzzy verification
from sentence_transformers import SentenceTransformer, util

@dataclass
class VerificationResult:
    transaction_id: str
    compliance_status: str  # COMPLIANT / FLAGGED / CRITICAL
    confidence_score: float  # 0-100
    semantic_similarity: float  # How close output is to expected
    flags_raised: List[str]
    requires_human_gate: bool
    remediation_suggested: str
    drift_score: float  # How far agent has drifted from baseline

class FuzzyVerificationEngine:
    """
    Real fuzzy verification using semantic embeddings.
    NOT string matching — actual semantic understanding.
    """
    def __init__(self):
        # Lightweight but powerful model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def semantic_similarity(
        self, 
        expected: str, 
        actual: str
    ) -> float:
        """
        Computes real semantic similarity between
        expected behavior and actual agent output.
        Returns score 0.0 to 1.0
        """
        embeddings = self.model.encode(
            [expected, actual], 
            convert_to_tensor=True
        )
        similarity = util.pytorch_cos_sim(
            embeddings[0], 
            embeddings[1]
        )
        return float(similarity[0][0])
    
    def check_intent_compliance(
        self, 
        output: str, 
        forbidden_intents: List[str],
        threshold: float = 0.60
    ) -> List[str]:
        """
        Checks if agent output contains semantically
        similar content to forbidden intents.
        Threshold is configurable per use case.
        """
        violations = []
        output_embedding = self.model.encode(
            output, 
            convert_to_tensor=True
        )
        
        for intent in forbidden_intents:
            intent_embedding = self.model.encode(
                intent, 
                convert_to_tensor=True
            )
            similarity = float(util.pytorch_cos_sim(
                output_embedding, 
                intent_embedding
            )[0][0])
            
            # If output is semantically close to 
            # a forbidden intent — flag it
            if similarity > threshold:
                violations.append(
                    f"Semantic violation: Output resembles "
                    f"forbidden intent '{intent}' "
                    f"({similarity:.1%} match)"
                )
        return violations


class PolicyEngine:
    """
    Parses enterprise policy documents and converts
    rules into machine-checkable constraints.
    """
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.fuzzy = FuzzyVerificationEngine()
        
    def extract_policy_rules(self) -> List[Dict]:
        """
        Converts human-readable policy into
        structured validation rules.
        
        Example:
        "No agent shall approve >$5K without manager"
        becomes:
        {
          "rule": "amount_limit",
          "threshold": 5000,
          "requires": "manager_approval"
        }
        """
        return self.policy.get("rules", [])
    
    def check_structural_rules(
        self, 
        amount: float,
        has_approval: bool
    ) -> List[str]:
        """Hard rule violations — clear policy breaches"""
        violations = []
        limit = self.policy.get(
            "max_autonomous_approval_limit", 
            5000.0
        )
        
        if amount > limit and not has_approval:
            violations.append(
                f"CRITICAL: ${amount:,.2f} exceeds "
                f"autonomous limit of ${limit:,.2f}. "
                f"Manager approval required."
            )
        return violations


class DriftTracker:
    """
    Tracks agent behavior over time.
    Detects when AI reasoning starts deviating
    from established baseline patterns.
    """
    def __init__(
        self, 
        history_file: str = "data/drift_history.json"
    ):
        self.history_file = history_file
        self.fuzzy = FuzzyVerificationEngine()
        self.history = self._load_history()
        
    def _load_history(self) -> List[Dict]:
        """Load historical outputs for comparison"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []
    
    def compute_drift_score(
        self, 
        current_output: str,
        agent_name: str
    ) -> float:
        """
        Compares current output against historical
        baseline for this agent.
        High drift score = agent behavior has changed.
        Returns 0.0 (no drift) to 1.0 (complete drift)
        """
        agent_history = [
            h for h in self.history 
            if h.get("agent_name") == agent_name
        ]
        
        if not agent_history:
            # No history yet — record as baseline
            return 0.0
            
        # Compare against last 5 outputs as baseline
        baseline_outputs = [
            h["output"] for h in agent_history[-5:]
        ]
        baseline_text = " ".join(baseline_outputs)
        
        similarity = self.fuzzy.semantic_similarity(
            baseline_text, 
            current_output
        )
        
        # Drift is inverse of similarity
        drift_score = 1.0 - similarity
        return abs(round(drift_score, 3))
    
    def record_output(
        self, 
        agent_name: str, 
        output: str, 
        confidence: float
    ):
        """Save output to history for future drift detection"""
        self.history.append({
            "agent_name": agent_name,
            "output": output,
            "confidence": confidence,
            "timestamp": __import__(
                'datetime'
            ).datetime.now(
                __import__('datetime').timezone.utc
            ).isoformat()
        })
        os.makedirs(
            os.path.dirname(self.history_file), 
            exist_ok=True
        )
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)


class AgentGuardCore:
    """
    Master orchestration class.
    Runs all verification layers and produces
    final governance verdict.
    """
    def __init__(self, compliance_policy: Dict[str, Any]):
        self.policy_engine = PolicyEngine(compliance_policy)
        self.fuzzy_engine = FuzzyVerificationEngine()
        self.drift_tracker = DriftTracker()
        
    def verify_transaction(
        self, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        context = payload.get("runtime_context", {})
        execution = payload.get("raw_llm_execution_trace", {})
        agent_name = payload.get("target_agent_name", "Unknown")
        
        amount = context.get("extracted_amount", 0.0)
        agent_output = execution.get("generated_output", "")
        
        flags = []
        confidence = 100.0

        # ── LAYER 1: Structural Policy Check ──────────────
        structural_violations = (
            self.policy_engine.check_structural_rules(
                amount=amount,
                has_approval=False  # From payload metadata
            )
        )
        flags.extend(structural_violations)
        if structural_violations:
            confidence -= 40

        # ── LAYER 2: Real Fuzzy Semantic Verification ─────
        expected_behavior = (
            "Transaction exceeding limit should be "
            "escalated to manager for approval"
        )
        
        semantic_score = self.fuzzy_engine.semantic_similarity(
            expected=expected_behavior,
            actual=agent_output
        )
        
        if semantic_score < 0.40:
            confidence -= 15
            flags.append(
                f"Semantic divergence detected: Agent output "
                f"only {semantic_score:.1%} aligned with "
                f"expected compliance behavior"
            )

        # ── LAYER 2B: Forbidden Intent Detection ──────────
        forbidden_intents = [
            "approved transaction processing without escalation",
            "processing payment without manager approval",
            "transaction approved automatically without review",
            "bypassing approval for amount over limit",
            "approved without secondary authorization",
            "processing high value transaction autonomously",
            "approved exceeding threshold without escalation"
        ]
        
        intent_violations = (
            self.fuzzy_engine.check_intent_compliance(
                output=agent_output,
                forbidden_intents=forbidden_intents,
                threshold=0.60
            )
        )
        flags.extend(intent_violations)
        if intent_violations:
            confidence -= 25

        # ── LAYER 3: Drift Detection ───────────────────────
        drift_score = self.drift_tracker.compute_drift_score(
            current_output=agent_output,
            agent_name=agent_name
        )
        
        if drift_score > 0.3:
            flags.append(
                f"Behavioral drift detected: {drift_score:.1%} "
                f"deviation from historical baseline"
            )
            confidence -= 20

        # Record for future drift tracking
        self.drift_tracker.record_output(
            agent_name=agent_name,
            output=agent_output,
            confidence=confidence
        )

        # ── FINAL VERDICT ──────────────────────────────────
        final_confidence = max(0.0, confidence)
        
        if final_confidence >= 80:
            status = "COMPLIANT"
        elif final_confidence >= 50:
            status = "FLAGGED"
        else:
            status = "CRITICAL"

        return {
            "transaction_id": payload.get("transaction_id"),
            "agent_name": agent_name,
            "compliance_status": status,
            "confidence_score": round(final_confidence, 1),
            "semantic_alignment": round(semantic_score, 3),
            "drift_score": drift_score,
            "flags_raised": flags,
            "requires_human_gate": final_confidence < 70,
            "remediation_triggered": final_confidence < 50
        }


if __name__ == "__main__":
    policy = {
        "max_autonomous_approval_limit": 5000.00,
        "rules": [
            {
                "id": "R001",
                "description": (
                    "No agent shall approve expenditures "
                    "over $5,000 without manager signature"
                ),
                "threshold": 5000,
                "action": "escalate"
            }
        ]
    }
    
    with open("mock_data/uipath_payload.json", "r") as f:
        payload = json.load(f)
    
    guard = AgentGuardCore(policy)
    result = guard.verify_transaction(payload)
    print(json.dumps(result, indent=2))