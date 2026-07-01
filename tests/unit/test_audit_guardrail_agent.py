from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import (
    audit_guardrail_agent, 
    ParsedReport, 
    FindingExtractionResult, 
    ClinicalFinding,
    TaskCreationPayload,
    CommunicationOutputs
)

@pytest.mark.asyncio
async def test_audit_guardrail_agent_isolated():
    """
    Test the Audit & Guardrail Agent in isolation.
    """
    isolated_app = App(
        root_agent=audit_guardrail_agent,
        name="isolated_audit_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    # Mock states
    mock_parsed_report = ParsedReport(
        patient_name="John Doe",
        exam_date="2026-01-01",
        clinical_history="No symptoms.",
        technical_protocol="CT",
        findings="7 mm nodule.",
        impression="Follow up in 6 months."
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
                "guideline_title": "Fleischner",
                "citation_section": "Table 1",
                "follow_up_recommendation": "Follow-up CT",
                "screening_interval_months": "6"
            }}
        ]
    }}'''
    
    mock_task = TaskCreationPayload(
        task_priority="MEDIUM",
        target_due_date="2026-07-01",
        reference_clinical_findings="7 mm nodule",
        ehr_patient_name="John Doe"
    )
    
    mock_comm = CommunicationOutputs(
        clinician_note="Patient has a 7 mm nodule. Recommending 6 month follow-up per Fleischner criteria.",
        patient_friendly_explanation="A small spot was found. Please come back in 6 months."
    )
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'parsed_report': mock_parsed_report,
        'extracted_findings': mock_findings,
        'guideline_recommendations_raw': mock_guidelines_raw,
        'task_creation_payload': mock_task,
        'communication_outputs': mock_comm,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    audit_outputs = session.state.get("audit_outputs")
    
    assert audit_outputs is not None
    assert "PASSED" in audit_outputs["timeline_aligned"]
    assert "PASSED" in audit_outputs["no_factual_discrepancies"]
    assert "PASSED" in audit_outputs["dates_correctly_calculated"]
