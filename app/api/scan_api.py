"""
================================================================================
 File Name:    scan_api.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Exposes the primary API endpoint to run the ADK Multi-Agent radiology 
   pipeline. Orchestrates InMemoryRunner session states and synchronizes 
   outputs into the global dashboard state.
================================================================================
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from google.genai import types
from google.adk.runners import InMemoryRunner
from app.agent import app as agent_app

# Import the shared dashboard state to update the analytics
from app.api.dashboard_api import dashboard_stats

# Initialize the router for scan processing
router = APIRouter()

@router.post("/analyze-scan")
async def analyze_scan(
    file: UploadFile = File(...), 
    patient_id: str = Form("UNKNOWN"), 
    modality: str = Form("UNKNOWN"), 
    target: str = Form("UNKNOWN")
):
    """
    Accepts an uploaded image/DICOM, runs it through the agent pipeline,
    and returns synthesized findings, target dates, and updates the dashboard.
    """
    try:
        contents = await file.read()
        
        filename = file.filename.lower()
        mime_type = file.content_type or "image/png"
        
        # Add DICOM support
        if filename.endswith(".dcm") or mime_type == "application/dicom":
            import pydicom
            import io
            from PIL import Image
            import numpy as np
            
            dicom_data = pydicom.dcmread(io.BytesIO(contents))
            
            # Extract real patient ID if available and valid
            real_patient_id = getattr(dicom_data, "PatientID", None)
            if not real_patient_id or str(real_patient_id).strip() == "":
                real_patient_id = getattr(dicom_data, "PatientName", None)
                
            if real_patient_id and str(real_patient_id).strip() != "":
                extracted_id = str(real_patient_id).strip()
                if any(char.isdigit() for char in extracted_id):
                    # Format to look like dashboard P-XXXXX if it's just numbers or text
                    if not extracted_id.upper().startswith("P"):
                        patient_id = f"P-{extracted_id}"
                    else:
                        patient_id = extracted_id
                        
            dicom_modality = getattr(dicom_data, "Modality", None)
            if dicom_modality and str(dicom_modality).strip() != "":
                modality = str(dicom_modality).strip()
                if modality == "OT":
                    if file.filename and "mr" in file.filename.lower():
                        modality = "MR"
                    else:
                        modality = "CT"
                
            pixel_array = dicom_data.pixel_array
            
            # Normalize to 0-255 uint8 for PNG conversion
            if pixel_array.max() > 0:
                pixel_array = pixel_array - pixel_array.min()
                pixel_array = (pixel_array / pixel_array.max()) * 255.0
            pixel_array = pixel_array.astype(np.uint8)
            
            image = Image.fromarray(pixel_array)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            
            contents = img_byte_arr.getvalue()
            mime_type = "image/png"
            
        image_part = types.Part.from_bytes(data=contents, mime_type=mime_type)
        text_prompt = types.Part.from_text(text="Analyze this clinical image, extract findings, and process it through the pipeline.")
        
        runner = InMemoryRunner(app=agent_app)
        session = await runner.session_service.create_session(app_name=agent_app.name, user_id='clinician_1')
        
        # Run the agent pipeline
        async for _ in runner.run_async(
            user_id='clinician_1', 
            session_id=session.id, 
            new_message=types.Content(role='user', parts=[image_part, text_prompt])
        ):
            pass
            
        session = await runner.session_service.get_session(session_id=session.id, app_name=agent_app.name, user_id=session.user_id)
        
        # Gather outputs from state
        comm_outputs = session.state.get("communication_outputs", {})
        task_payload = session.state.get("task_creation_payload", {})
        risk_class = session.state.get("risk_classification", {})
        audit = session.state.get("audit_outputs", {})
        
        priority = risk_class.get("priority", "UNKNOWN")
        target_date = task_payload.get("target_due_date", "Unknown")
        
        # Fail-safes for targets
        if priority == "LOW" or "unknown" in target_date.lower() or "n/a" in target_date.lower() or not target_date.strip():
            target_date = "Routine (1 Year)"
        
        # Update shared state
        dashboard_stats["totalScans"] += 1
        dashboard_stats["uniquePatients"].add(patient_id)
        if priority == "HIGH":
            dashboard_stats["highPriority"] += 1
            
        dashboard_stats["recentPatients"].insert(0, {
            "patientId": patient_id,
            "modality": modality,
            "target": target,
            "priority": priority,
            "targetDate": target_date,
            "clinicianNote": comm_outputs.get("clinician_note", "Processing failed."),
            "patientExplanation": comm_outputs.get("patient_friendly_explanation", "Processing failed."),
            "sampleKey": "chest_ct" if "chest" in target.lower() else "liver_mr" if "liver" in target.lower() else None
        })
        dashboard_stats["recentPatients"] = dashboard_stats["recentPatients"][:10]
        
        return {
            "clinicianNote": comm_outputs.get("clinician_note", "Processing failed."),
            "patientExplanation": comm_outputs.get("patient_friendly_explanation", "Processing failed."),
            "targetDate": target_date,
            "priority": risk_class.get("priority", "UNKNOWN"),
            "audit": audit
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
