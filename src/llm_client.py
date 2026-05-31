import os
import json
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
import litellm

logger = logging.getLogger(__name__)

class ExceptionAnalysis(BaseModel):
    is_exempt: bool = Field(description="True if the absence/infraction is exempt from point deductions due to FMLA, approved medical/family leave, or explicit supervisor override.")
    reason: str = Field(description="Detailed reason explaining why it is exempt or not exempt, referencing FMLA or policy rules.")
    exception_type: str = Field(description="Type of exception: 'FMLA', 'Approved Sick Leave', 'Supervisor Override', or 'None'.")

class LLMComplianceClient:
    def __init__(self, model: str = None):
        self.model = model or os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    def analyze_note(self, note_text: str, infraction_type: str) -> ExceptionAnalysis:
        """
        Analyzes a supervisor note to determine if an infraction qualifies for a policy exception.
        """
        if not note_text or note_text.strip() == "":
            return ExceptionAnalysis(is_exempt=False, reason="No supervisor note provided.", exception_type="None")

        if not self.api_key:
            # Fallback mock logic for local testing/runs without API key to ensure reliability
            note_lower = note_text.lower()
            if "fmla" in note_lower or "family medical leave" in note_lower:
                return ExceptionAnalysis(
                    is_exempt=True,
                    reason="[Mocked Exception] Supervisor note mentions FMLA/Family Medical Leave.",
                    exception_type="FMLA"
                )
            elif "let it slide" in note_lower or "letting it slide" in note_lower or "approved" in note_lower or "excused" in note_lower:
                return ExceptionAnalysis(
                    is_exempt=True,
                    reason="[Mocked Exception] Supervisor explicitly noted to let it slide or approved the exception.",
                    exception_type="Supervisor Override"
                )
            elif "sick" in note_lower and ("skps" in note_lower or "protected" in note_lower):
                return ExceptionAnalysis(
                    is_exempt=True,
                    reason="[Mocked Exception] Supervisor note refers to a protected sick period.",
                    exception_type="Approved Sick Leave"
                )
            return ExceptionAnalysis(
                is_exempt=False,
                reason="[Mocked Analysis] Note does not contain key exemption indicators (FMLA, let it slide, etc.).",
                exception_type="None"
            )

        prompt = f"""
Analyze the following supervisor note regarding a workforce attendance infraction.
Determine if the infraction is exempt from points reduction under company policies.
Policies allow exemptions for:
- Family and Medical Leave Act (FMLA)
- Other approved/protected leaves
- Explicit supervisor overrides/exemptions (e.g. "letting it slide", "excused", "approved")

Infraction Type: {infraction_type}
Supervisor Note: "{note_text}"

Return a JSON object conforming exactly to this structure:
{{
  "is_exempt": true/false,
  "reason": "Detailed reason here...",
  "exception_type": "FMLA" | "Approved Sick Leave" | "Supervisor Override" | "None"
}}
"""
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return ExceptionAnalysis(**data)
        except Exception as e:
            logger.error(f"Error calling LLM: {e}. Falling back to default negative result.")
            return ExceptionAnalysis(
                is_exempt=False,
                reason=f"Failed to analyze note due to LLM error: {str(e)}",
                exception_type="None"
            )
