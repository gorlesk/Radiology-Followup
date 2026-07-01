"""
================================================================================
 File Name:    agent.py
 Author:       Sunil Kumar Gorle
 
 Description:  
   Defines the Google ADK Multi-Agent workflow. This file contains the prompts,
   models, output schemas, and the Directed Acyclic Graph (DAG) that sequentially
   chains the 8 clinical AI agents into a seamless pipeline.
================================================================================
"""

import os
import google.auth
from pydantic import BaseModel, Field
from typing import List

from google.adk.agents import Agent
from google.adk.workflow import Workflow
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import query_clinical_guidelines

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# -------------------------------------------------------------------
# AGENT 1: Report Parser
# Purpose: Parses unstructured radiology text into defined categories.
# -------------------------------------------------------------------

class ParsedReport(BaseModel):
    patient_name: str = Field(description="Patient's name, if available.", default="Unknown")
    exam_date: str = Field(description="Date of the radiology exam, e.g., '2026-06-01'.", default="Unknown")
    clinical_history: str = Field(description="Clinical history extracted from the report.")
    technical_protocol: str = Field(description="Technical protocol used for the scan.")
    findings: str = Field(description="Detailed findings from the scan.")
    impression: str = Field(description="Overall impression or conclusion.")


report_parser_agent = Agent(
    name="report_parser_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Report Parser Agent. Your task is to ingest unstructured radiology scan reports (TXT/PDF text or DICOM header metadata).
Parse the contents, clean formatting anomalies, and structure them into defined clinical categories: Clinical History, Technical Protocol, Findings, and Impression.
Do NOT interpret findings; only structure the raw text into the requested categories.""",
    output_schema=ParsedReport,
    output_key="parsed_report",
)


# -------------------------------------------------------------------
# AGENT 2: Finding Extraction
# Purpose: Performs clinical NER to extract discrete findings from the parsed text.
# -------------------------------------------------------------------

class ClinicalFinding(BaseModel):
    finding_type: str = Field(description="Type of clinical finding (e.g., nodule, mass, cyst).")
    measurement: str = Field(description="Precise measurements if available (e.g., '7 mm'). Return empty string if none.")
    location: str = Field(description="Anatomical location of the finding (e.g., 'right upper lobe'). Return empty string if none.")
    is_negated: bool = Field(description="True if the finding is negated/excluded (e.g., 'no nodule'). False if the finding is present.")


class FindingExtractionResult(BaseModel):
    findings: List[ClinicalFinding] = Field(description="List of clinical findings extracted.")


finding_extraction_agent = Agent(
    name="finding_extraction_agent",
    model=Gemini(
        model="gemini-2.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Finding Extraction Agent. Analyze the parsed Findings and Impression sections provided in the input.
Perform clinical Named Entity Recognition (NER) to extract:
1) Clinical findings (e.g., nodule, mass, cyst)
2) Precise measurements (e.g., '7 mm')
3) Anatomical locations (e.g., 'right upper lobe')
Resolve negation status. If a finding is explicitly ruled out (e.g., 'No pleural effusion'), set is_negated to true.
Focus on actionable or abnormal clinical findings.
Here is the parsed report to analyze:
{parsed_report}""",
    output_schema=FindingExtractionResult,
    output_key="extracted_findings",
)


# -------------------------------------------------------------------
# AGENT 3: Guideline Retrieval
# Purpose: Uses external tools to query clinical guidelines for the extracted findings.
# -------------------------------------------------------------------

guideline_retrieval_agent = Agent(
    name="guideline_retrieval_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Guideline Retrieval Agent.
Use the `query_clinical_guidelines` tool to query the clinical guidelines registry for the extracted findings provided in the input.
Analyze the findings provided below:
{extracted_findings}

For each actionable finding (where is_negated is false), use the tool to retrieve the exact follow-up recommendations.
Output your final answer strictly as a JSON object with this exact structure:
{
    "recommendations": [
        {
            "finding_type": "<type>",
            "guideline_title": "<title>",
            "citation_section": "<citation>",
            "follow_up_recommendation": "<recommendation>",
            "screening_interval_months": "<interval>"
        }
    ]
}
Ensure the output is strictly valid JSON without Markdown blocks like ```json around it.
""",
    tools=[query_clinical_guidelines],
    output_key="guideline_recommendations_raw",
)


# -------------------------------------------------------------------
# AGENT 4: Risk Classification
# Purpose: Assigns clinical priority (HIGH/MEDIUM/LOW) based on findings and guidelines.
# -------------------------------------------------------------------

class RiskClassification(BaseModel):
    priority: str = Field(description="Assigned clinical priority (e.g., HIGH, MEDIUM, LOW).")
    justification: str = Field(description="Brief justification for the assigned priority based on findings and patient context.")


risk_classification_agent = Agent(
    name="risk_classification_agent",
    model=Gemini(
        model="gemini-2.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Risk Classification Agent.
Analyze the patient context, the extracted clinical findings, and the retrieved guideline recommendations provided below:

Patient Context (from parsed report):
{parsed_report}

Extracted Findings:
{extracted_findings}

Guideline Recommendations:
{guideline_recommendations_raw}

Assign a clinical priority (HIGH, MEDIUM, or LOW) for the follow-up tasks based on the finding severity, patient age/gender, and the recommended screening interval from the guidelines.
A short interval (e.g., 3 months) or concerning patient symptoms usually implies HIGH priority. Standard 6-12 month intervals often imply MEDIUM priority. Routine care implies LOW priority.
""",
    output_schema=RiskClassification,
    output_key="risk_classification",
)


# -------------------------------------------------------------------
# AGENT 5: Task Creation
# Purpose: Calculates strict due dates and structures payload for the EHR.
# -------------------------------------------------------------------

class TaskCreationPayload(BaseModel):
    task_priority: str = Field(description="Priority of the task (e.g., HIGH, MEDIUM, LOW).")
    target_due_date: str = Field(description="Calculated target calendar due date for the follow-up, formatted as YYYY-MM-DD.")
    reference_clinical_findings: str = Field(description="Summary of the referenced clinical findings.")
    ehr_patient_name: str = Field(description="Patient name for the EHR record.")


import datetime
current_date_str = datetime.date.today().isoformat()

task_creation_agent = Agent(
    name="task_creation_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=f"""You are the Task Creation Agent.
Based on the provided information, calculate the target calendar due date for a radiology follow-up and generate a structured EHR task creation payload.

CURRENT SYSTEM DATE: {current_date_str}

Context available to you:
Parsed Report (contains exam date and patient info):
{{parsed_report}}

Extracted Findings:
{{extracted_findings}}

Guideline Recommendations (contains screening interval):
{{guideline_recommendations_raw}}

Assigned Risk Priority:
{{risk_classification}}

To calculate the target_due_date, add the recommended screening interval (in months) to the exam date found in the parsed report. 
If the exam date is missing or not provided, you MUST use the CURRENT SYSTEM DATE ({current_date_str}) as the baseline exam date for your calculation.
CRITICAL: If the calculated target_due_date is in the past (earlier than {current_date_str}), this means the scan is historical and the follow-up is severely delayed. In this case, you MUST calculate the target_due_date starting from the CURRENT SYSTEM DATE ({current_date_str}) instead, or output 'OVERDUE - Schedule Immediately (ASAP)'. Never output a target date in the past.
Output the structured payload required to create the EHR task.
""",
    output_schema=TaskCreationPayload,
    output_key="task_creation_payload",
)


# -------------------------------------------------------------------
# AGENT 6: Communication
# Purpose: Synthesizes both a professional Clinician Note and a Patient-Friendly explanation.
# -------------------------------------------------------------------

class CommunicationOutputs(BaseModel):
    clinician_note: str = Field(description="A professional, concise Clinician Note summarizing the findings and the guideline justification.")
    patient_friendly_explanation: str = Field(description="A patient-friendly explanation written at a 6th-grade reading level, explaining the finding in simple terms.")


communication_agent = Agent(
    name="communication_agent",
    model=Gemini(
        model="gemini-2.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Communication Agent.
Based on all the collected information from the radiology report and follow-up guidelines, create two communication outputs:
1) A professional, concise Clinician Note summarizing the findings and the guideline justification.
2) A patient-friendly explanation written at a 6th-grade reading level, explaining the finding in simple, non-alarming terms.

CRITICAL: When mentioning the follow-up timeline in the Clinician Note or Patient Letter, you MUST ensure it strictly aligns with the exact target due date provided in the Task Payload. Do not generate conflicting dates or intervals.
CRITICAL: If the Assigned Risk Priority is HIGH, you MUST explicitly recommend in the Patient Letter that the patient contacts their doctor's office within 1-2 days to discuss the findings and schedule the follow-up.

Context available to you:
Parsed Report:
{parsed_report}

Extracted Findings:
{extracted_findings}

Guideline Recommendations:
{guideline_recommendations_raw}

Assigned Risk Priority:
{risk_classification}

Task Payload (including target due date):
{task_creation_payload}
""",
    output_schema=CommunicationOutputs,
    output_key="communication_outputs",
)


# -------------------------------------------------------------------
# AGENT 7: Follow-up Tracker
# Purpose: Establishes calendar reminders and escalation rules for tracking.
# -------------------------------------------------------------------

class TrackerOutputs(BaseModel):
    scheduling_state: str = Field(description="The scheduling state of the follow-up task (e.g., Pending, Scheduled, Completed).")
    calendar_reminders: List[str] = Field(description="List of calendar reminders to be set (e.g., 'Reminder 30 days before due date').")
    escalation_rules: str = Field(description="Escalation rules if the patient does not book the scan within the due window.")


follow_up_tracker_agent = Agent(
    name="follow_up_tracker_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Follow-up Tracker Agent.
Based on the task payload and priority, define tracking rules and output the scheduling state.
Since this is a new finding that was just processed, the initial state should typically be 'Pending'.
Register necessary calendar reminders leading up to the target due date.
Specify clear escalation rules if the patient does not book the scan by the target due window, considering the task priority.

Task Payload:
{task_creation_payload}

Risk Priority:
{risk_classification}
""",
    output_schema=TrackerOutputs,
    output_key="tracker_outputs",
)


# -------------------------------------------------------------------
# AGENT 8: Audit & Guardrail
# Purpose: Verifies the entire pipeline's output against strict safety rules before finalizing.
# -------------------------------------------------------------------

class AuditOutputs(BaseModel):
    timeline_aligned: str = Field(description="PASSED or FAILED. Indicates if the follow-up timeline is clinically aligned with the retrieved guideline.")
    no_factual_discrepancies: str = Field(description="PASSED or FAILED. Indicates if the patient explanation contains no factual discrepancies compared to the clinical findings.")
    dates_correctly_calculated: str = Field(description="PASSED or FAILED. Indicates if all dates (like target due date) are correctly calculated based on the exam date and interval.")
    audit_notes: str = Field(description="Detailed notes on any failures or overall verification summary.")


audit_guardrail_agent = Agent(
    name="audit_guardrail_agent",
    model=Gemini(
        model="gemini-2.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the Audit & Guardrail Agent.
Review the completed pipeline outputs to verify correctness and safety.

Verify the following:
1) The follow-up timeline (target_due_date from task payload) is clinically aligned with the retrieved guideline screening interval.
2) The patient-friendly explanation contains no factual discrepancies compared to the original parsed report and extracted clinical findings.
3) All dates are correctly calculated (target due date = exam date + screening interval).

Provide PASSED or FAILED for each check, along with audit notes.

Context available to you:
Parsed Report:
{parsed_report}

Extracted Findings:
{extracted_findings}

Guideline Recommendations:
{guideline_recommendations_raw}

Task Payload:
{task_creation_payload}

Communication Outputs:
{communication_outputs}
""",
    output_schema=AuditOutputs,
    output_key="audit_outputs",
)


# -------------------------------------------------------------------
# WORKFLOW DEFINITION
# Purpose: Chains all the above agents sequentially into a DAG (Directed Acyclic Graph).
# -------------------------------------------------------------------

# Combine into sequential pipeline using Workflow
radiology_pipeline = Workflow(
    name="radiology_pipeline",
    edges=[
        ('START', report_parser_agent),
        (report_parser_agent, finding_extraction_agent),
        (finding_extraction_agent, guideline_retrieval_agent),
        (guideline_retrieval_agent, risk_classification_agent),
        (risk_classification_agent, task_creation_agent),
        (task_creation_agent, communication_agent),
        (communication_agent, follow_up_tracker_agent),
        (follow_up_tracker_agent, audit_guardrail_agent),
    ]
)


app = App(
    root_agent=radiology_pipeline,
    name="app",
)
