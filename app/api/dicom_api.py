"""
================================================================================
 File Name:    dicom_api.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Exposes the DICOM conversion API. Handles extraction of critical patient 
   metadata (ID, Modality, Age, Sex) and transcodes raw medical pixel data 
   into standard PNG format for frontend visualization.
================================================================================
"""

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response
import io

# Initialize the router for DICOM processing endpoints
router = APIRouter()

@router.post("/convert-dicom")
async def convert_dicom(file: UploadFile = File(...)):
    """
    Accepts a DICOM file upload, parses its metadata (PatientID, Modality, Age, Sex),
    and converts its pixel data into a viewable PNG image.
    """
    import pydicom
    from PIL import Image
    import numpy as np
    
    # Read raw bytes and parse DICOM
    contents = await file.read()
    dicom_data = pydicom.dcmread(io.BytesIO(contents))
    pixel_array = dicom_data.pixel_array
    
    # Extract Patient ID
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
                
    # Extract Modality (Handling 'OT' fallback)
    modality = getattr(dicom_data, "Modality", "")
    if modality:
        modality = str(modality).strip()
        if modality == "OT":
            if file.filename and "mr" in file.filename.lower():
                modality = "MR"
            else:
                modality = "CT"
        
    # Extract Age and Sex
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
    
    # Normalize pixel data for PNG
    if pixel_array.max() > 0:
        pixel_array = pixel_array - pixel_array.min()
        pixel_array = (pixel_array / pixel_array.max()) * 255.0
    pixel_array = pixel_array.astype(np.uint8)
    
    image = Image.fromarray(pixel_array)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    
    # Set headers for the frontend to consume
    headers = {}
    if patient_id:
        headers["X-Patient-ID"] = patient_id
    if modality:
        headers["X-Modality"] = modality
    if age_gender:
        headers["X-Age-Gender"] = age_gender
        
    return Response(content=img_byte_arr.getvalue(), media_type="image/png", headers=headers)
