"""
================================================================================
 File Name:    test_agent.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Comprehensive tests for the primary ADK agent orchestration graph,
   ensuring correct sequential state handoffs.
================================================================================
"""

from google.genai import types
import pytest
import json
from google.adk.runners import InMemoryRunner
from app.agent import app, ParsedReport, FindingExtractionResult

@pytest.mark.asyncio
async def test_radiology_pipeline():
    """
    Test the sequential pipeline:
    Report Parser Agent -> Finding Extraction Agent -> Guideline Retrieval Agent
    """
    runner = InMemoryRunner(app=app)
    
    sample_report = """
    Patient: John Doe, Age: 45, Gender: M
    Exam Date: 2026-06-27
    CLINICAL HISTORY: 
    Patient complains of chronic cough for 3 weeks. No fever.
    
    TECHNIQUE: 
    Non-contrast CT of the chest. Dose modulation applied.
    
    FINDINGS: 
    Lungs: A 7 mm solid pulmonary nodule is seen in the right upper lobe. 
    Pleura: No pleural effusion or pneumothorax.
    Heart: Normal heart size.
    
    IMPRESSION: 
    1. 7 mm solid nodule in the right upper lobe. Recommend follow-up CT in 6-12 months.
    """
    
    # Run the pipeline
    session = await runner.session_service.create_session(app_name=app.name, user_id='test')
    async for _ in runner.run_async(user_id='test', session_id=session.id, new_message=types.Content(role='user', parts=[types.Part.from_text(text=sample_report)])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=app.name, user_id=session.user_id)
    # Retrieve outputs from state
    parsed_report = session.state.get("parsed_report")
    extracted_findings = session.state.get("extracted_findings")
    guidelines_raw = session.state.get("guideline_recommendations_raw")
    
    # Validate Report Parser Agent Output
    assert parsed_report is not None, "Parsed report should be present in the state"
    assert isinstance(parsed_report, dict)
    
    # Validate Finding Extraction Agent Output
    assert extracted_findings is not None, "Extracted findings should be present in the state"
    assert isinstance(extracted_findings, dict)
    assert len(extracted_findings['findings']) > 0, "Should have extracted at least one finding"
    
    # Validate Guideline Retrieval Agent Output
    assert guidelines_raw is not None, "Guideline recommendations should be present"
    
    try:
        # Strip potential markdown if the model mistakenly added it despite instructions
        if guidelines_raw.startswith("```json"):
            guidelines_raw = guidelines_raw.replace("```json", "").replace("```", "").strip()
        elif guidelines_raw.startswith("```"):
            guidelines_raw = guidelines_raw.replace("```", "").strip()
            
        guidelines_json = json.loads(guidelines_raw)
        recommendations = guidelines_json.get("recommendations", [])
        
        assert len(recommendations) > 0, "Should have at least one guideline recommendation"
        rec = recommendations[0]
        assert "Fleischner Society" in rec.get("guideline_title", ""), "Should reference Fleischner criteria"
        assert "6-12" in str(rec.get("screening_interval_months", "")), "Should extract interval"
        assert "Table 1" in rec.get("citation_section", ""), "Should extract citation section"
    except json.JSONDecodeError:
        pytest.fail(f"Agent failed to return valid JSON. Output was: {guidelines_raw}")
        
    # Validate Risk Classification Agent Output
    risk_classification = session.state.get("risk_classification")
    assert risk_classification is not None, "Risk classification should be present in the state"
    assert "priority" in risk_classification, "Should have priority assigned"
    assert risk_classification['priority'] in ["HIGH", "MEDIUM", "LOW"], "Priority should be HIGH, MEDIUM, or LOW"
    assert risk_classification['priority'] == "MEDIUM", "7mm pulmonary nodule with 6-12 month follow-up should be assigned MEDIUM priority"

    # Validate Task Creation Agent Output
    task_creation_payload = session.state.get("task_creation_payload")
    assert task_creation_payload is not None, "Task creation payload should be present in the state"
    assert "target_due_date" in task_creation_payload, "Should have target due date"
    assert "task_priority" in task_creation_payload, "Should have task priority"
    assert task_creation_payload['task_priority'] == "MEDIUM", "Task priority should match risk classification priority"
    assert "2026" in task_creation_payload['target_due_date'] or "2027" in task_creation_payload['target_due_date'], "Should contain calculated year"
    assert "John Doe" in task_creation_payload['ehr_patient_name'], "Patient name should be John Doe"

    # Validate Communication Agent Output
    comm_outputs = session.state.get("communication_outputs")
    assert comm_outputs is not None, "Communication outputs should be present in the state"
    assert "clinician_note" in comm_outputs, "Should have clinician note"
    assert "patient_friendly_explanation" in comm_outputs, "Should have patient friendly explanation"
    assert "7" in comm_outputs['clinician_note'] and "mm" in comm_outputs['clinician_note'], "Clinician note should mention 7 mm"
    assert any(word in comm_outputs['patient_friendly_explanation'].lower() for word in ["month", "2026", "2027", "december", "january"]), "Patient explanation should mention timeline or exact date"

    # Validate Follow-up Tracker Agent Output
    tracker_outputs = session.state.get("tracker_outputs")
    assert tracker_outputs is not None, "Tracker outputs should be present in the state"
    assert ("scheduling_state" in tracker_outputs), "Should have scheduling state"
    assert "Pending" in tracker_outputs['scheduling_state'], "New tasks should be marked as Pending"
    assert "calendar_reminders" in tracker_outputs, "Should have calendar reminders"
    assert "escalation_rules" in tracker_outputs, "Should have escalation rules"

    # Validate Audit & Guardrail Agent Output
    audit_outputs = session.state.get("audit_outputs")
    assert audit_outputs is not None, "Audit outputs should be present in the state"





    assert audit_outputs is not None, "Audit outputs should be present in the state"
    assert "timeline_aligned" in audit_outputs, "Should check timeline alignment"
    assert "no_factual_discrepancies" in audit_outputs, "Should check factual discrepancies"
    assert "dates_correctly_calculated" in audit_outputs, "Should check date calculations"

    assert "PASSED" in audit_outputs["timeline_aligned"], "Timeline alignment should pass"
    assert "PASSED" in audit_outputs["no_factual_discrepancies"], "Factual discrepancy check should pass"
    assert "PASSED" in audit_outputs["dates_correctly_calculated"], "Date calculation check should pass"
