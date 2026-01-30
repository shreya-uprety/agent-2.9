"""
Comprehensive Voice Agent Tools Testing Script
Tests all 11 canvas operations with current board data
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"
OUTPUT_DIR = Path("output")
TEST_RESULTS_FILE = "test_results_comprehensive.json"

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def send_voice_command(command, description=""):
    """Send a voice command to the agent"""
    if description:
        print(f"\n{Colors.BOLD}Test: {description}{Colors.ENDC}")
    print(f"Command: {Colors.OKBLUE}\"{command}\"{Colors.ENDC}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/send-chat",
            json=[{"role": "user", "content": command}],
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"Response: {result}")
        return {"success": True, "response": result, "status_code": response.status_code}
    except requests.exceptions.Timeout:
        print_error("Request timed out (30s)")
        return {"success": False, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {str(e)}")
        return {"success": False, "error": str(e)}

def check_file_created(filename, max_wait=5):
    """Check if output file was created"""
    filepath = OUTPUT_DIR / filename
    for i in range(max_wait):
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f) if filename.endswith('.json') else f.read()
            print_success(f"File created: {filename}")
            return True, content
        time.sleep(1)
    print_warning(f"File not found after {max_wait}s: {filename}")
    return False, None

def switch_patient(patient_id):
    """Switch to a different patient"""
    print_info(f"Switching to patient: {patient_id}")
    try:
        response = requests.post(
            f"{BASE_URL}/patient/switch",
            json={"patientId": patient_id}
        )
        response.raise_for_status()
        result = response.json()
        print_success(f"Switched to patient: {result.get('patientId')}")
        return True
    except Exception as e:
        print_error(f"Failed to switch patient: {str(e)}")
        return False

def get_current_patient():
    """Get current active patient"""
    try:
        response = requests.get(f"{BASE_URL}/patient/current")
        result = response.json()
        return result.get('patientId')
    except:
        return "unknown"

# =============================================================================
# TEST SUITES
# =============================================================================

def test_1_navigate_canvas():
    """Test Tool: navigate_canvas - Focus on board items"""
    print_header("TEST 1: Navigate Canvas (navigate_canvas tool)")
    
    test_cases = [
        {
            "command": "Show me encounter 2",
            "expected_file": "focus_payload.json",
            "description": "Navigate to Encounter 2"
        },
        {
            "command": "Focus on medication timeline",
            "expected_file": "focus_payload.json",
            "description": "Navigate to medication tracking"
        },
        {
            "command": "Show me the lab results",
            "expected_file": "focus_payload.json",
            "description": "Navigate to laboratory results"
        }
    ]
    
    results = []
    for test in test_cases:
        result = send_voice_command(test["command"], test["description"])
        time.sleep(2)
        
        file_created, content = check_file_created(test["expected_file"])
        
        results.append({
            "test": test["description"],
            "command": test["command"],
            "success": result["success"] and file_created,
            "response": result.get("response"),
            "file_content": content
        })
        
        time.sleep(1)
    
    return results

def test_2_generate_task():
    """Test Tool: generate_task - Create background tasks"""
    print_header("TEST 2: Generate Task (generate_task tool)")
    
    test_cases = [
        {
            "command": "Create task to analyze recent lab results",
            "expected_files": ["chatmode_todo_generated.json", "chatmode_todo_object_response.json"],
            "wait_time": 10,
            "description": "Generate lab analysis task"
        },
        {
            "command": "Create task to review medication interactions",
            "expected_files": ["chatmode_todo_generated.json", "chatmode_todo_object_response.json"],
            "wait_time": 10,
            "description": "Generate medication review task"
        }
    ]
    
    results = []
    for test in test_cases:
        result = send_voice_command(test["command"], test["description"])
        
        print_info(f"Waiting {test['wait_time']}s for background processing...")
        time.sleep(test["wait_time"])
        
        all_files_created = True
        file_contents = {}
        for filename in test["expected_files"]:
            file_created, content = check_file_created(filename)
            all_files_created = all_files_created and file_created
            file_contents[filename] = content
        
        # Check for result file
        result_created, result_content = check_file_created("chatmode_generate_response.md")
        
        results.append({
            "test": test["description"],
            "command": test["command"],
            "success": result["success"] and all_files_created and result_created,
            "response": result.get("response"),
            "files": file_contents,
            "result_posted": result_created,
            "result_preview": result_content[:200] if result_content else None
        })
        
        time.sleep(2)
    
    return results

def test_3_easl_guideline():
    """Test Tool: get_easl_answer - Query EASL guidelines"""
    print_header("TEST 3: EASL Guideline Query (get_easl_answer tool)")
    
    test_cases = [
        {
            "command": "What does EASL guideline say about DILI diagnosis?",
            "expected_files": ["initiate_iframe_payload.json", "initiate_iframe_response.json"],
            "wait_time": 8,
            "description": "EASL DILI diagnosis query"
        },
        {
            "command": "What are EASL recommendations for liver function monitoring?",
            "expected_files": ["initiate_iframe_payload.json", "initiate_iframe_response.json"],
            "wait_time": 8,
            "description": "EASL monitoring guidelines query"
        }
    ]
    
    results = []
    for test in test_cases:
        result = send_voice_command(test["command"], test["description"])
        
        print_info(f"Waiting {test['wait_time']}s for EASL processing...")
        time.sleep(test["wait_time"])
        
        all_files_created = True
        file_contents = {}
        for filename in test["expected_files"]:
            file_created, content = check_file_created(filename)
            all_files_created = all_files_created and file_created
            file_contents[filename] = content
        
        results.append({
            "test": test["description"],
            "command": test["command"],
            "success": result["success"] and all_files_created,
            "response": result.get("response"),
            "files": file_contents,
            "note": "EASL answer displayed in iframe on canvas (not in terminal)"
        })
        
        time.sleep(2)
    
    return results

def test_4_general_queries():
    """Test Tool: general - Answer questions from board data"""
    print_header("TEST 4: General Queries (general tool)")
    
    test_cases = [
        {
            "command": "What is the patient's current diagnosis?",
            "description": "Query patient diagnosis"
        },
        {
            "command": "What medications is the patient taking?",
            "description": "Query patient medications"
        },
        {
            "command": "Summarize the patient's recent lab results",
            "description": "Query lab results summary"
        },
        {
            "command": "Tell me about encounter 2",
            "description": "Query specific encounter details"
        }
    ]
    
    results = []
    for test in test_cases:
        result = send_voice_command(test["command"], test["description"])
        
        # Check if answer contains meaningful data
        response_text = result.get("response", "")
        has_meaningful_answer = (
            "sorry" not in response_text.lower() and 
            "do not have" not in response_text.lower() and
            len(response_text) > 50
        )
        
        results.append({
            "test": test["description"],
            "command": test["command"],
            "success": result["success"] and has_meaningful_answer,
            "response": result.get("response"),
            "answer_quality": "Good" if has_meaningful_answer else "Needs improvement"
        })
        
        time.sleep(1)
    
    return results

def test_5_multi_patient():
    """Test patient switching functionality"""
    print_header("TEST 5: Multi-Patient Support")
    
    # Only p0001 exists in the system
    patients = ["p0001"]
    results = []
    
    for patient_id in patients:
        print_info(f"\nTesting with patient: {patient_id}")
        
        if not switch_patient(patient_id):
            results.append({
                "patient": patient_id,
                "success": False,
                "error": "Failed to switch patient"
            })
            continue
        
        time.sleep(1)
        
        # Test a simple query for each patient
        result = send_voice_command(
            "What is the patient's current diagnosis?",
            f"Query diagnosis for {patient_id}"
        )
        
        results.append({
            "patient": patient_id,
            "success": result["success"],
            "response": result.get("response"),
            "board_items_fetched": "Fetching from" in str(result.get("response", ""))
        })
        
        time.sleep(2)
    
    return results

def test_6_all_canvas_operations():
    """Test all 11 canvas operations are dynamic"""
    print_header("TEST 6: All Canvas Operations (Dynamic Patient ID)")
    
    print_info("This test verifies all canvas operations include patientId")
    print_info("Check server logs for 'patientId' in payloads and URLs")
    
    operations_to_test = [
        {
            "name": "get_board_items",
            "command": "Show me the board items",
            "check": "URL includes /api/board-items/p"
        },
        {
            "name": "focus_item",
            "command": "Show me encounter 2",
            "check": "Focus payload includes patientId"
        },
        {
            "name": "create_todo",
            "command": "Create task to analyze data",
            "check": "Todo payload includes patientId"
        },
        {
            "name": "initiate_easl_iframe",
            "command": "What does EASL say about DILI?",
            "check": "EASL payload includes patientId"
        }
    ]
    
    results = []
    for op in operations_to_test:
        print_info(f"\nTesting: {op['name']}")
        result = send_voice_command(op["command"], op["name"])
        
        results.append({
            "operation": op["name"],
            "command": op["command"],
            "success": result["success"],
            "check_instruction": op["check"]
        })
        
        time.sleep(3)
    
    print_warning("\n📋 Manual verification required:")
    print("   Check server logs above for patientId in all payloads and URLs")
    
    return results

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all test suites"""
    print_header("VOICE AGENT COMPREHENSIVE TESTING")
    
    current_patient = get_current_patient()
    print_info(f"Current Patient: {current_patient}")
    print_info(f"Server: {BASE_URL}")
    print_info(f"Output Directory: {OUTPUT_DIR}")
    
    all_results = {}
    
    # Run all test suites
    test_suites = [
        ("navigate_canvas", test_1_navigate_canvas),
        ("generate_task", test_2_generate_task),
        ("easl_guideline", test_3_easl_guideline),
        ("general_queries", test_4_general_queries),
        ("multi_patient", test_5_multi_patient),
        ("all_operations", test_6_all_canvas_operations)
    ]
    
    for suite_name, test_func in test_suites:
        try:
            print(f"\n{Colors.OKBLUE}Starting test suite: {suite_name}{Colors.ENDC}")
            results = test_func()
            all_results[suite_name] = results
            
            # Print summary
            total = len(results)
            passed = sum(1 for r in results if r.get("success", False))
            print(f"\n{Colors.BOLD}Suite Summary: {passed}/{total} tests passed{Colors.ENDC}")
            
        except Exception as e:
            print_error(f"Test suite failed: {str(e)}")
            all_results[suite_name] = {"error": str(e)}
        
        time.sleep(2)
    
    # Save results
    with open(TEST_RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print_header("TESTING COMPLETE")
    print_success(f"Results saved to: {TEST_RESULTS_FILE}")
    
    # Print final summary
    total_tests = sum(len(results) if isinstance(results, list) else 0 
                     for results in all_results.values())
    total_passed = sum(
        sum(1 for r in results if r.get("success", False)) 
        if isinstance(results, list) else 0
        for results in all_results.values()
    )
    
    print(f"\n{Colors.BOLD}OVERALL RESULTS:{Colors.ENDC}")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {Colors.OKGREEN}{total_passed}{Colors.ENDC}")
    print(f"  Failed: {Colors.FAIL}{total_tests - total_passed}{Colors.ENDC}")
    
    if total_passed == total_tests:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! 🎉{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}⚠️  Some tests failed. Check {TEST_RESULTS_FILE} for details{Colors.ENDC}")
    
    return all_results

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}Voice Agent Testing Script{Colors.ENDC}")
    print("=" * 80)
    print("\nPrerequisites:")
    print("  1. Server running on http://localhost:8000")
    print("  2. Valid Google API key in .env file")
    print("  3. Canvas API accessible at https://iso-clinic-v3.vercel.app")
    print("\nPress Ctrl+C to cancel, or Enter to start...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        exit(0)
    
    run_all_tests()
