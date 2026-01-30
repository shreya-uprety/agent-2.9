"""
Voice Agent Tool Testing Script
Simulates voice agent requests from frontend and validates tool execution
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path("output")

class VoiceAgentTester:
    def __init__(self):
        self.current_patient = None
        self.test_results = []
        
    def set_patient(self, patient_id):
        """Switch to specific patient"""
        print(f"\n{'='*60}")
        print(f"🔄 Switching to Patient: {patient_id}")
        print(f"{'='*60}")
        
        response = requests.post(
            f"{BASE_URL}/patient/switch",
            json={"patientId": patient_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.current_patient = data.get('patientId')
            print(f"✅ Switched to patient: {self.current_patient}")
            return True
        else:
            print(f"❌ Failed to switch patient: {response.status_code}")
            return False
    
    def send_voice_command(self, command):
        """Simulate voice agent sending command"""
        print(f"\n🎤 Voice Command: \"{command}\"")
        print(f"   Patient: {self.current_patient}")
        
        # Simulate chat history format
        chat_history = [
            {"role": "user", "content": command}
        ]
        
        try:
            response = requests.post(
                f"{BASE_URL}/send-chat",
                json=chat_history,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.text if isinstance(response.text, str) else response.json()
                print(f"✅ Response received ({len(str(result))} chars)")
                return True, result
            else:
                print(f"❌ Error: Status {response.status_code}")
                return False, response.text
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Timeout after 30 seconds")
            return False, "Timeout"
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False, str(e)
    
    def check_output_files(self, expected_files):
        """Check if expected output files were created"""
        print(f"\n📂 Checking output files...")
        found_files = []
        
        for filename in expected_files:
            filepath = OUTPUT_DIR / filename
            if filepath.exists():
                # Check file modification time (recent = within last 10 seconds)
                mtime = filepath.stat().st_mtime
                age = time.time() - mtime
                
                if age < 10:
                    print(f"   ✅ {filename} (modified {age:.1f}s ago)")
                    found_files.append(filename)
                else:
                    print(f"   ⚠️ {filename} (old file, {age:.1f}s ago)")
            else:
                print(f"   ❌ {filename} (not found)")
        
        return found_files
    
    def test_navigate_tool(self):
        """Test: Show me encounter 2"""
        print(f"\n{'#'*60}")
        print("TEST 1: Navigate Canvas Tool")
        print(f"{'#'*60}")
        
        success, result = self.send_voice_command("Show me encounter 2")
        
        # Check if focus operation was executed
        expected_files = ["focus_payload.json", "focus_response.json"]
        found = self.check_output_files(expected_files)
        
        if found:
            # Validate payload content
            with open(OUTPUT_DIR / "focus_payload.json", "r") as f:
                payload = json.load(f)
                print(f"\n📋 Focus Payload:")
                print(f"   patientId: {payload.get('patientId')}")
                print(f"   objectId: {payload.get('objectId')}")
                
                if payload.get('patientId') == self.current_patient:
                    print(f"   ✅ Patient ID matches current patient")
                else:
                    print(f"   ❌ Patient ID mismatch!")
        
        return success and len(found) > 0
    
    def test_create_todo_tool(self):
        """Test: Create task to analyze labs"""
        print(f"\n{'#'*60}")
        print("TEST 2: Generate Task Tool")
        print(f"{'#'*60}")
        
        success, result = self.send_voice_command("Create task to analyze recent lab results")
        
        # Wait a bit for background task
        print("⏳ Waiting 3 seconds for background task...")
        time.sleep(3)
        
        # Check if TODO was created
        expected_files = ["chatmode_todo_generated.json", "chatmode_todo_object_response.json"]
        found = self.check_output_files(expected_files)
        
        if "chatmode_todo_object_response.json" in found:
            with open(OUTPUT_DIR / "chatmode_todo_object_response.json", "r") as f:
                todo_response = json.load(f)
                print(f"\n📋 TODO Response:")
                print(f"   id: {todo_response.get('id')}")
                print(f"   patientId: {todo_response.get('todoData', {}).get('patientId', 'N/A')}")
        
        return success and len(found) > 0
    
    def test_easl_tool(self):
        """Test: Query EASL guidelines"""
        print(f"\n{'#'*60}")
        print("TEST 3: EASL Guideline Tool")
        print(f"{'#'*60}")
        
        success, result = self.send_voice_command("What does EASL guideline say about DILI diagnosis?")
        
        # Wait for EASL processing
        print("⏳ Waiting 3 seconds for EASL processing...")
        time.sleep(3)
        
        # Check if EASL iframe was initiated
        expected_files = ["initiate_iframe_payload.json", "initiate_iframe_response.json"]
        found = self.check_output_files(expected_files)
        
        if "initiate_iframe_payload.json" in found:
            with open(OUTPUT_DIR / "initiate_iframe_payload.json", "r") as f:
                payload = json.load(f)
                print(f"\n📋 EASL Payload:")
                print(f"   patientId: {payload.get('patientId')}")
                print(f"   query: {payload.get('query')[:50]}...")
                
                if payload.get('patientId') == self.current_patient:
                    print(f"   ✅ Patient ID matches")
        
        return success and len(found) > 0
    
    def test_general_query(self):
        """Test: General information query"""
        print(f"\n{'#'*60}")
        print("TEST 4: General Query (No Tool)")
        print(f"{'#'*60}")
        
        success, result = self.send_voice_command("What is the patient's current diagnosis?")
        
        # This should not create specific tool files, just return an answer
        if success:
            print(f"✅ Received answer (general query, no tool execution expected)")
        
        return success

def run_complete_test():
    """Run complete voice agent tool test suite"""
    print("\n" + "🧪 "*30)
    print("VOICE AGENT TOOL VALIDATION TEST SUITE")
    print("🧪 "*30)
    
    tester = VoiceAgentTester()
    results = []
    
    # Set patient first
    if not tester.set_patient("p0001"):
        print("\n❌ Failed to set patient. Aborting tests.")
        return
    
    print("\n⚠️  IMPORTANT: Make sure the backend server is running!")
    print("   python server.py or uvicorn server:app --reload")
    input("\nPress Enter to start tests...")
    
    # Run tests
    tests = [
        ("Navigate Tool", tester.test_navigate_tool),
        ("Create TODO Tool", tester.test_create_todo_tool),
        ("EASL Tool", tester.test_easl_tool),
        ("General Query", tester.test_general_query),
    ]
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((test_name, False))
        
        time.sleep(2)  # Brief pause between tests
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Voice agent tools are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs above for details.")
    
    print("\n💡 TIP: Check the output/ folder for generated payloads")
    print("   Each payload shows patientId and tool-specific data")

if __name__ == "__main__":
    run_complete_test()
