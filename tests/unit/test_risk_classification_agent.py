from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import risk_classification_agent, ParsedReport, FindingExtractionResult, ClinicalFinding

@pytest.mark.asyncio
async def test_risk_classification_agent_isolated():
    """
    Test the Risk Classification Agent in isolation by providing mocked context variables.
    """
    isolated_app = App(
        root_agent=risk_classification_agent,
        name="isolated_risk_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    mock_parsed_report = ParsedReport(
        patient_name="Jane Doe",
        exam_date="2026-06-20",
        clinical_history="No history.",
        technical_protocol="CT scan.",
        findings="A large 20 mm mass.",
        impression="Suspicious for malignancy."
    )
    
    mock_findings = FindingExtractionResult(
        findings=[
            ClinicalFinding(
                finding_type="mass",
                measurement="20 mm",
                location="left lung",
                is_negated=False
            )
        ]
    )
    
    # We simulate a 3-month recommendation for this large mass
    mock_guidelines_raw = '''{{
        "recommendations": [
            {{
                "finding_type": "mass",
                "guideline_title": "Guidelines",
                "citation_section": "Table 2",
                "follow_up_recommendation": "Tissue sampling or PET/CT",
                "screening_interval_months": "3"
            }}
        ]
    }}'''
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'parsed_report': mock_parsed_report,
        'extracted_findings': mock_findings,
        'guideline_recommendations_raw': mock_guidelines_raw,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    risk_classification = session.state.get("risk_classification")
    
    assert risk_classification is not None
    assert risk_classification['priority'] == "HIGH", "A 3-month interval with a 20mm mass should be classified as HIGH priority"
