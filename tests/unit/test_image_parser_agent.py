import pytest
import pathlib
from google.genai import types
from google.adk.runners import InMemoryRunner
from app.agent import app

@pytest.mark.asyncio
async def test_image_pipeline():
    """
    Tests the pipeline end-to-end using an actual CT scan slice image.
    The Gemini 2.5 Flash model will visually extract the text/findings from the image.
    """
    runner = InMemoryRunner(app=app)
    
    # Load the Medical Image
    image_path = pathlib.Path(__file__).parent.parent / "testdata" / "chest_ct_scan_slice_1782576817200.png"
    
    if not image_path.exists():
        pytest.skip(f"Image not found at {image_path}")

    image_part = types.Part.from_bytes(data=image_path.read_bytes(), mime_type="image/png")
    
    # We ask the first agent to process this image
    text_prompt = types.Part.from_text(text="Analyze this CT scan slice, extract the medical report text visible in it, and process it through the pipeline.")

    # Initialize Session and Send Message
    session = await runner.session_service.create_session(app_name=app.name, user_id='test_image_user')
    
    async for _ in runner.run_async(
        user_id='test_image_user', 
        session_id=session.id, 
        new_message=types.Content(role='user', parts=[image_part, text_prompt])
    ): 
        pass
    
    session = await runner.session_service.get_session(session_id=session.id, app_name=app.name, user_id=session.user_id)
    # Retrieve final output states to verify the pipeline processed the image
    parsed_report = session.state.get("parsed_report")
    assert parsed_report is not None, "Report should have been visually parsed"
    
    extracted_findings = session.state.get("extracted_findings")
    assert extracted_findings is not None, "Findings should have been extracted"
    
    audit = session.state.get("audit_outputs")
    assert audit is not None, "Audit outputs should be generated"
    assert audit["timeline_aligned"] in ["PASSED", "FAILED"]
