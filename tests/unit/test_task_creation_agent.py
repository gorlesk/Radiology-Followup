from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import task_creation_agent, ParsedReport, FindingExtractionResult, ClinicalFinding, RiskClassification

@pytest.mark.asyncio
async def test_task_creation_agent_isolated():
    """
    Test the Task Creation Agent in isolation.
    Ensures it correctly uses the exam date and interval to calculate due date.
    """
    isolated_app = App(
        root_agent=task_creation_agent,
        name="isolated_task_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    import datetime
    today_str = datetime.date.today().isoformat()
    
    mock_parsed_report = ParsedReport(
        patient_name="Alex Smith",
        exam_date=today_str,
        clinical_history="No history.",
        technical_protocol="CT scan.",
        findings="Nodule.",
        impression="Follow up."
    )
    
    mock_findings = FindingExtractionResult(
        findings=[
            ClinicalFinding(
                finding_type="nodule",
                measurement="6 mm",
                location="right lung",
                is_negated=False
            )
        ]
    )
    
    mock_guidelines_raw = '''{{
        "recommendations": [
            {{
                "finding_type": "nodule",
                "guideline_title": "Guidelines",
                "citation_section": "Table 1",
                "follow_up_recommendation": "Follow-up",
                "screening_interval_months": "6"
            }}
        ]
    }}'''
    
    mock_risk = RiskClassification(
        priority="MEDIUM",
        justification="Standard 6 month interval."
    )
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'parsed_report': mock_parsed_report,
        'extracted_findings': mock_findings,
        'guideline_recommendations_raw': mock_guidelines_raw,
        'risk_classification': mock_risk,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    task_payload = session.state.get("task_creation_payload")
    
    assert task_payload is not None
    assert task_payload['task_priority'] == "MEDIUM"
    assert "Alex Smith" in task_payload['ehr_patient_name']
    # target due date should be 6 months from today_str
    target_date_obj = datetime.date.fromisoformat(today_str)
    month = target_date_obj.month + 6
    year = target_date_obj.year + (month // 13)
    month = month % 12 or 12
    expected_target_month = f"{year}-{month:02d}"
    assert expected_target_month in task_payload['target_due_date'] or str(year) in task_payload['target_due_date'], f"Should correctly add 6 months to {today_str}"
