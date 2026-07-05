import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import subprocess
import os

def run_test_suite():
    print("=" * 60)
    print("🚀 SHADOWMAP v1.5.0 MASTER TEST RUNNER")
    print("=" * 60)
    
    python_exe = sys.executable
    test_files = [
        ("Physics Mathematical Suite", [python_exe, "test_physics.py"]),
        ("Core PyTest Suite", [python_exe, "-m", "pytest", "tests/test.py", "-v"]),
        ("v1.4 Simple Integration Suite", [python_exe, "-m", "pytest", "test_v14_simple.py", "-v"]),
        ("v1.4 API Integration Suite", [python_exe, "-m", "pytest", "test_v14_api.py", "-v"])
    ]
    
    all_passed = True
    results = []
    
    for name, cmd in test_files:
        print(f"\n▶️ Running: {name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding='utf-8')
            if result.returncode == 0:
                print(f"✅ {name}: PASSED")
                results.append((name, "PASSED"))
            else:
                print(f"❌ {name}: FAILED")
                print(result.stdout)
                print(result.stderr)
                results.append((name, "FAILED"))
                all_passed = False
        except Exception as e:
            print(f"❌ {name}: ERROR ({str(e)})")
            results.append((name, f"ERROR ({str(e)})"))
            all_passed = False
            
    print("\n" + "=" * 60)
    print("📊 SUMMARY OF TEST RESULTS:")
    print("=" * 60)
    for name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"   {symbol} {name}: {status}")
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 ALL TEST SUITES PASSED SUCCESSFULLY! SHADOWMAP v1.5.0 IS READY FOR DEPLOYMENT.")
        sys.exit(0)
    else:
        print("\n⚠️ SOME TEST SUITES FAILED. PLEASE REVIEW LOGS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    run_test_suite()
