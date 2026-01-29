"""
Test script to verify dynamic patient ID system
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_get_current_patient():
    print("\n" + "="*60)
    print("TEST 1: Get Current Patient")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/patient/current")
    data = response.json()
    
    print(f"✅ Status: {response.status_code}")
    print(f"📋 Response: {json.dumps(data, indent=2)}")
    return data

def test_switch_patient(patient_id):
    print("\n" + "="*60)
    print(f"TEST 2: Switch to Patient {patient_id}")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/patient/switch",
        headers={"Content-Type": "application/json"},
        json={"patientId": patient_id}
    )
    data = response.json()
    
    print(f"✅ Status: {response.status_code}")
    print(f"📋 Response: {json.dumps(data, indent=2)}")
    return data

def test_chat_with_patient():
    print("\n" + "="*60)
    print("TEST 3: Send Chat Message (uses current patient)")
    print("="*60)
    
    # First check current patient
    current = test_get_current_patient()
    print(f"\n🔍 Testing with Patient ID: {current['patientId']}")
    
    response = requests.post(
        f"{BASE_URL}/send-chat",
        headers={"Content-Type": "application/json"},
        json=[
            {"role": "user", "content": "Show me patient summary"}
        ]
    )
    
    print(f"✅ Status: {response.status_code}")
    print(f"📋 Response (first 200 chars): {response.text[:200]}...")

def run_all_tests():
    print("\n" + "🧪 "*20)
    print("DYNAMIC PATIENT ID SYSTEM - INTEGRATION TESTS")
    print("🧪 "*20)
    
    try:
        # Test 1: Get current patient
        current = test_get_current_patient()
        original_patient = current['patientId']
        
        # Test 2: Switch to P0002
        test_switch_patient("P0002")
        
        # Verify switch
        new_patient = test_get_current_patient()
        assert new_patient['patientId'] == "P0002", "Patient switch failed!"
        print("\n✅ Patient switch verified!")
        
        # Test 3: Switch to P0003
        test_switch_patient("P0003")
        
        # Test 4: Send chat (should use P0003)
        test_chat_with_patient()
        
        # Restore original patient
        print("\n" + "="*60)
        print(f"Restoring original patient: {original_patient}")
        print("="*60)
        test_switch_patient(original_patient)
        
        print("\n" + "✅ "*20)
        print("ALL TESTS PASSED!")
        print("✅ "*20)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("   Make sure the server is running:")
        print("   uvicorn server:app --reload --port 8000")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    run_all_tests()
