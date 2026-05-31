const employeeData = {
  "EMP101": {
    "name": "Vanshul Goyal",
    "join_date": "2022-03-01",
    "role": "Senior Warehouse Operator",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 0.5,
    "warning_status": "Termination Warning Active",
    "fmla_approved_cases": 2,
    "excused_absences": 4,
    "freebies_used": 3,
    "sick_balance_hours": 32,
    "vacation_hours": 80,
    "freeze_history": [
      { "start": "2026-02-15", "end": "2026-06-15", "status": "Active" }
    ],
    "schedule": [
      { "date": "2023-01-15", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #1" },
      { "date": "2023-02-10", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #2" },
      { "date": "2023-03-20", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #3" },
      { "date": "2023-05-01", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Point Deducted (-1.0)", "dto": false, "notes": "Unexcused sick leave.", "roll_on": "2024-05-01" },
      { "date": "2023-08-10", "base": "SW (Scheduled Work)", "actual": "LT (Late >14m)", "status": "Point Deducted (-0.5)", "dto": false, "notes": "Late 20 mins.", "roll_on": "2024-08-10" },
      { "date": "2023-11-15", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No show.", "roll_on": "2024-11-15" },
      { "date": "2024-01-10", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Point Deducted (-1.0)", "dto": false, "notes": "Sick day.", "roll_on": "2025-01-10" },
      { "date": "2025-03-15", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #1 (New 12m rolling window)" },
      { "date": "2025-06-01", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Point Deducted (-1.0)", "dto": false, "notes": "Sick day.", "roll_on": "2026-06-01" },
      { "date": "2025-06-02", "base": "SW (Scheduled Work)", "actual": "skp (Unprotected Sick)", "status": "Consecutive - No Penalty", "dto": false, "notes": "Day 2 of consecutive sick period.", "supervisor_note": "Vanshul called in sick again. Continuing skp." },
      { "date": "2025-08-15", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No call no show shift.", "roll_on": "2026-08-15" },
      { "date": "2025-10-10", "base": "SW (Scheduled Work)", "actual": "LT (Late >14m)", "status": "Point Deducted (-0.5)", "dto": false, "notes": "Late 18 mins.", "roll_on": "2026-10-10" },
      { "date": "2026-02-15", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-2.0)", "dto": false, "notes": "Late reported absence. Reached 0.5 points, active freeze period triggered.", "roll_on": "2027-02-15" }
    ],
    "history": [
      { "date": "2023-01-15", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo (occurrence 1 of 3 in 12m)" },
      { "date": "2023-02-10", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo (occurrence 2 of 3 in 12m)" },
      { "date": "2023-03-20", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo (occurrence 3 of 3 in 12m)" },
      { "date": "2023-05-01", "code": "skp", "points": -1.0, "balance": 6.0, "status": "Active Deduction", "details": "Unprotected sick period", "roll_on": "2024-05-01" },
      { "date": "2023-08-10", "code": "LT", "points": -0.5, "balance": 5.5, "status": "Active Deduction", "details": "Late >14 mins", "roll_on": "2024-08-10" },
      { "date": "2023-11-15", "code": "IANS", "points": -3.0, "balance": 2.5, "status": "Active Deduction", "details": "No call no show", "roll_on": "2024-11-15" },
      { "date": "2024-01-10", "code": "skp", "points": -1.0, "balance": 1.5, "status": "Active Deduction", "details": "Unprotected sick (Written Warning triggered)", "roll_on": "2025-01-10" },
      { "date": "2024-05-01", "code": "ROLL-ON", "points": 1.0, "balance": 2.5, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-05-01 skp deduction" },
      { "date": "2024-08-10", "code": "ROLL-ON", "points": 0.5, "balance": 3.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-08-10 LT deduction" },
      { "date": "2024-11-15", "code": "ROLL-ON", "points": 3.0, "balance": 6.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-11-15 IANS deduction" },
      { "date": "2025-01-10", "code": "ROLL-ON", "points": 1.0, "balance": 7.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2024-01-10 skp deduction" },
      { "date": "2025-03-15", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo (occurrence 1 of 3 in new 12m)" },
      { "date": "2025-06-01", "code": "skp", "points": -1.0, "balance": 6.0, "status": "Active Deduction", "details": "Unprotected sick period", "roll_on": "2026-06-01" },
      { "date": "2025-06-02", "code": "skp", "points": 0.0, "balance": 6.0, "status": "Exempted", "details": "Consecutive sick day under same skp period" },
      { "date": "2025-08-15", "code": "IANS", "points": -3.0, "balance": 3.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-08-15" },
      { "date": "2025-10-10", "code": "LT", "points": -0.5, "balance": 2.5, "status": "Active Deduction", "details": "Late >14 mins", "roll_on": "2026-10-10" },
      { "date": "2026-02-15", "code": "LTNC", "points": -2.0, "balance": 0.5, "status": "Active Deduction", "details": "Late reported absence. Reached 0.5 points. Active freeze period initiated (all point roll-ons paused).", "roll_on": "2027-02-15" },
      { "date": "2026-06-01", "code": "ROLL-ON", "points": 1.0, "balance": 0.5, "status": "PAUSED (Freeze Active)", "details": "Recovery of 2025-06-01 skp paused during 4m freeze.", "roll_on": "Paused" }
    ],
    "warnings": [
      { "date": "2024-01-10", "level": "Written Warning (<= 2.0)", "points": 1.5 },
      { "date": "2026-02-15", "level": "Termination Warning (<= 1.0)", "points": 0.5 }
    ]
  },
  "EMP102": {
    "name": "Sarah Connor",
    "join_date": "2020-06-15",
    "role": "Assembly Line Supervisor",
    "department": "Manufacturing Operations",
    "starting_points": 7.0,
    "current_points": 7.0,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 16,
    "vacation_hours": 48,
    "freeze_history": [
      { "start": "2025-01-11", "end": "2025-05-11", "status": "Completed" }
    ],
    "schedule": [
      { "date": "2025-01-10", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "No call no show.", "roll_on": "2026-01-10" },
      { "date": "2025-01-11", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-2.0)", "dto": false, "notes": "Late reported absence. Warning level triggered.", "roll_on": "2026-01-11" }
    ],
    "history": [
      { "date": "2025-01-10", "code": "IANS", "points": -3.0, "balance": 4.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-01-10" },
      { "date": "2025-01-11", "code": "LTNC", "points": -2.0, "balance": 2.0, "status": "Active Deduction", "details": "Late reported absence (Freeze Period Triggered)", "roll_on": "2026-01-11" },
      { "date": "2026-01-10", "code": "ROLL-ON", "points": 3.0, "balance": 5.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2025-01-10 IANS deduction" },
      { "date": "2026-01-11", "code": "ROLL-ON", "points": 2.0, "balance": 7.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2025-01-11 LTNC deduction" }
    ],
    "warnings": [
      { "date": "2025-01-11", "level": "Written Warning (<= 2.0)", "points": 2.0 }
    ]
  },
  "EMP103": {
    "name": "Marcus Wright",
    "join_date": "2024-01-10",
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
      { "date": "2025-01-01", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" }
    ],
    "history": [],
    "warnings": []
  },
  "EMP104": {
    "name": "John Connor",
    "join_date": "2023-05-20",
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
      { "date": "2025-01-05", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-01-12", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-01-20", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie" },
      { "date": "2025-02-15", "code": "IANS", "points": -3.0, "balance": 4.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-02-15" },
      { "date": "2025-03-01", "code": "IANS", "points": -3.0, "balance": 1.0, "status": "Active Deduction", "details": "NCNS (Freeze Triggered)", "roll_on": "2026-03-01" }
    ],
    "warnings": [
      { "date": "2025-02-15", "level": "Written Warning (<= 2.0)", "points": 4.0 },
      { "date": "2025-03-01", "level": "Termination Warning (<= 1.0)", "points": 1.0 }
    ]
  },
  "EMP105": {
    "name": "Kyle Reese",
    "join_date": "2021-08-01",
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
      { "date": "2025-01-10", "code": "IANS", "points": -3.0, "balance": 4.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2026-01-10" },
      { "date": "2025-02-20", "code": "LTNC", "points": -2.0, "balance": 2.0, "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2026-02-20" },
      { "date": "2025-04-10", "code": "LTNC", "points": -2.0, "balance": 0.0, "status": "Active Deduction", "details": "Late reported absence", "roll_on": "2026-04-10" }
    ],
    "warnings": [
      { "date": "2025-02-20", "level": "Written Warning (<= 2.0)", "points": 2.0 },
      { "date": "2025-04-10", "level": "Termination Memo (<= 0.0)", "points": 0.0 }
    ]
  },
  "EMP106": {
    "name": "Ellen Ripley",
    "join_date": "2020-11-12",
    "role": "Inventory Supervisor",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 7.0,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 3,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 40,
    "vacation_hours": 160,
    "freeze_history": [],
    "schedule": [
      { "date": "2024-05-10", "base": "SW (Scheduled Work)", "actual": "LTDR (Personal)", "status": "Exempted (FMLA)", "dto": false, "notes": "FMLA approved medical leave.", "supervisor_note": "FMLA leave approved by HR for family surgery." },
      { "date": "2024-09-12", "base": "SW (Scheduled Work)", "actual": "LTDR (Personal)", "status": "Exempted (FMLA)", "dto": false, "notes": "FMLA approved medical leave.", "supervisor_note": "FMLA protected sickness." },
      { "date": "2025-03-04", "base": "SW (Scheduled Work)", "actual": "skps (Protected Sick)", "status": "Exempted (FMLA)", "dto": false, "notes": "FMLA protected sick period.", "supervisor_note": "FMLA protected day." }
    ],
    "history": [
      { "date": "2024-05-10", "code": "LTDR", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "FMLA Leave Approved" },
      { "date": "2024-09-12", "code": "LTDR", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "FMLA Leave Approved" },
      { "date": "2025-03-04", "code": "skps", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "FMLA Protected Sick Leave" }
    ],
    "warnings": []
  },
  "EMP107": {
    "name": "Peter Parker",
    "join_date": "2025-01-05",
    "role": "Safety Inspector",
    "department": "Quality Assurance",
    "starting_points": 7.0,
    "current_points": 6.5,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 3,
    "sick_balance_hours": 32,
    "vacation_hours": 40,
    "freeze_history": [],
    "schedule": [
      { "date": "2025-02-01", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #1" },
      { "date": "2025-02-15", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #2" },
      { "date": "2025-03-01", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Excused", "dto": false, "notes": "Freebie Lo #3" },
      { "date": "2025-04-10", "base": "SW (Scheduled Work)", "actual": "Lo (Late <=14m)", "status": "Point Deducted (-0.5)", "dto": false, "notes": "Late arrival. 4th Lo in 12m rolling period.", "roll_on": "2026-04-10" }
    ],
    "history": [
      { "date": "2025-02-01", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo" },
      { "date": "2025-02-15", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo" },
      { "date": "2025-03-01", "code": "Lo", "points": 0.0, "balance": 7.0, "status": "Exempted", "details": "Freebie Lo" },
      { "date": "2025-04-10", "code": "Lo", "points": -0.5, "balance": 6.5, "status": "Active Deduction", "details": "Late <=14m (4th occurrence)", "roll_on": "2026-04-10" },
      { "date": "2026-04-10", "code": "ROLL-ON", "points": 0.5, "balance": 7.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2025-04-10 Lo deduction" }
    ],
    "warnings": []
  },
  "EMP108": {
    "name": "Tony Stark",
    "join_date": "2022-10-01",
    "role": "Machinist Tech",
    "department": "Facilities",
    "starting_points": 7.0,
    "current_points": 4.5,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 1,
    "freebies_used": 0,
    "sick_balance_hours": 24,
    "vacation_hours": 96,
    "freeze_history": [
      { "start": "2023-05-10", "end": "2023-09-10", "status": "Completed" }
    ],
    "schedule": [
      { "date": "2023-01-10", "base": "SW (Scheduled Work)", "actual": "IANS (No Call No Show)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "Missed shift.", "roll_on": "2024-01-10" },
      { "date": "2023-05-10", "base": "SW (Scheduled Work)", "actual": "LTNC (Late Reported)", "status": "Point Deducted (-3.0)", "dto": false, "notes": "Dropped to 1.0 points. Freeze started.", "roll_on": "2024-05-10" },
      { "date": "2023-07-15", "base": "SW (Scheduled Work)", "actual": "LT (Late >14m)", "status": "Point Deducted (-0.5)", "dto": false, "notes": "Deduction occurred during active freeze. Score drops to 0.5.", "roll_on": "2024-07-15" }
    ],
    "history": [
      { "date": "2023-01-10", "code": "IANS", "points": -3.0, "balance": 4.0, "status": "Active Deduction", "details": "No call no show", "roll_on": "2024-01-10" },
      { "date": "2023-05-10", "code": "IANS", "points": -3.0, "balance": 1.0, "status": "Active Deduction", "details": "NCNS (Freeze Triggered)", "roll_on": "2024-05-10" },
      { "date": "2023-07-15", "code": "LT", "points": -0.5, "balance": 0.5, "status": "Active Deduction", "details": "Late >14m (Deducted during freeze)", "roll_on": "2024-07-15" },
      { "date": "2024-01-10", "code": "ROLL-ON", "points": 3.0, "balance": 3.5, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-01-10 IANS deduction" },
      { "date": "2024-05-10", "code": "ROLL-ON", "points": 3.0, "balance": 6.5, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-05-10 IANS deduction" },
      { "date": "2024-07-15", "code": "ROLL-ON", "points": 0.5, "balance": 7.0, "status": "Rolled-on (Expired)", "details": "Recovery of 2023-07-15 LT deduction" }
    ],
    "warnings": [
      { "date": "2023-05-10", "level": "Termination Warning (<= 1.0)", "points": 1.0 }
    ]
  },
  "EMP109": {
    "name": "Bruce Wayne",
    "join_date": "2023-09-15",
    "role": "Logistics Planner",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 7.0,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 40,
    "vacation_hours": 88,
    "freeze_history": [],
    "schedule": [
      { "date": "2024-11-20", "base": "DTO (Day Trade)", "actual": "DO (Day Off)", "status": "Swapped", "dto": true, "trade_partner": "EMP101", "notes": "Traded shift with EMP101." },
      { "date": "2025-02-10", "base": "DTO (Day Trade)", "actual": "DO (Day Off)", "status": "Swapped", "dto": true, "trade_partner": "EMP103", "notes": "Traded shift with EMP103." }
    ],
    "history": [],
    "warnings": []
  },
  "EMP110": {
    "name": "Clark Kent",
    "join_date": "2025-06-01",
    "role": "Receiving Agent",
    "department": "Logistics & Fulfillment",
    "starting_points": 7.0,
    "current_points": 7.0,
    "warning_status": "Good Standing",
    "fmla_approved_cases": 0,
    "excused_absences": 0,
    "freebies_used": 0,
    "sick_balance_hours": 40,
    "vacation_hours": 32,
    "freeze_history": [],
    "schedule": [
      { "date": "2025-07-01", "base": "SW (Scheduled Work)", "actual": "SW (Present)", "status": "Normal", "dto": false, "notes": "" }
    ],
    "history": [],
    "warnings": []
  }
};
