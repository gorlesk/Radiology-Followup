from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import finding_extraction_agent, ParsedReport, FindingExtractionResult

@pytest.mark.asyncio
async def test_finding_extraction_agent_isolated():
    """
    Test the Finding Extraction Agent in isolation.
    """
    # Create an app just for this agent to test it in isolation
    isolated_app = App(
        root_agent=finding_extraction_agent,
        name="isolated_finding_extraction_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    # We create a mock ParsedReport to inject into the state 
    # since the agent's instruction expects {parsed_report} in the state.
    mock_parsed_report = ParsedReport(
        clinical_history="No symptoms.",
        technical_protocol="CT scan.",
        findings="A 3 cm mass is seen in the left lower lobe. No cyst.",
        impression="Suspicious 3 cm mass."
    )
    
    # Run the agent. We pass empty string as input since the agent gets its context 
    # from the state variables injected into the instruction.
    # To inject into state, we can use the `state` parameter of run_async if available,
    # or just rely on passing it as input and adjusting the agent's instruction slightly, 
    # but since it's expecting {parsed_report}, we will populate the initial state.
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'parsed_report': mock_parsed_report,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    extracted_findings = session.state.get("extracted_findings")
    
    # Validations
    assert extracted_findings is not None, "Extracted findings should be present in the state"
    assert isinstance(extracted_findings, dict)
    
    # Check for the primary finding (mass)
    mass_finding = next((f for f in extracted_findings['findings'] if "mass" in f["finding_type"].lower()), None)
    assert mass_finding is not None, "Should extract 'mass' finding"
    assert "3" in mass_finding["measurement"], "Should extract '3 cm' measurement"
    assert "left lower lobe" in mass_finding["location"].lower(), "Should extract anatomical location"
    assert mass_finding["is_negated"] is False, "Mass finding is not negated"
    
    # Check for negated finding (cyst)
    cyst_finding = next((f for f in extracted_findings['findings'] if "cyst" in f["finding_type"].lower()), None)
    if cyst_finding:
        assert cyst_finding["is_negated"] is True, "Cyst should be marked as negated"
