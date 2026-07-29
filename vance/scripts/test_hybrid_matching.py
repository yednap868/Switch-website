#!/usr/bin/env python3
"""
Interactive Test Script for Hybrid Matching Service

This script allows you to test the hybrid matching service with various queries
and evaluate its performance in suggesting candidates.

Usage:
    python test_hybrid_matching.py
"""

import json
import os
import sys
import time
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.hybrid_matching_service import HybridMatchingService, MatchedProfile


class HybridMatchingTester:
    """Interactive tester for hybrid matching service."""

    def __init__(self):
        self.service = HybridMatchingService()
        self.test_history = []

    def print_header(self):
        """Print welcome header."""
        print("\n" + "=" * 80)
        print("🔍 HYBRID MATCHING SERVICE - INTERACTIVE TESTER")
        print("=" * 80)
        print(
            "\nThis tool tests the performance of hybrid matching for candidate suggestions."
        )
        print("You can enter custom queries or use pre-defined test cases.\n")

    def print_menu(self):
        """Print main menu options."""
        print("\n" + "-" * 80)
        print("OPTIONS:")
        print("  1. Test with custom job requirements")
        print("  2. Test with pre-defined scenarios")
        print("  3. View test history")
        print("  4. Performance comparison")
        print("  5. Exit")
        print("-" * 80)

    def get_predefined_scenarios(self) -> Dict[str, Dict]:
        """Return pre-defined test scenarios."""
        return {
            "1": {
                "name": "Senior Python Developer",
                "data": {
                    "job_title": "Senior Python Developer",
                    "required_skills": "Python, Django, FastAPI, PostgreSQL, Docker, AWS",
                    "experience_level": "5+ years",
                    "office_location": "Bangalore",
                    "work_model": "Hybrid",
                    "salary_budget": "25-35 LPA",
                    "hiring_urgency": "Immediate",
                },
            },
            "2": {
                "name": "Frontend Engineer",
                "data": {
                    "job_title": "Frontend Engineer",
                    "required_skills": "React, TypeScript, Next.js, Tailwind CSS",
                    "experience_level": "3-5 years",
                    "office_location": "Remote",
                    "work_model": "Remote",
                    "salary_budget": "$100k-$130k",
                    "hiring_urgency": "Within 2 months",
                },
            },
            "3": {
                "name": "Full Stack Engineer (Startup)",
                "data": {
                    "job_title": "Full Stack Engineer",
                    "required_skills": "Node.js, React, MongoDB, AWS, Kubernetes",
                    "experience_level": "4+ years",
                    "office_location": "San Francisco",
                    "work_model": "On-site",
                    "salary_budget": "$140k-$180k",
                    "hiring_urgency": "ASAP",
                    "ideal_candidate": "Self-starter comfortable with ambiguity, startup experience preferred",
                },
            },
            "4": {
                "name": "DevOps Engineer",
                "data": {
                    "job_title": "DevOps Engineer",
                    "required_skills": "Kubernetes, Docker, Terraform, AWS/GCP, CI/CD",
                    "experience_level": "5+ years",
                    "office_location": "Pune",
                    "work_model": "Hybrid",
                    "salary_budget": "30-40 LPA",
                },
            },
            "5": {
                "name": "Data Scientist",
                "data": {
                    "job_title": "Data Scientist",
                    "required_skills": "Python, TensorFlow, PyTorch, SQL, Statistics",
                    "experience_level": "3-7 years",
                    "office_location": "Bangalore",
                    "work_model": "Remote",
                    "salary_budget": "20-30 LPA",
                    "ideal_candidate": "Strong ML fundamentals, experience with production ML systems",
                },
            },
        }

    def custom_query_builder(self) -> Dict:
        """Interactive builder for custom job requirements."""
        print("\n" + "=" * 80)
        print("CUSTOM JOB REQUIREMENTS BUILDER")
        print("=" * 80)
        print("Enter job requirements (press Enter to skip optional fields)\n")

        job_data = {}

        # Required fields
        job_data["job_title"] = input("Job Title (required): ").strip()
        if not job_data["job_title"]:
            print("❌ Job title is required!")
            return None

        job_data["required_skills"] = input(
            "Required Skills (e.g., Python, AWS): "
        ).strip()

        # Optional fields
        job_data["experience_level"] = input(
            "Experience Level (e.g., 3-5 years): "
        ).strip()
        job_data["office_location"] = input(
            "Office Location (e.g., Bangalore, Remote): "
        ).strip()
        job_data["work_model"] = input("Work Model (Remote/Hybrid/On-site): ").strip()
        job_data["salary_budget"] = input("Salary Budget (e.g., 25-35 LPA): ").strip()
        job_data["hiring_urgency"] = input("Hiring Urgency (e.g., Immediate): ").strip()
        job_data["ideal_candidate"] = input(
            "Ideal Candidate Description (optional): "
        ).strip()

        return job_data

    def run_matching_test(
        self, job_data: Dict, scenario_name: str = "Custom", limit: int = 3
    ) -> Dict:
        """
        Run a matching test and return results with timing.

        Args:
            job_data: Job requirements dictionary
            scenario_name: Name of the test scenario
            limit: Number of matches to return

        Returns:
            Dictionary with results and metrics
        """
        print(f"\n{'=' * 80}")
        print(f"🚀 RUNNING TEST: {scenario_name}")
        print(f"{'=' * 80}\n")

        # Display input
        print("📋 JOB REQUIREMENTS:")
        for key, value in job_data.items():
            if value:
                print(f"  • {key.replace('_', ' ').title()}: {value}")

        print(f"\n⏱️  Starting matching process...\n")

        # Time the matching
        start_time = time.time()

        try:
            matches = self.service.find_job_seeker_matches(
                job_provider_data=job_data, limit=limit, min_score=0.5
            )
            elapsed_time = time.time() - start_time

            # Display results
            print(f"\n{'=' * 80}")
            print(f"✅ MATCHING COMPLETED in {elapsed_time:.2f}s")
            print(f"{'=' * 80}\n")

            if matches:
                print(f"📊 FOUND {len(matches)} CANDIDATE MATCHES:\n")
                self._display_matches(matches)
            else:
                print("❌ No matches found")

            # Collect metrics
            result = {
                "scenario_name": scenario_name,
                "job_data": job_data,
                "num_matches": len(matches),
                "elapsed_time": elapsed_time,
                "matches": matches,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "success": True,
            }

            self.test_history.append(result)
            return result

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ ERROR: {e}")
            print(f"⏱️  Failed after {elapsed_time:.2f}s\n")

            result = {
                "scenario_name": scenario_name,
                "job_data": job_data,
                "num_matches": 0,
                "elapsed_time": elapsed_time,
                "matches": [],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "success": False,
                "error": str(e),
            }

            self.test_history.append(result)
            return result

    def _display_matches(self, matches: List[MatchedProfile]):
        """Display matched profiles in a readable format."""
        for i, match in enumerate(matches, 1):
            print(f"{'-' * 80}")
            print(f"🎯 MATCH #{i} - {match.name}")
            print(f"{'-' * 80}")
            print(f"  Score:          {match.match_score:.2f}")
            print(f"  Email:          {match.email}")
            print(f"  Target Role:    {match.target_role or 'N/A'}")
            print(f"  Skills:         {match.core_skills or 'N/A'}")
            print(f"  Experience:     {match.work_experience or 'N/A'}")
            print(f"  Location:       {match.current_location or 'N/A'}")
            print(f"  Salary Exp:     {match.salary_expectations or 'N/A'}")
            print(f"  LinkedIn:       {match.linkedin_url or 'N/A'}")
            print(f"\n  💡 Match Reason:")
            print(f"     {match.match_reason}\n")

    def test_predefined_scenarios(self):
        """Run tests with pre-defined scenarios."""
        scenarios = self.get_predefined_scenarios()

        print("\n" + "=" * 80)
        print("PRE-DEFINED TEST SCENARIOS")
        print("=" * 80)

        for key, scenario in scenarios.items():
            print(f"  {key}. {scenario['name']}")

        print(f"  0. Test all scenarios")
        print(f"  b. Back to main menu")

        choice = input("\nSelect scenario: ").strip()

        if choice == "b":
            return
        elif choice == "0":
            print("\n🚀 Running all scenarios...\n")
            for key, scenario in scenarios.items():
                self.run_matching_test(scenario["data"], scenario["name"])
                print("\n" + "=" * 80 + "\n")
        elif choice in scenarios:
            scenario = scenarios[choice]
            self.run_matching_test(scenario["data"], scenario["name"])
        else:
            print("❌ Invalid choice")

    def view_test_history(self):
        """Display test history and statistics."""
        if not self.test_history:
            print("\n⚠️  No test history available. Run some tests first!\n")
            return

        print("\n" + "=" * 80)
        print("📊 TEST HISTORY & STATISTICS")
        print("=" * 80)

        total_tests = len(self.test_history)
        successful_tests = sum(1 for t in self.test_history if t["success"])
        avg_time = sum(t["elapsed_time"] for t in self.test_history) / total_tests
        avg_matches = sum(t["num_matches"] for t in self.test_history) / total_tests

        print(f"\n📈 SUMMARY:")
        print(f"  • Total Tests:       {total_tests}")
        print(f"  • Successful:        {successful_tests}")
        print(f"  • Failed:            {total_tests - successful_tests}")
        print(f"  • Avg Time:          {avg_time:.2f}s")
        print(f"  • Avg Matches:       {avg_matches:.1f}")

        print(f"\n📋 TEST DETAILS:\n")
        for i, test in enumerate(self.test_history, 1):
            status = "✅" if test["success"] else "❌"
            print(f"{status} Test #{i} - {test['scenario_name']}")
            print(f"     Time: {test['timestamp']}")
            print(f"     Duration: {test['elapsed_time']:.2f}s")
            print(f"     Matches: {test['num_matches']}")
            if not test["success"]:
                print(f"     Error: {test.get('error', 'Unknown')}")
            print()

    def performance_comparison(self):
        """Compare performance across different query types."""
        if len(self.test_history) < 2:
            print("\n⚠️  Need at least 2 tests for comparison. Run more tests!\n")
            return

        print("\n" + "=" * 80)
        print("⚡ PERFORMANCE COMPARISON")
        print("=" * 80 + "\n")

        # Sort by elapsed time
        by_time = sorted(self.test_history, key=lambda x: x["elapsed_time"])
        print("🏃 FASTEST QUERIES:")
        for test in by_time[:3]:
            print(
                f"  • {test['scenario_name']}: {test['elapsed_time']:.2f}s ({test['num_matches']} matches)"
            )

        print("\n🐢 SLOWEST QUERIES:")
        for test in by_time[-3:]:
            print(
                f"  • {test['scenario_name']}: {test['elapsed_time']:.2f}s ({test['num_matches']} matches)"
            )

        # Sort by number of matches
        by_matches = sorted(
            self.test_history, key=lambda x: x["num_matches"], reverse=True
        )
        print("\n🎯 MOST MATCHES:")
        for test in by_matches[:3]:
            print(
                f"  • {test['scenario_name']}: {test['num_matches']} matches ({test['elapsed_time']:.2f}s)"
            )

    def run(self):
        """Run the interactive tester."""
        self.print_header()

        while True:
            self.print_menu()
            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                job_data = self.custom_query_builder()
                if job_data:
                    limit = input("\nNumber of matches to return (default 3): ").strip()
                    limit = int(limit) if limit.isdigit() else 3
                    self.run_matching_test(job_data, "Custom Query", limit)

            elif choice == "2":
                self.test_predefined_scenarios()

            elif choice == "3":
                self.view_test_history()

            elif choice == "4":
                self.performance_comparison()

            elif choice == "5":
                print("\n👋 Exiting tester. Goodbye!\n")
                break

            else:
                print("\n❌ Invalid choice. Please select 1-5.\n")


def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it before running this script.")
        sys.exit(1)

    try:
        tester = HybridMatchingTester()
        tester.run()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
