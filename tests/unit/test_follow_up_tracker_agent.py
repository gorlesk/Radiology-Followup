"""
================================================================================
 File Name:    test_follow_up_tracker_agent.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Unit tests for the Follow-up Tracker Agent, checking initial
   scheduling state registration and escalation rules.
================================================================================
"""

from google.genai import types
import pytest
from google.adk.runners import InMemoryRunner
from google.adk.apps import App
from app.agent import (
    follow_up_tracker_agent, 
    TaskCreationPayload,
    RiskClassification,
    TrackerOutputs
)

@pytest.mark.asyncio
async def test_follow_up_tracker_agent_isolated():
    """
    Test the Follow-up Tracker Agent in isolation.
    Ensures it registers 'Pending' state, reminders, and escalation rules.
    """
    isolated_app = App(
        root_agent=follow_up_tracker_agent,
        name="isolated_tracker_app"
    )
    runner = InMemoryRunner(app=isolated_app)
    
    # Mocking the pipeline state
    mock_risk = RiskClassification(
        priority="MEDIUM",
        justification="Standard interval."
    )
    
    mock_task = TaskCreationPayload(
        task_priority="MEDIUM",
        target_due_date="2026-12-01",
        reference_clinical_findings="7 mm nodule",
        ehr_patient_name="Alex Smith"
    )
    
    session = await runner.session_service.create_session(app_name=isolated_app.name, user_id="test_user")
    
    state_delta = {
        'risk_classification': mock_risk,
        'task_creation_payload': mock_task,
    }
    async for _ in runner.run_async(user_id='test_user', session_id=session.id, state_delta=state_delta, new_message=types.Content(role='user', parts=[types.Part.from_text(text='start')])): pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=isolated_app.name, user_id=session.user_id)
    tracker_outputs = session.state.get("tracker_outputs")
    
    assert tracker_outputs is not None, "Tracker outputs should be present in state"
    assert ("scheduling_state" in tracker_outputs), "Should generate a scheduling state"
    assert ("calendar_reminders" in tracker_outputs), "Should generate calendar reminders"
    assert ("escalation_rules" in tracker_outputs), "Should generate escalation rules"
    assert tracker_outputs["scheduling_state"] == "Pending", "New tasks should be marked as Pending"
    assert len(tracker_outputs['calendar_reminders']) > 0, "Should register at least one calendar reminder"
    assert len(tracker_outputs['escalation_rules']) > 10, "Should specify clear escalation rules"
