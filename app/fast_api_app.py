"""
================================================================================
 File Name:    fast_api_app.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   FastAPI implementation for serving ADK agents. Handles OpenTelemetry 
   integration, direct DICOM parsing endpoints, and structured feedback logging 
   from the UI.
================================================================================
"""

import os

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=False,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)
app.title = "radiology-followup"
app.description = "API for interacting with the Agent radiology-followup"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}

from fastapi import UploadFile, File
from fastapi.responses import Response

@app.post("/api/convert-dicom")
async def convert_dicom(file: UploadFile = File(...)):
    import pydicom
    import io
    from PIL import Image
    import numpy as np

    contents = await file.read()
    dicom_data = pydicom.dcmread(io.BytesIO(contents))
    pixel_array = dicom_data.pixel_array
    
    patient_id = ""
    real_patient_id = getattr(dicom_data, "PatientID", None)
    if not real_patient_id or str(real_patient_id).strip() == "":
        real_patient_id = getattr(dicom_data, "PatientName", None)
        
    if real_patient_id and str(real_patient_id).strip() != "":
        extracted_id = str(real_patient_id).strip()
        if any(char.isdigit() for char in extracted_id):
            if not extracted_id.upper().startswith("P"):
                patient_id = f"P-{extracted_id}"
            else:
                patient_id = extracted_id
                
    modality = getattr(dicom_data, "Modality", "")
    if modality:
        modality = str(modality).strip()
        if modality == "OT":
            if file.filename and "mr" in file.filename.lower():
                modality = "MR"
            else:
                modality = "CT"
        
    age = getattr(dicom_data, "PatientAge", "")
    sex = getattr(dicom_data, "PatientSex", "")
    age_gender = ""
    if age or sex:
        age_str = str(age).strip() if age else "Unknown"
        if age_str.endswith('Y'):
            age_str = age_str[:-1].lstrip('0')
            if not age_str: age_str = "0"
        sex_str = str(sex).strip() if sex else "Unknown"
        if sex_str == 'M': sex_str = 'Male'
        elif sex_str == 'F': sex_str = 'Female'
        age_gender = f"{age_str} / {sex_str}"
    
    if pixel_array.max() > 0:
        pixel_array = pixel_array - pixel_array.min()
        pixel_array = (pixel_array / pixel_array.max()) * 255.0
    pixel_array = pixel_array.astype(np.uint8)
    
    image = Image.fromarray(pixel_array)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    
    headers = {}
    if patient_id:
        headers["X-Patient-ID"] = patient_id
    if modality:
        headers["X-Modality"] = modality
    if age_gender:
        headers["X-Age-Gender"] = age_gender
        
    return Response(content=img_byte_arr.getvalue(), media_type="image/png", headers=headers)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("radiology_interactive_workflow.html")

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
