"""
================================================================================
 File Name:    main.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   The primary entry point for the Radiology Follow-up FastAPI application.
   This module wires together all modular endpoints (dashboard, DICOM processing, 
   and ADK pipeline execution) and serves the interactive frontend UI.
================================================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
import os

# Import our modular routers
from app.api.dashboard_api import router as dashboard_router
from app.api.dicom_api import router as dicom_router
from app.api.scan_api import router as scan_router

app = FastAPI(title="Radiology Follow-up API")

# Enable CORS for local testing if the HTML file is opened directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routers
app.include_router(dashboard_router, prefix="/api")
app.include_router(dicom_router, prefix="/api")
app.include_router(scan_router, prefix="/api")

# Mount the static directory to serve images and other assets
BASE_DIR = pathlib.Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

@app.get("/")
def read_root():
    """
    Redirect root to our specific html file acting as the frontend UI.
    """
    return FileResponse(str(BASE_DIR / "radiology_interactive_workflow.html"))
