# src/test_generator.py
# AgentGuard — Autonomous Test Scenario Generator
# Converts enterprise compliance rules into
# structured, executable test cases using Groq LLM

import os
import json
import logging
import datetime
from typing import List, Dict, Any
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestScenarioGenerator:
    """
    Converts structured compliance rules into
    realistic, executable test payloads.

    Each rule generates THREE test cases:
    - COMPLIANT: Should pass cleanly
    - BOUNDARY:  Edge case at the exact threshold
    - CRITICAL:  Clear violation that must be caught
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

    def generate_scenarios_for_rule(
        self,
        rule: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        For a single compliance rule, generates three
        realistic UiPath agent simulation payloads.
        """
        prompt = f"""
        You are a Senior QA Architect designing test cases 
        for an enterprise AI agent governance system.

        Given this compliance rule:
        Rule ID: {rule['id']}
        Rule Text: {rule['text']}
        Category: {rule['category']}
        Severity: {rule['severity']}
        Threshold: {rule.get('threshold', 'N/A')}
        Expected Action: {rule['action']}

        Generate exactly 3 test scenarios as a JSON object 
        with key "scenarios" containing a list.

        Each scenario must have:
        - scenario_id: (e.g., {rule['id']}_TC001)
        - scenario_type: (COMPLIANT, BOUNDARY, or CRITICAL)
        - description: (one sentence explaining what is tested)
        - agent_name: (realistic enterprise agent name)
        - extracted_amount: (realistic dollar amount as float)
        - agent_reasoning: (realistic LLM reasoning trace)
        - agent_output: (realistic LLM output text)
        - expected_status: (COMPLIANT, FLAGGED, or CRITICAL)
        - expected_human_gate: (true or false)

        Make scenarios highly realistic — as if a real 
        enterprise AI agent produced them.
        Financial amounts must be specific (not round numbers).
        Agent reasoning must sound like a real LLM reasoning trace.
        """

        try:
            logger.info(
                f"Generating scenarios for rule {rule['id']}..."
            )
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Senior QA Architect. "
                            "Output valid JSON only. "
                            "Be extremely realistic and precise."
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

            data = json.loads(
                response.choices[0].message.content
            )
            scenarios = data.get("scenarios", [])
            logger.info(
                f"✅ {len(scenarios)} scenarios generated "
                f"for rule {rule['id']}"
            )
            return scenarios

        except json.JSONDecodeError as e:
            logger.error(
                f"JSON parse error for rule "
                f"{rule['id']}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Groq error for rule {rule['id']}: {e}"
            )
            return []

    def generate_all_scenarios(
        self,
        rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Iterates over all extracted policy rules
        and generates test scenarios for each.
        """
        all_scenarios = []

        for rule in rules:
            scenarios = self.generate_scenarios_for_rule(rule)
            for scenario in scenarios:
                # Attach the source rule for traceability
                scenario["source_rule_id"] = rule["id"]
                scenario["source_rule_text"] = rule["text"]
                all_scenarios.append(scenario)

        logger.info(
            f"Total scenarios generated: {len(all_scenarios)}"
        )
        return all_scenarios

    def save_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        output_path: str = "mock_data/generated_test_cases.json"
    ) -> None:
        """
        Saves all generated test cases to a structured
        JSON file with metadata for audit purposes.
        """
        os.makedirs(
            os.path.dirname(output_path),
            exist_ok=True
        )

        output = {
            "metadata": {
                "generated_at": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "total_scenarios": len(scenarios),
                "generator_model": self.model,
                "source": "AgentGuard Test Scenario Generator"
            },
            "test_cases": scenarios
        }

        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(
            f"✅ Test cases saved to {output_path}"
        )

    def export_uipath_test_manager_schema(
        self,
        scenarios: List[Dict[str, Any]],
        output_path: str = "data/uipath_test_manager.json"
    ) -> None:
        """
        Exports generated test cases in UiPath Test Manager
        compatible schema format.

        This allows AgentGuard to directly provision
        test requirements into UiPath Test Cloud,
        closing the loop between policy extraction
        and enterprise test management.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Group scenarios by source rule
        rules_map = {}
        for scenario in scenarios:
            rule_id = scenario.get("source_rule_id", "UNKNOWN")
            if rule_id not in rules_map:
                rules_map[rule_id] = {
                    "RequirementID": rule_id,
                    "RequirementDescription": scenario.get(
                        "source_rule_text", ""
                    ),
                    "RequirementSource": "AgentGuard Policy Parser",
                    "CreatedAt": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "TestCases": []
                }

            # Map scenario type to UiPath risk level
            risk_map = {
                "COMPLIANT": "LOW",
                "BOUNDARY": "MEDIUM",
                "CRITICAL": "HIGH"
            }

            # Map expected status to UiPath assertion type
            assertion_map = {
                "COMPLIANT": "PASS",
                "FLAGGED": "WARNING",
                "CRITICAL": "FAIL"
            }

            rules_map[rule_id]["TestCases"].append({
                "TestCaseID": scenario.get("scenario_id"),
                "TestCaseName": scenario.get("description"),
                "ScenarioType": scenario.get("scenario_type"),
                "AgentName": scenario.get("agent_name"),
                "InputAmount": scenario.get("extracted_amount"),
                "ExpectedAssertion": assertion_map.get(
                    scenario.get("expected_status", "COMPLIANT"),
                    "PASS"
                ),
                "RiskLevel": risk_map.get(
                    scenario.get("scenario_type", "COMPLIANT"),
                    "LOW"
                ),
                "HumanGateRequired": scenario.get(
                    "expected_human_gate", False
                ),
                "AutomationStatus": "READY",
                "Tags": [
                    scenario.get("source_rule_id"),
                    scenario.get("scenario_type"),
                    "AgentGuard",
                    "AIGovernance"
                ]
            })

        # Build final UiPath Test Manager schema
        uipath_schema = {
            "SchemaVersion": "1.0",
            "ProjectName": "AgentGuard AI Governance",
            "ExportedAt": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            "ExportedBy": "AgentGuard Test Scenario Generator",
            "TotalRequirements": len(rules_map),
            "TotalTestCases": len(scenarios),
            "Requirements": list(rules_map.values())
        }

        with open(output_path, "w") as f:
            json.dump(uipath_schema, f, indent=2)

        logger.info(
            f"✅ UiPath Test Manager schema exported: "
            f"{output_path}"
        )
        logger.info(
            f"   Requirements: {len(rules_map)} | "
            f"Test Cases: {len(scenarios)}"
        )


if __name__ == "__main__":
    # Load rules from policy parser output
    policy_path = "config/policy.json"

    if not os.path.exists(policy_path):
        logger.error(
            f"Policy file not found at {policy_path}. "
            f"Run policy_parser.py first."
        )
    else:
        with open(policy_path, "r") as f:
            policy_data = json.load(f)

        rules = policy_data.get("rules", [])
        logger.info(
            f"Loaded {len(rules)} rules from {policy_path}"
        )

        generator = TestScenarioGenerator()

        # Generate scenarios
        scenarios = generator.generate_all_scenarios(rules)

        # Save standard format
        generator.save_scenarios(scenarios)

        # NEW: Export UiPath Test Manager schema
        generator.export_uipath_test_manager_schema(scenarios)

        # Preview
        print("\n📋 SAMPLE GENERATED TEST CASES:")
        print("=" * 60)
        preview = (
            scenarios[:2] if len(scenarios) >= 2
            else scenarios
        )
        print(json.dumps(preview, indent=2))
        print(
            f"\n✅ Standard output: "
            f"mock_data/generated_test_cases.json"
        )
        print(
            f"✅ UiPath Test Manager: "
            f"data/uipath_test_manager.json"
        )