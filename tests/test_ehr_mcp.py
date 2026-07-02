"""
================================================================================
 File Name:    test_ehr_mcp.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Simulates Model Context Protocol (MCP) interactions with a mock EHR
   system to test read and write actions.
================================================================================
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ehr_mcp_server import EHR_MCP_Server

def run_simulated_mcp_test():
    print("\n" + "="*50)
    print(" INITIATING EHR MCP SERVER TEST")
    print("="*50)
    
    # 1. Initialize the Server
    server = EHR_MCP_Server(
        fhir_api_endpoint="https://fhir.mockhospital.com/api/v1", 
        auth_token="mock_oauth_token_12345"
    )
    
    print("\n[TEST 1] Testing Read-Only History Extraction (Parser Agent Simulation)")
    history = server.get_patient_history(patient_id="P-93021")
    assert history["patient_id"] == "P-93021", "Failed to retrieve correct patient!"
    print(f"Success! Extracted History: {history}")
    
    print("\n[TEST 2] Testing Write-Action Note Injection (Communication Agent Simulation)")
    note_success = server.push_clinician_note(
        patient_id="P-93021", 
        note_text="Patient has a 7mm nodule. Routine follow-up scheduled.", 
        priority="HIGH"
    )
    assert note_success is True, "Failed to write note to EHR!"
    print(f"Success! Note successfully transmitted to the FHIR endpoint.")
    
    print("\n[TEST 3] Testing Write-Action Scheduling Ticket (Task Agent Simulation)")
    schedule_success = server.schedule_followup_task(
        patient_id="P-93021", 
        target_date="2026-12-01", 
        department="Radiology"
    )
    assert schedule_success is True, "Failed to schedule appointment in EHR!"
    print(f"Success! Calendar appointment dynamically inserted.")
    
    print("\n" + "="*50)
    print(" ALL MCP TOOLS PASSED VALIDATION")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_simulated_mcp_test()
