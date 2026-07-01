"""
================================================================================
 File Name:    tools.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Defines the strict clinical tools used by the ADK agents. Includes functions
   to query authoritative guidelines and lookup internal registry parameters.
================================================================================
"""

import json

def query_clinical_guidelines(finding_type: str, measurement: str = "") -> dict:
    """Queries the internal clinical guidelines registry for follow-up recommendations based on the finding.

    Args:
        finding_type: The type of clinical finding (e.g., 'nodule', 'mass').
        measurement: The size or measurement of the finding (e.g., '7 mm').

    Returns:
        dict: A dictionary containing the guideline title, citation section, 
              follow-up recommendation, and suggested screening interval.
    """
    finding_type_lower = finding_type.lower()
    
    if "nodule" in finding_type_lower:
        if "mm" in measurement:
            # Simulate a basic size check for pulmonary nodules (Fleischner criteria)
            try:
                size_str = ''.join(c for c in measurement if c.isdigit() or c == '.')
                if size_str:
                    size = float(size_str)
                    if size >= 6 and size <= 8:
                        return {
                            "guideline_title": "Fleischner Society Guidelines for Management of Incidental Pulmonary Nodules",
                            "citation_section": "Table 1, Solid nodule 6-8 mm",
                            "follow_up_recommendation": "Follow-up CT at 6-12 months, then at 18-24 months",
                            "screening_interval_months": "6-12"
                        }
                    elif size > 8:
                        return {
                            "guideline_title": "Fleischner Society Guidelines for Management of Incidental Pulmonary Nodules",
                            "citation_section": "Table 1, Solid nodule > 8 mm",
                            "follow_up_recommendation": "Consider CT at 3 months, PET/CT, or tissue sampling",
                            "screening_interval_months": "3"
                        }
            except ValueError:
                pass
                
        return {
            "guideline_title": "Fleischner Society Guidelines for Management of Incidental Pulmonary Nodules",
            "citation_section": "General Recommendation",
            "follow_up_recommendation": "Follow-up CT based on patient risk and nodule size.",
            "screening_interval_months": "12"
        }
    
    return {
        "guideline_title": "General Radiology Follow-up Guidelines",
        "citation_section": "Standard Care",
        "follow_up_recommendation": "Routine follow-up as clinically indicated.",
        "screening_interval_months": "12"
    }
