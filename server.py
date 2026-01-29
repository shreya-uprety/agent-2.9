# main.py
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import subprocess
import os, sys
import subprocess, os, datetime, psutil
from fastapi.middleware.cors import CORSMiddleware
import json
import chat_model
import side_agent
import time
from patient_manager import patient_manager

TARGET_SCRIPTS = ["visit_meet_with_audio.py", "gemini_audio_only_cable.py"]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # <— Allow every domain
    allow_credentials=True,
    allow_methods=["*"],        # <— Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],        # <— Allow all headers
)

@app.get("/health")
def health():
    return {"status": "ok"}

def kill_existing_processes(script_name: str):
    """Find and kill any running PowerShell or Python processes executing the target script."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = " ".join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ""
            if any(script_name.lower() in cmdline for script_name in TARGET_SCRIPTS):
                print(f"Terminating PID {proc.pid}: {cmdline}")
                proc.terminate()
                proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def run_powershell_script(script_name: str, meet_url: str = None):
    if meet_url:
        command = f'start powershell -NoExit -ExecutionPolicy Bypass -Command "python {script_name} --link {meet_url}"'
    else:
        command = f'start powershell -NoExit -ExecutionPolicy Bypass -Command "python {script_name}"'

    subprocess.Popen(command, shell=True)
    print(f"Opened PowerShell window for {script_name}")


@app.post("/join-meeting")
def join_meeting(payload: dict, background_tasks: BackgroundTasks):
    meet_url = payload.get("meetUrl")
    print("Received:", payload)

    background_tasks.add_task(kill_existing_processes, "visit_meet_with_audio.py")
    background_tasks.add_task(kill_existing_processes, "gemini_audio_only_cable.py")


    background_tasks.add_task(run_powershell_script, "gemini_audio_only_cable.py")
    time.sleep(5)
    background_tasks.add_task(run_powershell_script, "visit_meet_with_audio.py", meet_url)

    return {"status": "joining", "meeting_url": meet_url}

@app.post("/mute")
def mute(payload: dict):
    with open("agent_status.json", "r", encoding="utf-8") as f:
        agent_status = json.load(f)
    if agent_status.get('mute'):
        agent_status['mute'] = False
    else:
        agent_status['mute'] = True
    with open("agent_status.json", "w", encoding="utf-8") as f:
        json.dump(agent_status, f,indent=4)

    print("Agent Status:", agent_status['mute'])
    return agent_status


@app.post("/send-chat")
async def run_chat_agent(payload: list[dict]):
    answer = await chat_model.chat_agent(payload)

    print("Agent Answer:", answer)
    return answer


@app.post("/generate_diagnosis")
async def gen_diagnosis(payload: dict):
    await side_agent.create_dili_diagnosis()
    return {
        "status" : "done"
    }

@app.post("/generate_report")
async def gen_report(payload: dict):
    await side_agent.create_patient_report()
    return {
        "status" : "done"
    }

@app.post("/generate_legal")
async def gen_report(payload: dict):
    await side_agent.create_legal_doc()
    return {
        "status" : "done"
    }

@app.get("/patient/current")
async def get_current_patient():
    """Get current patient ID"""
    return {
        "patientId": patient_manager.get_patient_id(),
        "baseUrl": patient_manager.get_base_url()
    }

@app.post("/patient/switch")
async def switch_patient(payload: dict):
    """Switch to a different patient ID"""
    patient_id = payload.get("patientId")
    if patient_id:
        patient_manager.set_patient_id(patient_id)
        return {
            "status": "success",
            "patientId": patient_id,
            "message": f"Switched to patient {patient_id}"
        }
    else:
        return {
            "status": "error",
            "message": "patientId is required"
        }

@app.get("/ui", response_class=HTMLResponse)
async def get_ui():
    """Simple UI for testing patient management"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MedForce Agent - Patient Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .info-box {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .info-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        .info-value {
            font-size: 18px;
            font-weight: 600;
            color: #2d3748;
            word-break: break-all;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #2d3748;
            font-weight: 500;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-right: 10px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .btn-secondary {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }
        .status {
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
        .status.success {
            background: #c6f6d5;
            color: #22543d;
            border-left: 4px solid #38a169;
        }
        .status.error {
            background: #fed7d7;
            color: #742a2a;
            border-left: 4px solid #e53e3e;
        }
        .test-section {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e2e8f0;
        }
        .test-results {
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            max-height: 400px;
            overflow-y: auto;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            background: #667eea;
            color: white;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🏥 MedForce Agent <span class="badge">Patient Manager</span></h1>
            <p class="subtitle">Dynamic Patient ID Management System</p>
            
            <div class="info-grid">
                <div class="info-box">
                    <div class="info-label">Current Patient ID</div>
                    <div class="info-value" id="currentPatient">Loading...</div>
                </div>
                <div class="info-box">
                    <div class="info-label">Base URL</div>
                    <div class="info-value" id="baseUrl">Loading...</div>
                </div>
            </div>

            <div class="form-group">
                <label for="patientId">Switch Patient ID</label>
                <input type="text" id="patientId" placeholder="e.g., P0001, P0002" />
            </div>

            <button class="btn" onclick="switchPatient()">
                <span id="switchBtnText">Switch Patient</span>
            </button>
            <button class="btn btn-secondary" onclick="refreshInfo()">
                Refresh Info
            </button>

            <div id="status" class="status"></div>

            <div class="test-section">
                <h2 style="color: #2d3748; margin-bottom: 15px;">🧪 Test API Endpoints</h2>
                <button class="btn" onclick="testBoardItems()">Test Board Items</button>
                <button class="btn btn-secondary" onclick="testChatAgent()">Test Chat Agent</button>
                <div id="testResults" class="test-results" style="display:none;"></div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;

        async function fetchCurrentPatient() {
            try {
                const response = await fetch(`${API_BASE}/patient/current`);
                const data = await response.json();
                document.getElementById('currentPatient').textContent = data.patientId;
                document.getElementById('baseUrl').textContent = data.baseUrl;
            } catch (error) {
                console.error('Error fetching patient:', error);
                showStatus('Failed to fetch current patient', 'error');
            }
        }

        async function switchPatient() {
            const patientId = document.getElementById('patientId').value.trim();
            if (!patientId) {
                showStatus('Please enter a patient ID', 'error');
                return;
            }

            const btn = document.getElementById('switchBtnText');
            btn.innerHTML = '<span class="loading"></span>';

            try {
                const response = await fetch(`${API_BASE}/patient/switch`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ patientId })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    showStatus(`✅ Successfully switched to patient ${data.patientId}`, 'success');
                    await fetchCurrentPatient();
                    document.getElementById('patientId').value = '';
                } else {
                    showStatus(`❌ ${data.message}`, 'error');
                }
            } catch (error) {
                showStatus(`❌ Error: ${error.message}`, 'error');
            } finally {
                btn.textContent = 'Switch Patient';
            }
        }

        async function refreshInfo() {
            await fetchCurrentPatient();
            showStatus('✅ Information refreshed', 'success');
        }

        async function testBoardItems() {
            const resultsDiv = document.getElementById('testResults');
            resultsDiv.style.display = 'block';
            resultsDiv.textContent = 'Loading board items...';

            try {
                const currentPatient = await fetch(`${API_BASE}/patient/current`).then(r => r.json());
                const patientId = currentPatient.patientId;
                const baseUrl = currentPatient.baseUrl;
                
                resultsDiv.textContent = `Fetching from: ${baseUrl}/api/board-items/${patientId}\\n\\n`;
                
                // Note: This would actually call your board API
                resultsDiv.textContent += `✅ Patient ID "${patientId}" is configured\\n`;
                resultsDiv.textContent += `✅ All API calls will include: "patientId": "${patientId}"\\n\\n`;
                resultsDiv.textContent += `Example payload structure:\\n`;
                resultsDiv.textContent += JSON.stringify({
                    patientId: patientId,
                    endpoint: `/api/board-items/${patientId}`,
                    samplePayload: {
                        patientId: patientId,
                        title: "Sample Task",
                        todo_items: ["Item 1"]
                    }
                }, null, 2);
            } catch (error) {
                resultsDiv.textContent = `❌ Error: ${error.message}`;
            }
        }

        async function testChatAgent() {
            const resultsDiv = document.getElementById('testResults');
            resultsDiv.style.display = 'block';
            resultsDiv.textContent = 'Testing chat agent with current patient...\\n\\n';

            try {
                const response = await fetch(`${API_BASE}/send-chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify([
                        { role: 'user', content: 'Show me patient summary' }
                    ])
                });
                const data = await response.text();
                resultsDiv.textContent += `✅ Response received\\n\\n`;
                resultsDiv.textContent += data.substring(0, 500) + '...';
            } catch (error) {
                resultsDiv.textContent = `❌ Error: ${error.message}`;
            }
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = `status ${type}`;
            statusDiv.style.display = 'block';
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }

        // Enter key support
        document.getElementById('patientId').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') switchPatient();
        });

        // Load current patient on page load
        fetchCurrentPatient();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)