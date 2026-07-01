"""
================================================================================
 File Name:    dashboard_api.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Manages the global in-memory dashboard state and provides the API endpoint 
   required by the frontend to fetch real-time workflow statistics.
================================================================================
"""

from fastapi import APIRouter

# Initialize the router for dashboard API endpoints
router = APIRouter()

# Global state for dashboard analytics
dashboard_stats = {
    "totalScans": 36,
    "uniquePatients": {"P-45921", "P-82103", "P-10934", "P-93021", "P-11234", "P-84729", "P-55910", "P-33102", "P-72810", "P-22394"},
    "highPriority": 4,
    "guardrailPassRate": 99.8,
    "recentPatients": [
        {
            "patientId": "P12345", "modality": "CT", "target": "Chest (Lung Target)", "priority": "MEDIUM", "targetDate": "2027-03-26", "sampleKey": "chest_ct",
            "clinicianNote": "64-year-old male with a history of tobacco usage presented with a 7mm right upper lobe pulmonary nodule. Follow-up CT chest scheduled in 6-12 months per Fleischner criteria.",
            "patientExplanation": "A small spot (7 mm nodule) was found in your right lung. It is common and often not serious. We recommend a repeat CT scan in 6-12 months to make sure it stays stable."
        },
        {
            "patientId": "P67890", "modality": "MR", "target": "Abdomen (Hepatobiliary)", "priority": "HIGH", "targetDate": "2026-07-25", "sampleKey": "liver_mr",
            "clinicianNote": "52-year-old female with a history of breast cancer presented with a newly noted 1.5 cm indeterminate liver lesion in segment IVb. Urgent hepatobiliary MR follow-up requested within 4 weeks.",
            "patientExplanation": "During your recent scan, we found a small 1.5 cm spot on your liver. Given your medical history, it is important to take a closer look. We scheduled a specialized follow-up liver scan for you as a priority."
        },
        {
            "patientId": "P-93021", "modality": "CT", "target": "Head (Brain)", "priority": "LOW", "targetDate": "Routine (1 Year)", "sampleKey": None,
            "clinicianNote": "No acute intracranial pathology. Ventricles and sulci are age-appropriate.",
            "patientExplanation": "Your brain scan looks normal for your age. There are no signs of bleeding, tumors, or other serious issues."
        },
        {
            "patientId": "P-11234", "modality": "XR", "target": "Chest (Heart)", "priority": "HIGH", "targetDate": "2026-07-05", "sampleKey": None,
            "clinicianNote": "Enlarged cardiac silhouette with mild pulmonary venous congestion. Suggest cardiology consult.",
            "patientExplanation": "Your heart appears slightly larger than normal and there is some extra fluid in your lungs. We want you to see a heart specialist soon."
        },
        {
            "patientId": "P-84729", "modality": "US", "target": "Pelvis", "priority": "LOW", "targetDate": "Routine (6 Months)", "sampleKey": None,
            "clinicianNote": "Unremarkable pelvic ultrasound. Normal ovarian flow.",
            "patientExplanation": "Your pelvic ultrasound looks completely normal. All organs appear healthy."
        },
        {
            "patientId": "P-55910", "modality": "MR", "target": "Spine (Cervical)", "priority": "MEDIUM", "targetDate": "2026-08-20", "sampleKey": None,
            "clinicianNote": "Mild C5-C6 foraminal stenosis without cord compression. Conservative management recommended.",
            "patientExplanation": "There is a slight narrowing in your neck spine where a nerve exits, but it's not pushing on the spinal cord. Physical therapy might help."
        },
        {
            "patientId": "P-33102", "modality": "CT", "target": "Abdomen/Pelvis", "priority": "HIGH", "targetDate": "2026-07-01", "sampleKey": None,
            "clinicianNote": "Acute appendicitis with localized inflammatory changes. Surgical consult paged.",
            "patientExplanation": "Your appendix is inflamed and irritated. We have contacted a surgeon to evaluate you immediately."
        },
        {
            "patientId": "P-72810", "modality": "XR", "target": "Left Knee", "priority": "LOW", "targetDate": "Routine (1 Year)", "sampleKey": None,
            "clinicianNote": "Mild tricompartmental osteoarthritis. No acute fracture.",
            "patientExplanation": "You have some mild arthritis in your left knee, which is normal wear and tear. There are no broken bones."
        },
        {
            "patientId": "P-22394", "modality": "MR", "target": "Brain", "priority": "HIGH", "targetDate": "2026-07-10", "sampleKey": None,
            "clinicianNote": "Subacute lacunar infarct in the left basal ganglia. Neurology referral required.",
            "patientExplanation": "There is evidence of a small, recent stroke in a deep part of your brain. You will need to see a neurologist for further care."
        },
        {
            "patientId": "P-10934", "modality": "XR", "target": "Right Shoulder", "priority": "LOW", "targetDate": "Routine (1 Year)", "sampleKey": None,
            "clinicianNote": "Degenerative changes at the AC joint. Intact rotator cuff shadow.",
            "patientExplanation": "You have some arthritis at the top of your shoulder joint, but the major tendons appear to be intact."
        }
    ]
}

@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """
    Returns the current dashboard statistics, tracking total scans,
    unique patients, and recent processed patient results.
    """
    return {
        "totalScans": dashboard_stats["totalScans"],
        "uniquePatients": len(dashboard_stats["uniquePatients"]),
        "highPriority": dashboard_stats["highPriority"],
        "guardrailPassRate": dashboard_stats["guardrailPassRate"],
        "recentPatients": dashboard_stats["recentPatients"]
    }
