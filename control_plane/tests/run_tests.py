"""
Simple Test Runner for Factory Control Plane API - PROTOTYPE

This script runs all the simplified tests for the prototype.
"""

import subprocess
import sys
import os

def run_tests():
    """Run all simplified tests."""
    print("🧪 Running Factory Control Plane API Tests (Prototype)")
    print("=" * 60)
    
    # Get the tests directory
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    
    # List of test files
    test_files = [
        "test_products_simple.py",
        "test_artifacts_simple.py",
        "test_tenants_simple.py", 
        "test_platforms_simple.py",
        "test_pipelines_simple.py",
        "test_states_simple.py",
        "test_metrics_simple.py"
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_file in test_files:
        test_path = os.path.join(tests_dir, test_file)
        if os.path.exists(test_path):
            print(f"\n📋 Running {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"
                ], capture_output=True, text=True, cwd=tests_dir)
                
                if result.returncode == 0:
                    print(f"✅ {test_file} - PASSED")
                    # Count tests from output
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if '::' in line and 'PASSED' in line:
                            passed_tests += 1
                            total_tests += 1
                else:
                    print(f"❌ {test_file} - FAILED")
                    print(result.stdout)
                    print(result.stderr)
            except Exception as e:
                print(f"❌ Error running {test_file}: {e}")
        else:
            print(f"⚠️  {test_file} not found")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Prototype API is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
