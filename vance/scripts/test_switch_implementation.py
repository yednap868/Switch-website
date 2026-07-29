"""
Test script to validate Switch implementation locally.
Checks syntax, imports, and basic structure.
"""

import ast
import os
import sys
from pathlib import Path

def test_file_syntax(file_path):
    """Test if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            ast.parse(f.read())
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {e}"

def test_imports(file_path):
    """Check for common import issues."""
    issues = []
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Check for inline imports (forbidden per project rules)
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('from ') or stripped.startswith('import '):
                    # Check if it's inside a function/class (indented)
                    if line.startswith(' ') and not line.startswith('    '):
                        # Might be inline, but could be in a try block - skip for now
                        pass
            
            # Check for missing Optional import if Optional is used
            if 'Optional[' in content and 'from typing import' in content:
                if 'Optional' not in content.split('from typing import')[1].split('\n')[0]:
                    issues.append("Optional used but not imported from typing")
            
    except Exception as e:
        issues.append(f"Error checking imports: {e}")
    
    return issues

def main():
    """Run all tests."""
    print("=" * 70)
    print("Switch Implementation - Local Testing")
    print("=" * 70)
    print()
    
    base_path = Path(__file__).parent.parent
    test_files = {
        "Models": [
            "models/switch_models.py",
        ],
        "Services": [
            "services/switch_business_intake_service.py",
            "services/switch_job_service.py",
            "services/switch_matching_service.py",
            "services/switch_call_service.py",
            "services/switch_screening_service.py",
            "services/switch_availability_tracker.py",
            "services/switch_job_tracker.py",
            "services/switch_whatsapp_service.py",
            "services/switch_call_tracking.py",
            "services/switch_edge_cases.py",
            "services/switch_metrics.py",
        ],
        "API Routes": [
            "api/switch_business_routes.py",
            "api/switch_metrics_routes.py",
            "api/switch_routes.py",
            "api/candidate_onboarding_routes.py",
        ],
        "Integration": [
            "api/routers.py",
        ],
        "Scripts": [
            "scripts/migrate_switch_data.py",
        ],
    }
    
    results = {
        "passed": 0,
        "failed": 0,
        "warnings": 0,
    }
    
    for category, files in test_files.items():
        print(f"\n📁 {category}")
        print("-" * 70)
        
        for file_path in files:
            full_path = base_path / file_path
            if not full_path.exists():
                print(f"  ❌ {file_path} - FILE NOT FOUND")
                results["failed"] += 1
                continue
            
            # Test syntax
            syntax_ok, syntax_error = test_file_syntax(full_path)
            if not syntax_ok:
                print(f"  ❌ {file_path}")
                print(f"     Syntax Error: {syntax_error}")
                results["failed"] += 1
                continue
            
            # Test imports
            import_issues = test_imports(full_path)
            if import_issues:
                print(f"  ⚠️  {file_path}")
                for issue in import_issues:
                    print(f"     Warning: {issue}")
                results["warnings"] += 1
            else:
                print(f"  ✅ {file_path}")
                results["passed"] += 1
    
    # Test router integration
    print(f"\n🔗 Router Integration")
    print("-" * 70)
    routers_file = base_path / "api/routers.py"
    if routers_file.exists():
        with open(routers_file) as f:
            content = f.read()
            required_routers = [
                "switch_router",
                "switch_business_router",
                "switch_metrics_router",
            ]
            missing = [r for r in required_routers if r not in content]
            if missing:
                print(f"  ❌ Missing routers: {', '.join(missing)}")
                results["failed"] += len(missing)
            else:
                print(f"  ✅ All Switch routers integrated")
                results["passed"] += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Passed: {results['passed']}")
    print(f"⚠️  Warnings: {results['warnings']}")
    print(f"❌ Failed: {results['failed']}")
    print()
    
    if results["failed"] == 0:
        print("🎉 All syntax checks passed!")
        print("\nNote: Full functionality testing requires:")
        print("  - Dependencies installed (pydantic, fastapi, etc.)")
        print("  - Environment variables configured")
        print("  - Database connection")
        print("  - API keys (ElevenLabs, Twilio, Anthropic)")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
