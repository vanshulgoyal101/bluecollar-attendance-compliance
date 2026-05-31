import datetime
from typing import Dict, Any

class ComplianceReportGenerator:
    @staticmethod
    def generate_irm_brief(employee_id: str, results: Dict[str, Any]) -> str:
        """
        Generates a professional, detailed Investigative Review Meeting (IRM) brief in Markdown.
        """
        current_points = results["current_points"]
        history = results["history"]
        warnings = results["warnings"]
        freeze_periods = results["freeze_periods"]
        
        status = "Good Standing"
        if current_points <= 0.0:
            status = "TERMINATION PROTOCOL TRIGGERED"
        elif current_points <= 1.0:
            status = "Termination Warning Active"
        elif current_points <= 2.0:
            status = "Written Warning Active"
            
        md = []
        md.append(f"# Investigative Review Meeting (IRM) Brief")
        md.append(f"**Date Generated:** {datetime.date.today().strftime('%Y-%m-%d')}")
        md.append(f"**Employee ID:** {employee_id}")
        md.append(f"**Current Compliance Points:** {current_points} / 7.0")
        md.append(f"**Status:** `{status}`")
        md.append("")
        
        md.append("## Executive Summary")
        md.append("This report compiles a chronological compliance review of the employee's attendance record, "
                  "cross-referencing raw punch logs, system configuration parameters, and parsed supervisor shift notes. "
                  "It evaluates points roll-on/expiry under active freeze rules and identifies valid regulatory exceptions (like FMLA).")
        md.append("")
        
        # Warnings log
        md.append("## Escalation & Warning Triggers")
        if warnings:
            md.append("| Date | Warning / Action | Points at Time |")
            md.append("| :--- | :--- | :--- |")
            for w in warnings:
                md.append(f"| {w['date']} | {w['level']} | {w['points']} |")
        else:
            md.append("*No compliance action thresholds crossed.*")
        md.append("")

        # Freeze periods
        md.append("## Freeze Periods")
        if freeze_periods:
            md.append("| Freeze Start | Freeze End (Tentative) | Status |")
            md.append("| :--- | :--- | :--- |")
            for fp in freeze_periods:
                is_active = "Active" if datetime.date.today() <= fp["end"] else "Completed"
                md.append(f"| {fp['start']} | {fp['end']} | {is_active} |")
        else:
            md.append("*No freeze periods activated.*")
        md.append("")

        # History log
        md.append("## Detailed Infraction & Audit Trail")
        md.append("| Date | Infraction Code | Points Deducted | Status | Exception Details / supervisor note |")
        md.append("| :--- | :--- | :--- | :--- | :--- |")
        
        for item in history:
            pts = item["points_deducted"]
            exempt = item["is_exempted"]
            status_str = "Exempt / Overridden" if exempt else f"Applied (Roll-on: {item['roll_on_date']})"
            
            note_str = item["note"] if item["note"] else "*None*"
            reason_str = f"**{item['exempt_reason']}**" if item["exempt_reason"] else note_str
            
            md.append(f"| {item['date']} | `{item['code']}` | -{pts} | {status_str} | {reason_str} |")
            
        md.append("")
        md.append("---")
        md.append("*Confidential - For Internal HR and Management Use Only.*")
        
        return "\n".join(md)

    @staticmethod
    def generate_warning_letter(employee_id: str, level: str, points: float) -> str:
        """
        Generates a warning letter ready for signature.
        """
        today_str = datetime.date.today().strftime('%B %d, %Y')
        
        md = f"""# OFFICIAL COMPLIANCE WARNING NOTICE

**Date:** {today_str}  
**To:** Employee {employee_id}  
**From:** Workforce Compliance Operations  
**Subject:** NOTICE OF ATTENDANCE COMPLIANCE ACTION ({level})

This letter serves as formal notification regarding your attendance compliance score under the company's No-Fault attendance policy. 

### Status Summary
- **Current Balance:** {points} Points (Starting balance: 7.0)
- **Status level:** {level}

### Policy Reminder
Our attendance tracking utilizes a rolling point system where infractions lead to point reductions. Consistent attendance is critical to operational success.
- Point levels at or below **2.0** trigger a **Written Warning**.
- Point levels at or below **1.0** trigger a **Termination Warning** and initiate a **4-month roll-on freeze period**.
- Point levels at or below **0.0** result in immediate **termination**.

Please contact HR or your direct supervisor immediately to discuss this notice and develop a plan to restore your attendance rating.

Sincerely,  
*Workforce Compliance Department Office*
"""
        return md
