"""
================================================================================
 File Name:    test_report_parser_agent.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Unit tests for the Report Parser Agent, verifying extraction of
   clinical history and findings from unstructured text narratives.
================================================================================
"""

from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import report_parser_agent, ParsedReport

@pytest.mark.asyncio
async def test_report_parser_agent_isolated():
    """
    Test the Report Parser Agent in isolation.
    """
    isolated_app = App(
        root_agent=report_parser_agent,
        name="isolated_report_parser_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    sample_report = """
    Patient: John Doe, Age: 45, Gender: M
    Exam Date: 2026-06-27
    CLINICAL HISTORY: 
    Patient complains of chronic cough for 3 weeks. No fever.
    
    TECHNIQUE: 
    Non-contrast CT of the chest.
    
    FINDINGS: 
    A 7 mm pulmonary nodule is seen in the right upper lobe. 
    
    IMPRESSION: 
    1. 7 mm solid nodule in the right upper lobe. Recommend follow-up CT in 6-12 months.
    """
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id='test')
    async for _ in runner.run_async(user_id='test', session_id=session.id, new_message=types.Content(role='user', parts=[types.Part.from_text(text=sample_report)])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    parsed_report = session.state.get("parsed_report")
    
    assert parsed_report is not None
    assert isinstance(parsed_report, dict)
    assert "John Doe" in parsed_report['patient_name']
    assert "2026" in parsed_report["exam_date"]
    assert "chronic cough" in parsed_report["clinical_history"].lower()
    assert "ct" in parsed_report["technical_protocol"].lower()
    assert "7 mm" in parsed_report['findings'].lower()
    assert "follow-up ct" in parsed_report["impression"].lower()
