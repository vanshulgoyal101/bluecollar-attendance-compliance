const employeeData = {
  "EMP101": {
    "name": "Vanshul Goyal",
    "role": "Senior Warehouse Operator",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 2.5,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 1,
    "excused_absences": 2,
    "freebies_used": 3,
    "sick_balance_hours": 32,
    "vacation_hours": 80,
    "freeze_history": [],
    "schedule": [
      { "date": "2025-01-01", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" },
      { "date": "2025-02-15", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Late by 8 mins. Freebie #1 applied." },
      { "date": "2025-03-10", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Late by 11 mins. Freebie #2 applied." },
      { "date": "2025-04-12", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Late by 5 mins. Freebie #3 applied." },
      { "date": "2025-05-18", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Vanshul had car trouble. Supervisor let it slide.", "supervisor_note": "Vanshul had trouble with his car engine, but made it in late. I approved the late arrival and told him we would let it slide this time.", "is_exempt": true },
      { "date": "2025-06-01", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Point Deducted (-1.0)", "dto": false, "notes": "Day 1 of sick period.", "roll_on": "2026-06-01" },
      { "date": "2025-06-02", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Consecutive - No Penalty", "dto": false, "notes": "Day 2 of consecutive sick period.", "supervisor_note": "Vanshul called in sick again. Continuing skp." },
      { "date": "2025-07-20", "base": "SW (Scheduled Work)", "actual": "LT (Late >14m)", "status": "Point Deducted (-0.5)", "dto": false, "notes": "Late by 25 mins.", "roll_on": "2026-07-20" },
      { "date": "2025-08-15", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No call no show shift.", "roll_on": "2026-08-15" },
      { "date": "2025-08-20", "base": "DTO (Day Trade)", "actual": "DO (Day Off)", "status": "Swapped", "dto": true, "trade_partner": "EMP102", "notes": "Traded shift with EMP102." },
      { "date": "2025-09-01", "base": "SW (Scheduled Work)", "actual": "LTDR (Personal)", "status": "Exempted (FMLA)", "dto": false, "notes": "FMLA protected leave.", "supervisor_note": "Employee was out today due to FMLA-approved family medical leave.", "is_exempt": true }
    ],
    "history": [
      { "date": "2025-02-15", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie Lo (occurrence 1 of 3 in 12m)" },
      { "date": "2025-03-10", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie Lo (occurrence 2 of 3 in 12m)" },
      { "date": "2025-04-12", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie Lo (occurrence 3 of 3 in 12m)" },
      { "date": "2025-05-18", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Supervisor Override: Vanshul car trouble - let slide" },
      { "date": "2025-06-01", "code": "skp", "points": -1.0, "status": "Active Deduction", "details": "Unprotected sick period", "roll_on": "2026-06-01" },
      { "date": "2025-06-02", "code": "skp", "points": 0.0, "status": "Exempted", "details": "Consecutive sick day under same skp period" },
      { "date": "2025-07-20", "code": "LT", "points": -0.5, "status": "Active Deduction", "details": "Late >14 mins", "roll_on": "2026-07-20" },
      { "date": "2025-08-15", "code": "IANS", "points": -3.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-08-15" },
      { "date": "2025-09-01", "code": "LTDR", "points": 0.0, "status": "Exempted", "details": "FMLA Approved Medical Leave" }
    ],
    "warnings": []
  },
  "EMP102": {
    "name": "Sarah Connor",
    "role": "Assembly Line Supervisor",
    "department": "Manufacturing Operations",
    "starting_points": 7.0,
    "current_points": 2.0,
    "warning_status": "Written Warning Active",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 16,
    "vacation_hours": 48,
    "freeze_history": [
      { "start": "2025-01-11", "end": "2025-05-11", "status": "Completed" }
    ],
    "schedule": [
      { "date": "2025-01-01", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" },
      { "date": "2025-01-10", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No call no show.", "roll_on": "2026-01-10" },
      { "date": "2025-01-11", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-2.0)", "dto": false, "notes": "Late reported absence. Warning level triggered.", "roll_on": "2026-01-11" },
      { "date": "2025-08-20", "base": "DTO (Day Trade)", "actual": "SW (Present)", "dto": true, "trade_partner": "EMP101", "notes": "Worked shift swapped with EMP101." }
    ],
    "history": [
      { "date": "2025-01-10", "code": "IANS", "points": -3.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-01-10" },
      { "date": "2025-01-11", "code": "LTNC", "points": -2.0, "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2026-01-11" }
    ],
    "warnings": [
      { "date": "2025-01-11", "level": "Written Warning (<= 2.0)", "points": 2.0 }
    ]
  },
  "EMP103": {
    "name": "Marcus Wright",
    "role": "Inventory Handler",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 7.0,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 40,
    "vacation_hours": 120,
    "freeze_history": [],
    "schedule": [
      { "date": "2025-01-01", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" },
      { "date": "2025-01-02", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" }
    ],
    "history": [],
    "warnings": []
  },
  "EMP104": {
    "name": "John Connor",
    "role": "Operations Analyst",
    "department": "Quality Assurance",
    "starting_points": 7.0,
    "current_points": 1.0,
    "warning_status": "Termination Warning Active",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 3,
    "sick_balance_hours": 8,
    "vacation_hours": 16,
    "freeze_history": [
      { "start": "2025-03-01", "end": "2025-07-01", "status": "Active" }
    ],
    "schedule": [
      { "date": "2025-01-05", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie #1" },
      { "date": "2025-01-12", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie #2" },
      { "date": "2025-01-20", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie #3" },
      { "date": "2025-02-15", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "NCNS penalty.", "roll_on": "2026-02-15" },
      { "date": "2025-03-01", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "Late reported absence. Reached 1.0 threshold, freeze initiated.", "roll_on": "2026-03-01" }
    ],
    "history": [
      { "date": "2025-01-05", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-01-12", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-01-20", "code": "Lo", "points": 0.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-02-15", "code": "IANS", "points": -3.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-02-15" },
      { "date": "2025-03-01", "code": "IANS", "points": -3.0, "status": "Active Deduction", "details": "No call no show (Warning Triggered)", "roll_on": "2026-03-01" }
    ],
    "warnings": [
      { "date": "2025-02-15", "level": "Written Warning (<= 2.0)", "points": 4.0 },
      { "date": "2025-03-01", "level": "Termination Warning (<= 1.0)", "points": 1.0 }
    ]
  },
  "EMP105": {
    "name": "Kyle Reese",
    "role": "Maintenance Technician",
    "department": "Facilities",
    "starting_points": 7.0,
    "current_points": 0.0,
    "warning_status": "TERMINATION PROTOCOL TRIGGERED",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 1,
    "sick_balance_hours": 0,
    "vacation_hours": 0,
    "freeze_history": [
      { "start": "2025-04-10", "end": "2025-08-10", "status": "Completed" }
    ],
    "schedule": [
      { "date": "2025-01-10", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No call no show.", "roll_on": "2026-01-10" },
      { "date": "2025-02-20", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-2.0)", "dto": false, "notes": "Late reported absence. Written warning triggered.", "roll_on": "2026-02-20" },
      { "date": "2025-04-10", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-2.0)", "dto": false, "notes": "Late reported absence. Points reached 0.0, termination protocol active.", "roll_on": "2026-04-10" }
    ],
    "history": [
      { "date": "2025-01-10", "code": "IANS", "points": -3.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-01-10" },
      { "date": "2025-02-20", "code": "LTNC", "points": -2.0, "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2026-02-20" },
      { "date": "2025-04-10", "code": "LTNC", "points": -2.0, "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2026-04-10" }
    ],
    "warnings": [
      { "date": "2025-02-20", "level": "Written Warning (<= 2.0)", "points": 2.0 },
      { "date": "2025-04-10", "level": "Termination Memo (<= 0.0)", "points": 0.0 }
    ]
  }
};
