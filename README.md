# Workforce Attendance Compliance Engine & Dashboard

An AI-native compliance engine and interactive dashboard built to automate workforce attendance policies, enforce union/corporate guidelines fairly, and parse unstructured shift logs for regulatory excusals (like FMLA). 

This project solves operational inefficiencies in blue-collar operations using a combination of **deterministic policy engines** and **Retrieval-Augmented Generation (RAG) LLM note analysis** to automate administrative friction and investigative reviews.

---

## 📋 The "No-Fault" Attendance Policy Rules

The compliance engine evaluates employee actions against a strict, configurable point policy defined in `config.yaml`:

### 1. Point Deductions
All employees start with **7.0 points**. Infractions reduce points as follows:
* **`skps` (Protected Sick Period)**: **0.0 points** (FMLA / legally protected).
* **`skp` (Unprotected Sick)**: **1.0 point**. Multiple consecutive days of sickness are grouped and treated as **one** single unprotected period (deducting 1.0 point total).
* **`LTDR` (Personal Absence)**: **1.0 point** per day.
* **`IANS` (No Call No Show)**: **3.0 points**.
* **`LTNC` (Late Reported Absence)**: **2.0 points**.
* **`LT` (Late Arrival >14 mins)**: **0.5 points**.
* **`Lo` (Late Arrival <=14 mins)**: **0.5 points**. The first **3 `Lo` infractions** in a rolling 12-month period are granted as freebies (**0.0 points** impact).

### 2. Point Expirations & Roll-ons
* Point deductions expire and roll back on (recover) exactly **12 months** after the infraction date.
* Points balance is capped at the maximum starting balance of **7.0**.

### 3. Warning Levels
* **$\le$ 2.0 Points**: Triggers a **Written Warning**.
* **$\le$ 1.0 Points**: Triggers a **Termination Warning** and initiates a **4-month point roll-on freeze period**.
* **$\le$ 0.0 Points**: Triggers the **Termination Memo**.

### 4. The 4-Month Roll-on Freeze
When a points balance falls to or below **1.0**:
* A **4-month freeze period** is activated.
* New point deductions are still applied if new infractions occur.
* No point recovery (roll-on) is allowed to execute during the freeze.
* Once the freeze period ends, any paused or scheduled roll-ons execute instantly.

---

## 🛠 Project Architecture

```
blue_collar_attendance_compliance/
├── config.yaml            # Configurable point rules and thresholds
├── requirements.txt       # Dependencies (LiteLLM, pandas, pytest, pyyaml, pydantic)
├── main.py                # Ingestion and compliance report generator CLI
├── src/
│   ├── config.py          # Policy config loader
│   ├── parser.py          # Raw CSV punch log & JSON notes parser
│   ├── engine.py          # Timeline-based policy calculation engine
│   ├── llm_client.py      # LiteLLM client for notes exception parsing (FMLA, overrides)
│   └── report_generator.py# Generates markdown IRM Briefs and warning letters
├── data/
│   ├── punch_logs.csv     # Mock raw logs database
│   └── supervisor_notes.json# Mock supervisor logs database
├── dashboard/
│   ├── index.html         # Frontend HTML structure
│   ├── index.css          # Blue-white corporate dashboard styles
│   ├── app.js             # Interactive rendering, modals, and scrolling
│   └── data.js            # Mock dataset for 10 employees
├── tests/
│   └── test_engine.py     # Core rules logic unit tests
└── reports/               # Auto-generated HR letters and meeting briefs
```

---

## 🚀 Getting Started

### 1. Requirements & Setup
Make sure you have Python 3.10+ installed. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Compliance Evaluation CLI
The CLI ingests logs and notes, evaluates each employee's history, parses supervisor notes for FMLA/excused statuses, and outputs formatted HR reports:
```bash
python3 main.py
```
This generates:
* **IRM Briefs** in `reports/IRM_Brief_EMPxxx.md` (Investigative Review Meeting briefs outlining the trajectory).
* **Warning / Termination Notices** in `reports/Warning_Letter_EMPxxx.md`.

### 3. Run the Unit Test Suite
We have implemented strict test coverages to verify freeze periods, rolling freebie resets, consecutive sick grouping, and basic deductions:
```bash
python3 -m pytest tests/
```

### 4. Run the Interactive Dashboard Locally
To view the front-end dashboard, spin up a lightweight server from the `dashboard` directory:
```bash
cd dashboard
python3 -m http.server 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 📊 Dashboard Views

The application provides a two-dashboard linked tab interface:
1. **Compliance & Escalations**: Tracks point trajectory balances, remaining freebies, active/past freeze states, and features a Warning Letter generator previewer. Clicking a freebie date scrolls smoothly to its row, and clicking on an excused point opens a modal detail popup showing the parsed supervisor note.
2. **Operational Shift & Schedules**: Tracks remaining protected sick balances (starting at 40 hours/year), vacation days, base shift calendars, trade-off shift swaps (DTOs), and supervisor notes logs.
