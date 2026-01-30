"""
Quick Voice Agent Test - Essential Operations Only
Run this for fast validation of core functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_command(command, description):
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Command: \"{command}\"")
    print('-'*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/send-chat",
            json=[{"role": "user", "content": command}],
            timeout=30
        )
        result = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {result}")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*60)
    print("VOICE AGENT QUICK TEST")
    print("="*60)
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Server is running on {BASE_URL}")
    except:
        print(f"❌ Server not accessible at {BASE_URL}")
        print("Please start the server: uvicorn server:app --reload")
        return
    
    # Get current patient
    try:
        response = requests.get(f"{BASE_URL}/patient/current")
        patient = response.json().get('patientId')
        print(f"📋 Current Patient: {patient}")
    except:
        print("⚠️  Could not get current patient")
    
    print("\nRunning 4 essential tests...")
    
    tests = [
        ("Show me encounter 2", "1. Navigate Canvas"),
        ("Create task to analyze lab results", "2. Generate Task (wait 10s)"),
        ("What does EASL say about DILI?", "3. EASL Query (wait 8s)"),
        ("What is the patient's current diagnosis?", "4. General Query")
    ]
    
    results = []
    for command, description in tests:
        success = test_command(command, description)
        results.append(success)
        
        # Wait longer for background operations
        if "Task" in description:
            print("⏳ Waiting 10s for background processing...")
            time.sleep(10)
        elif "EASL" in description:
            print("⏳ Waiting 8s for EASL processing...")
            time.sleep(8)
        else:
            time.sleep(2)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Check logs above.")
        print("\nTroubleshooting:")
        print("  1. Check server logs for detailed errors")
        print("  2. Verify Google API key in .env")
        print("  3. Ensure https://iso-clinic-v3.vercel.app is accessible")
    
    print("\nFor detailed testing, run:")
    print("  python test_all_tools_comprehensive.py")
    print("\nFor troubleshooting guide, see:")
    print("  TESTING_GUIDE.md")

if __name__ == "__main__":
    main()
