from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import (
    communication_agent, 
    ParsedReport, 
    FindingExtractionResult, 
    ClinicalFinding, 
    RiskClassification, 
    TaskCreationPayload
)

@pytest.mark.asyncio
async def test_communication_agent_isolated():
    """
    Test the Communication Agent in isolation.
    Ensures it correctly generates a clinician note and a patient-friendly explanation.
    """
    isolated_app = App(
        root_agent=communication_agent,
        name="isolated_communication_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    # Mocking the pipeline state
    mock_parsed_report = ParsedReport(
        patient_name="Alex Smith",
        exam_date="2025-01-01",
        clinical_history="Cough.",
        technical_protocol="CT scan.",
        findings="7 mm nodule.",
        impression="Recommend CT follow up."
    )
    
    mock_findings = FindingExtractionResult(
        findings=[
            ClinicalFinding(
                finding_type="nodule",
                measurement="7 mm",
                location="right upper lobe",
                is_negated=False
            )
        ]
    )
    
    mock_guidelines_raw = '''{{
        "recommendations": [
            {{
                "finding_type": "nodule",
                "guideline_title": "Fleischner Society",
                "citation_section": "Table 1",
                "follow_up_recommendation": "Follow-up CT at 6-12 months",
                "screening_interval_months": "6"
            }}
        ]
    }}'''
    
    mock_risk = RiskClassification(
        priority="MEDIUM",
        justification="Standard 6-12 month interval for 7mm nodule."
    )
    
    mock_task = TaskCreationPayload(
        task_priority="MEDIUM",
        target_due_date="2025-07-01",
        reference_clinical_findings="7 mm nodule right upper lobe",
        ehr_patient_name="Alex Smith"
    )
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'parsed_report': mock_parsed_report,
        'extracted_findings': mock_findings,
        'guideline_recommendations_raw': mock_guidelines_raw,
        'risk_classification': mock_risk,
        'task_creation_payload': mock_task,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    comm_outputs = session.state.get("communication_outputs")
    
    assert comm_outputs is not None, "Communication outputs should be present in state"
    assert "clinician_note" in comm_outputs, "Should generate a clinician note"
    assert "patient_friendly_explanation" in comm_outputs, "Should generate a patient explanation"
    
    assert "7" in comm_outputs['clinician_note'] and "mm" in comm_outputs['clinician_note'], "Clinician note should contain the finding"
    assert "Fleischner" in comm_outputs['clinician_note'], "Clinician note should cite the guideline"
    
    # Patient explanation should use simple terms
    assert "small spot" in comm_outputs['patient_friendly_explanation'].lower() or "nodule" in comm_outputs['patient_friendly_explanation'].lower()
    
    # Check for either the interval OR the exact date output (e.g. 2025-07-01 -> July)
    assert any(word in comm_outputs['patient_friendly_explanation'].lower() for word in ["month", "july", "2025"]), "Should mention the timeframe or exact date to the patient"
