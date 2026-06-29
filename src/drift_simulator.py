# src/drift_simulator.py
# AgentGuard — Historical Drift Timeline Simulator
# Generates 30 days of realistic agent behavioral
# data for dashboard visualization and demo purposes.

import os
import json
import random
import logging
import datetime
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DriftSimulator:
    """
    Simulates 30 days of realistic enterprise AI agent
    behavioral data including:
    - Gradual prompt integrity degradation
    - Hallucination events
    - Drift acceleration
    - Remediation intervention
    - Post-fix stabilization

    This data powers the AgentGuard Timeline Dashboard.
    """

    def __init__(self):
        os.makedirs("data/dashboard", exist_ok=True)
        os.makedirs("data/timeline", exist_ok=True)

        # Agents we will simulate
        self.agents = [
            {
                "name": "InvoiceProcessingAgent_v2",
                "category": "financial",
                "baseline_integrity": 98.0,
                "drift_start_day": 11,
                "remediation_day": 21,
                "risk_profile": "HIGH"
            },
            {
                "name": "VendorVerificationAgent_v1",
                "category": "vendor",
                "baseline_integrity": 96.0,
                "drift_start_day": 18,
                "remediation_day": 25,
                "risk_profile": "MEDIUM"
            },
            {
                "name": "FraudDetectionAgent_v3",
                "category": "fraud",
                "baseline_integrity": 99.0,
                "drift_start_day": 25,
                "remediation_day": None,  # Not yet fixed
                "risk_profile": "CRITICAL"
            },
            {
                "name": "ComplianceReportAgent_v1",
                "category": "general",
                "baseline_integrity": 94.0,
                "drift_start_day": None,  # Stable all month
                "remediation_day": None,
                "risk_profile": "LOW"
            }
        ]

    def _compute_integrity_score(
        self,
        agent: Dict,
        day: int
    ) -> float:
        """
        Computes realistic integrity score for a given day.
        Models three phases:
        1. Stable phase (baseline)
        2. Drift phase (gradual degradation)
        3. Post-remediation phase (recovery)
        """
        baseline = agent["baseline_integrity"]
        drift_start = agent.get("drift_start_day")
        remediation_day = agent.get("remediation_day")

        # Phase 1: Stable — no drift started yet
        if drift_start is None or day < drift_start:
            noise = random.uniform(-1.5, 1.5)
            return round(
                min(100.0, max(85.0, baseline + noise)),
                1
            )

        # Phase 2: Drifting
        if remediation_day is None or day < remediation_day:
            days_drifting = day - drift_start
            # Accelerating degradation curve
            degradation = (days_drifting ** 1.4) * 1.2
            noise = random.uniform(-2.0, 2.0)
            score = baseline - degradation + noise
            return round(min(100.0, max(20.0, score)), 1)

        # Phase 3: Post-remediation recovery
        days_since_fix = day - remediation_day
        recovery = min(
            baseline,
            (baseline - 25) + (days_since_fix * 3.5)
        )
        noise = random.uniform(-1.0, 1.0)
        return round(min(100.0, max(70.0, recovery + noise)), 1)

    def _compute_hallucination_count(
        self,
        integrity: float,
        day: int,
        agent: Dict
    ) -> int:
        """
        Generates realistic hallucination counts
        inversely proportional to integrity score.
        """
        drift_start = agent.get("drift_start_day")

        # No drift yet — very rare hallucinations
        if drift_start is None or day < drift_start:
            return random.choices(
                [0, 1],
                weights=[95, 5]
            )[0]

        # Drift phase — increasing hallucinations
        if integrity > 85:
            return random.choices(
                [0, 1, 2],
                weights=[70, 25, 5]
            )[0]
        elif integrity > 70:
            return random.choices(
                [0, 1, 2, 3],
                weights=[40, 35, 20, 5]
            )[0]
        elif integrity > 50:
            return random.choices(
                [1, 2, 3, 4],
                weights=[30, 35, 25, 10]
            )[0]
        else:
            return random.choices(
                [2, 3, 4, 5, 6],
                weights=[20, 30, 25, 15, 10]
            )[0]

    def _compute_risk_level(
        self,
        integrity: float
    ) -> str:
        """Maps integrity score to risk level."""
        if integrity >= 90:
            return "LOW"
        elif integrity >= 75:
            return "MEDIUM"
        elif integrity >= 55:
            return "HIGH"
        else:
            return "CRITICAL"

    def _generate_agent_event(
        self,
        agent: Dict,
        day: int,
        integrity: float,
        hallucinations: int
    ) -> Dict[str, Any]:
        """
        Generates a single day's event record
        for a given agent.
        """
        drift_start = agent.get("drift_start_day")
        remediation_day = agent.get("remediation_day")

        # Determine event type for this day
        event_type = "NORMAL"
        event_description = None

        if (
            drift_start and
            day == drift_start
        ):
            event_type = "DRIFT_DETECTED"
            event_description = (
                f"Behavioral drift initiated. "
                f"Prompt integrity began degrading."
            )
        elif (
            remediation_day and
            day == remediation_day
        ):
            event_type = "REMEDIATION_APPLIED"
            event_description = (
                f"AgentGuard triggered auto-remediation. "
                f"Corrected system prompt deployed. "
                f"Pending human approval."
            )
        elif (
            remediation_day and
            day == remediation_day + 1
        ):
            event_type = "HUMAN_APPROVED"
            event_description = (
                f"Governance team approved prompt fix. "
                f"Agent redeployed with constraints."
            )
        elif hallucinations >= 3:
            event_type = "HALLUCINATION_SPIKE"
            event_description = (
                f"{hallucinations} hallucinations detected. "
                f"Automatic alert sent to governance team."
            )

        # Compute drift score
        if drift_start and day >= drift_start:
            if remediation_day and day >= remediation_day:
                drift_score = max(
                    0.0,
                    0.3 - ((day - remediation_day) * 0.03)
                )
            else:
                days_drifting = day - drift_start
                drift_score = min(
                    0.8,
                    days_drifting * 0.06
                )
        else:
            drift_score = round(random.uniform(0.0, 0.05), 3)

        return {
            "day": day,
            "date": (
                datetime.datetime.now(datetime.timezone.utc) -
                datetime.timedelta(days=30 - day)
            ).strftime("%Y-%m-%d"),
            "agent_name": agent["name"],
            "category": agent["category"],
            "integrity_score": integrity,
            "hallucinations_caught": hallucinations,
            "drift_score": round(drift_score, 3),
            "risk_level": self._compute_risk_level(integrity),
            "event_type": event_type,
            "event_description": event_description,
            "tests_run": random.randint(8, 24),
            "tests_passed": max(
                1,
                int(integrity / 100 * random.randint(8, 24))
            )
        }

    def simulate_30_days(self) -> Dict[str, Any]:
        """
        Generates complete 30-day simulation
        for all monitored agents.
        """
        logger.info(
            "🕐 Simulating 30 days of agent behavioral data..."
        )

        all_events = []
        agent_summaries = []

        for agent in self.agents:
            logger.info(
                f"Simulating agent: {agent['name']}"
            )
            agent_events = []
            total_hallucinations = 0
            integrity_trend = []

            for day in range(1, 31):
                integrity = self._compute_integrity_score(
                    agent, day
                )
                hallucinations = self._compute_hallucination_count(
                    integrity, day, agent
                )
                total_hallucinations += hallucinations
                integrity_trend.append(integrity)

                event = self._generate_agent_event(
                    agent, day, integrity, hallucinations
                )
                agent_events.append(event)
                all_events.append(event)

            # Agent summary for dashboard cards
            current_integrity = integrity_trend[-1]
            peak_integrity = max(integrity_trend)
            lowest_integrity = min(integrity_trend)

            agent_summaries.append({
                "agent_name": agent["name"],
                "category": agent["category"],
                "risk_profile": agent["risk_profile"],
                "current_integrity": current_integrity,
                "peak_integrity": peak_integrity,
                "lowest_integrity": lowest_integrity,
                "avg_integrity": round(
                    sum(integrity_trend) / len(integrity_trend),
                    1
                ),
                "total_hallucinations_caught": total_hallucinations,
                "remediation_applied": (
                    agent.get("remediation_day") is not None
                ),
                "current_risk": self._compute_risk_level(
                    current_integrity
                ),
                "status": (
                    "STABLE" if current_integrity >= 88
                    else "DRIFTING" if current_integrity >= 65
                    else "CRITICAL"
                ),
                "drift_started_day": agent.get("drift_start_day"),
                "remediation_day": agent.get("remediation_day"),
                "daily_trend": integrity_trend
            })

        logger.info(
            f"✅ Generated {len(all_events)} events "
            f"across {len(self.agents)} agents"
        )
        return {
            "agent_summaries": agent_summaries,
            "all_events": all_events
        }

    def generate_dashboard_metrics(
        self,
        simulation_data: Dict
    ) -> Dict[str, Any]:
        """
        Computes high-level dashboard KPIs
        from simulation data.
        These feed directly into UiPath Apps.
        """
        summaries = simulation_data["agent_summaries"]
        all_events = simulation_data["all_events"]

        total_hallucinations = sum(
            s["total_hallucinations_caught"]
            for s in summaries
        )
        avg_integrity = round(
            sum(s["current_integrity"] for s in summaries) /
            len(summaries),
            1
        )
        critical_agents = [
            s for s in summaries
            if s["current_risk"] in ["CRITICAL", "HIGH"]
        ]
        remediations_applied = sum(
            1 for s in summaries
            if s["remediation_applied"]
        )
        hallucination_events = [
            e for e in all_events
            if e["event_type"] == "HALLUCINATION_SPIKE"
        ]

        return {
            "dashboard_metrics": {
                "prompt_integrity_index": avg_integrity,
                "total_agents_monitored": len(summaries),
                "hallucinations_caught_30_days": (
                    total_hallucinations
                ),
                "hallucination_spikes": len(
                    hallucination_events
                ),
                "remediations_applied": remediations_applied,
                "critical_agents": len(critical_agents),
                "system_health": (
                    "HEALTHY" if avg_integrity >= 88
                    else "DEGRADED" if avg_integrity >= 70
                    else "CRITICAL"
                )
            },
            "agent_risk_matrix": [
                {
                    "agent": s["agent_name"],
                    "integrity": s["current_integrity"],
                    "risk": s["current_risk"],
                    "status": s["status"],
                    "hallucinations": (
                        s["total_hallucinations_caught"]
                    )
                }
                for s in summaries
            ],
            "weekly_hallucinations": (
                self._compute_weekly_hallucinations(all_events)
            ),
            "agent_summaries": summaries
        }

    def _compute_weekly_hallucinations(
        self,
        events: List[Dict]
    ) -> List[Dict]:
        """Aggregates hallucinations by week for chart."""
        weeks = {"Week 1": 0, "Week 2": 0,
                 "Week 3": 0, "Week 4": 0}
        for event in events:
            day = event["day"]
            count = event["hallucinations_caught"]
            if day <= 7:
                weeks["Week 1"] += count
            elif day <= 14:
                weeks["Week 2"] += count
            elif day <= 21:
                weeks["Week 3"] += count
            else:
                weeks["Week 4"] += count
        return [
            {"week": k, "hallucinations": v}
            for k, v in weeks.items()
        ]

    def save_all(
        self,
        simulation_data: Dict,
        dashboard_metrics: Dict
    ) -> None:
        """Saves all simulation data for UiPath integration."""

        # Full timeline (for detailed charts)
        with open("data/timeline/agent_timeline.json", "w") as f:
            json.dump(simulation_data, f, indent=2)

        # Dashboard metrics (for UiPath Apps cards)
        with open("data/dashboard/metrics.json", "w") as f:
            json.dump(dashboard_metrics, f, indent=2)

        logger.info(
            "✅ Timeline saved: data/timeline/agent_timeline.json"
        )
        logger.info(
            "✅ Dashboard metrics: data/dashboard/metrics.json"
        )


if __name__ == "__main__":
    random.seed(42)  # Reproducible results for demo

    simulator = DriftSimulator()

    # Generate 30 days of data
    simulation_data = simulator.simulate_30_days()

    # Compute dashboard metrics
    dashboard_metrics = simulator.generate_dashboard_metrics(
        simulation_data
    )

    # Save everything
    simulator.save_all(simulation_data, dashboard_metrics)

    # Print dashboard summary
    metrics = dashboard_metrics["dashboard_metrics"]
    print("\n📊 AGENTGUARD DASHBOARD METRICS")
    print("=" * 50)
    print(json.dumps(metrics, indent=2))
    print("\n🎯 AGENT RISK MATRIX")
    print("=" * 50)
    print(json.dumps(
        dashboard_metrics["agent_risk_matrix"],
        indent=2
    ))