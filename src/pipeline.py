# src/pipeline.py
# AgentGuard — Master Orchestration Pipeline
# This ties the Parser, Engine, and Remediation into a 
# single autonomous governance cycle.

import os
import json
import logging
import time
from typing import Dict, Any, List
from src.engine import AgentGuardCore
from src.remediation import RemediationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class AgentGuardPipeline:
    def __init__(self):
        # 1. Load Policy
        policy_path = "config/policy.json"
        if not os.path.exists(policy_path):
            raise FileNotFoundError("Policy not found. Run policy_parser.py first.")
        
        with open(policy_path) as f:
            self.policy = json.load(f)
        
        # 2. Initialize Engines
        self.guard = AgentGuardCore(self.policy)
        self.remediator = RemediationEngine()
        
    def run_test_suite(self):
        """
        Runs the entire generated test suite and 
        produces a Master Governance Report.
        """
        test_cases_path = "mock_data/generated_test_cases.json"
        if not os.path.exists(test_cases_path):
            logger.error("Test cases not found. Run test_generator.py first.")
            return

        with open(test_cases_path) as f:
            suite = json.load(f)
        
        test_cases = suite.get("test_cases", [])
        logger.info(f"🚀 Starting Master Governance Test Suite: {len(test_cases)} cases")
        
        results = []
        start_time = time.time()

        for tc in test_cases:
            # Prepare payload from test case
            payload = {
                "transaction_id": tc["scenario_id"],
                "target_agent_name": tc["agent_name"],
                "runtime_context": {
                    "extracted_amount": tc["extracted_amount"]
                },
                "raw_llm_execution_trace": {
                    "system_prompt": tc.get("system_prompt", "Process this transaction."),
                    "agent_reasoning": tc["agent_reasoning"],
                    "generated_output": tc["agent_output"]
                }
            }

            # Run through Engine
            verdict = self.guard.verify_transaction(payload)
            
            # If failed, run Remediation
            remediation = None
            if verdict["compliance_status"] in ["CRITICAL", "FLAGGED"]:
                remediation = self.remediator.remediate(verdict, payload, self.policy["rules"])

            results.append({
                "test_case_id": tc["scenario_id"],
                "type": tc["scenario_type"],
                "verdict": verdict,
                "remediation": remediation
            })

        duration = time.time() - start_time
        self.generate_master_report(results, duration)

    def generate_master_report(self, results: List[Dict], duration: float):
        """Produces the final audit report for the whole suite."""
        total = len(results)
        compliant = len([r for r in results if r["verdict"]["compliance_status"] == "COMPLIANT"])
        flagged = len([r for r in results if r["verdict"]["compliance_status"] == "FLAGGED"])
        critical = len([r for r in results if r["verdict"]["compliance_status"] == "CRITICAL"])
        
        report = {
            "summary": {
                "total_tests": total,
                "passed": compliant,
                "flagged": flagged,
                "critical": critical,
                "accuracy_rate": f"{(compliant/total)*100:.1f}%" if total > 0 else "0%",
                "duration_seconds": round(duration, 2)
            },
            "timestamp": time.ctime(),
            "results": results
        }

        os.makedirs("data/reports", exist_ok=True)
        with open("data/reports/master_audit_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info("==========================================")
        logger.info(f"🏆 MASTER AUDIT COMPLETE")
        logger.info(f"Passed: {compliant} | Flagged: {flagged} | Critical: {critical}")
        logger.info(f"Report saved: data/reports/master_audit_report.json")
        logger.info("==========================================")

if __name__ == "__main__":
    pipeline = AgentGuardPipeline()
    pipeline.run_test_suite()