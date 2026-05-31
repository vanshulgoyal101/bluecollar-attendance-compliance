import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple
from src.config import PolicyConfig
from src.llm_client import LLMComplianceClient, ExceptionAnalysis

class ComplianceEngine:
    def __init__(self, config: PolicyConfig, llm_client: LLMComplianceClient = None):
        self.config = config
        self.llm_client = llm_client or LLMComplianceClient()

    def process_employee_compliance(
        self, 
        employee_id: str, 
        punch_df: pd.DataFrame, 
        notes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process the attendance history for a single employee and calculate point trajectory.
        """
        # Filter punches for this employee
        emp_punches = punch_df[punch_df["employee_id"] == employee_id].copy()
        emp_punches = emp_punches.sort_values(by="date")
        
        if emp_punches.empty:
            return {
                "employee_id": employee_id,
                "current_points": self.config.start_points,
                "history": [],
                "warnings": [],
                "freeze_periods": []
            }

        # Index notes by date for quick access
        emp_notes = {
            note["date"]: note["note"] 
            for note in notes 
            if str(note["employee_id"]) == str(employee_id)
        }

        # Determine the timeline range
        start_date = emp_punches["date"].min()
        end_date = emp_punches["date"].max()
        
        # We will loop day-by-day to simulate chronological compliance tracking
        current_date = start_date
        current_points = self.config.start_points
        
        # State tracking
        deductions_history = []  # List of dicts representing point deductions
        warnings_triggered = []  # List of dicts: {"date": date, "level": "Written Warning"|"Termination Warning"|"Termination", "points": float}
        freeze_periods = []      # List of dicts: {"start": date, "end": date}
        active_freeze = None     # Dict: {"start": date, "end": date}
        
        # For consecutive skp tracking
        last_skp_date = None

        # Build list of unique dates to iterate or just iterate day by day
        # Day by day is safer for rolling window expirations even on days with no punches
        all_dates = pd.date_range(start=start_date, end=end_date).date
        
        for today in all_dates:
            # 1. Check if the active freeze period has ended
            if active_freeze and today > active_freeze["end"]:
                # Freeze ended!
                active_freeze = None

            # 2. Process roll-ons (expirations)
            # Roll-on happens if today is >= roll_on_date, the deduction hasn't rolled on yet,
            # and we are NOT in an active freeze period.
            if not active_freeze:
                for dec in deductions_history:
                    if not dec["rolled_on"] and today >= dec["roll_on_date"]:
                        # Restore points
                        current_points += dec["points_deducted"]
                        # Cap points at maximum starting points (7.0)
                        if current_points > self.config.start_points:
                            current_points = self.config.start_points
                        dec["rolled_on"] = True
                        dec["actual_roll_on_date"] = today

            # 3. Check for punches on this day
            day_punches = emp_punches[emp_punches["date"] == today]
            for _, punch in day_punches.iterrows():
                base_code = punch["base_code"]
                actual_code = punch["actual_code"]
                
                # If there's no actual infraction, skip
                if pd.isna(actual_code) or actual_code == base_code or actual_code == "SW":
                    continue

                # Get base deduction amount
                base_deduction = self.config.get_deduction(actual_code)
                if base_deduction == 0.0 and actual_code != "skps":
                    # If it's not a configured infraction and not skps, skip
                    continue
                
                # Check for LLM / Supervisor Note Exceptions
                note_text = emp_notes.get(today, "")
                is_exempt = False
                exempt_reason = "No note provided"
                exception_type = "None"

                if note_text:
                    analysis = self.llm_client.analyze_note(note_text, actual_code)
                    is_exempt = analysis.is_exempt
                    exempt_reason = analysis.reason
                    exception_type = analysis.exception_type

                # Rules for specific codes
                points_to_deduct = base_deduction
                
                # Unprotected consecutive sick period (skp)
                if actual_code == "skp":
                    if last_skp_date and (today - last_skp_date).days == 1:
                        # Consecutive day of sick leave, no additional points deducted
                        points_to_deduct = 0.0
                        exempt_reason = "Consecutive sick day under same skp period"
                        is_exempt = True
                    last_skp_date = today
                else:
                    # Reset last_skp_date if they have a non-skp infraction or work day
                    # But wait: only reset if not skp.
                    pass

                # Late <= 14 min (Lo) freebies
                if actual_code == "Lo" and not is_exempt:
                    # Look back 12 months for non-exempt Lo occurrences
                    lookback_start = today - datetime.timedelta(days=365)
                    past_los = [
                        d for d in deductions_history
                        if d["code"] == "Lo" 
                        and (not d["is_exempted"] or (d["is_exempted"] and "Freebie Lo" in str(d.get("exempt_reason", ""))))
                        and d["date"] >= lookback_start
                    ]
                    if len(past_los) < self.config.lo_freebies:
                        # It's a freebie!
                        points_to_deduct = 0.0
                        exempt_reason = f"Freebie Lo (occurrence {len(past_los) + 1} of {self.config.lo_freebies} in 12m)"
                        is_exempt = True

                # Apply deduction if not exempt
                if is_exempt:
                    points_to_deduct = 0.0

                if points_to_deduct > 0.0:
                    current_points -= points_to_deduct
                    # Points cannot go below 0
                    if current_points < 0.0:
                        current_points = 0.0

                    # Calculate standard roll_on_date (12 months from today)
                    # We can approximate 12 months as 365 days
                    roll_on_date = today + datetime.timedelta(days=365)

                    deduction_entry = {
                        "date": today,
                        "code": actual_code,
                        "points_deducted": points_to_deduct,
                        "is_exempted": False,
                        "exempt_reason": None,
                        "rolled_on": False,
                        "roll_on_date": roll_on_date,
                        "actual_roll_on_date": None,
                        "note": note_text
                    }
                    deductions_history.append(deduction_entry)
                else:
                    # Log the exempt/freebie infraction for audit history
                    deductions_history.append({
                        "date": today,
                        "code": actual_code,
                        "points_deducted": 0.0,
                        "is_exempted": True,
                        "exempt_reason": exempt_reason,
                        "rolled_on": False,
                        "roll_on_date": today,
                        "actual_roll_on_date": today,
                        "note": note_text
                    })

                # Check warning thresholds
                if current_points <= self.config.warning_termination:
                    warnings_triggered.append({
                        "date": today,
                        "level": "Termination Warning (<= 0.0)",
                        "points": current_points
                    })
                elif current_points <= self.config.warning_termination_warning:
                    warnings_triggered.append({
                        "date": today,
                        "level": "Termination Warning (<= 1.0)",
                        "points": current_points
                    })
                elif current_points <= self.config.warning_written:
                    warnings_triggered.append({
                        "date": today,
                        "level": "Written Warning (<= 2.0)",
                        "points": current_points
                    })

                # Check for freeze period trigger
                # Starts when points drop to or below 1.0, and no freeze is active
                if current_points <= self.config.freeze_trigger and not active_freeze:
                    # Trigger 4-month freeze period
                    freeze_end = today + datetime.timedelta(days=120)  # 4 months roughly 120 days
                    active_freeze = {
                        "start": today,
                        "end": freeze_end
                    }
                    freeze_periods.append(active_freeze)

        return {
            "employee_id": employee_id,
            "current_points": round(current_points, 2),
            "history": deductions_history,
            "warnings": warnings_triggered,
            "freeze_periods": freeze_periods
        }
