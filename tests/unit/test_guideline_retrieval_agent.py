from google.genai import types
import pytest
import json
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import guideline_retrieval_agent, FindingExtractionResult, ClinicalFinding

@pytest.mark.asyncio
async def test_guideline_retrieval_agent_isolated():
    """
    Test the Guideline Retrieval Agent in isolation using mocked NER inputs.
    """
    isolated_app = App(
        root_agent=guideline_retrieval_agent,
        name="isolated_guideline_retrieval_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    # Mock finding extraction result to inject into the state
    mock_findings = FindingExtractionResult(
        findings=[
            ClinicalFinding(
                finding_type="solid pulmonary nodule",
                measurement="7 mm",
                location="right upper lobe",
                is_negated=False
            ),
            ClinicalFinding(
                finding_type="pleural effusion",
                measurement="",
                location="",
                is_negated=True
            )
        ]
    )
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    # Run agent
    state_delta = {
        'extracted_findings': mock_findings,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    guidelines_raw = session.state.get("guideline_recommendations_raw")
    
    assert guidelines_raw is not None, "Guideline recommendations should be present"
    
    try:
        # Strip potential markdown formatting
        if guidelines_raw.startswith("```json"):
            guidelines_raw = guidelines_raw.replace("```json", "").replace("```", "").strip()
        elif guidelines_raw.startswith("```"):
            guidelines_raw = guidelines_raw.replace("```", "").strip()
            
        guidelines_json = json.loads(guidelines_raw)
        recommendations = guidelines_json.get("recommendations", [])
        
        # We only expect 1 actionable finding, since pleural effusion is negated
        assert len(recommendations) == 1, "Should have exactly one recommendation for the actionable finding"
        
        rec = recommendations[0]
        assert "Fleischner Society" in rec.get("guideline_title", ""), "Should reference Fleischner criteria"
        assert "6-12" in str(rec.get("screening_interval_months", "")), "Should extract 6-12 interval"
        assert "Table 1" in rec.get("citation_section", ""), "Should extract Table 1 citation section"
    except json.JSONDecodeError:
        pytest.fail(f"Agent failed to return valid JSON. Output was: {guidelines_raw}")
