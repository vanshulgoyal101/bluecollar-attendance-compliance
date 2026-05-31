import os
import json
from src.config import PolicyConfig
from src.parser import DataIngestion
from src.llm_client import LLMComplianceClient
from src.engine import ComplianceEngine
from src.report_generator import ComplianceReportGenerator

def main():
    print("🚀 Initializing Blue-Collar Attendance Compliance Agent...")
    
    # Load configuration
    config = PolicyConfig("config.yaml")
    
    # Initialize LLM Client (will fallback to mock logic automatically if API keys are missing)
    llm_client = LLMComplianceClient()
    
    # Initialize compliance rules engine
    engine = ComplianceEngine(config, llm_client)
    
    # Load mock datasets
    csv_path = os.path.join("data", "punch_logs.csv")
    json_path = os.path.join("data", "supervisor_notes.json")
    
    print(f"📂 Loading punch logs from: {csv_path}")
    print(f"📂 Loading supervisor notes from: {json_path}")
    
    punch_df = DataIngestion.load_punch_logs(csv_path)
    notes = DataIngestion.load_supervisor_notes(json_path)
    
    # Identify unique employee IDs
    employees = punch_df["employee_id"].unique()
    print(f"👥 Found {len(employees)} employee records to evaluate.")
    
    # Create reports directory if it doesn't exist
    os.makedirs("reports", exist_ok=True)
    
    # Process compliance for each employee
    for emp_id in employees:
        print(f"\nEvaluating Employee {emp_id}...")
        results = engine.process_employee_compliance(emp_id, punch_df, notes)
        
        print(f"   📊 Current Point Balance: {results['current_points']} / {config.start_points}")
        print(f"   ⚠️  Warnings Triggered: {len(results['warnings'])}")
        print(f"   ❄️  Freeze Periods Active/Scheduled: {len(results['freeze_periods'])}")
        
        # Generate and save IRM report
        irm_brief = ComplianceReportGenerator.generate_irm_brief(emp_id, results)
        report_path = os.path.join("reports", f"IRM_Brief_{emp_id}.md")
        with open(report_path, "w") as f:
            f.write(irm_brief)
        print(f"   📝 Generated IRM Brief: {report_path}")
        
        # If warning triggered, generate letters
        if results['warnings']:
            latest_warning = results['warnings'][-1]
            warning_letter = ComplianceReportGenerator.generate_warning_letter(
                emp_id, 
                latest_warning["level"], 
                results["current_points"]
            )
            letter_path = os.path.join("reports", f"Warning_Letter_{emp_id}.md")
            with open(letter_path, "w") as f:
                f.write(warning_letter)
            print(f"   ✉️  Generated Warning Letter: {letter_path}")

    print("\n✅ Compliance evaluation completed successfully! All reports saved to the 'reports/' directory.")

if __name__ == "__main__":
    main()
