import pandas as pd
import json
import os
from typing import List, Dict, Any

class DataIngestion:
    @staticmethod
    def load_punch_logs(csv_path: str) -> pd.DataFrame:
        """
        Loads the CSV punch logs.
        Expected columns: employee_id, date, base_code, actual_code
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Punch logs CSV not found at {csv_path}")
        
        df = pd.read_csv(csv_path)
        required_cols = {"employee_id", "date", "base_code", "actual_code"}
        if not required_cols.issubset(df.columns):
            raise ValueError(f"CSV must contain columns: {required_cols}")
            
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["employee_id"] = df["employee_id"].astype(str)
        return df

    @staticmethod
    def load_supervisor_notes(json_path: str) -> List[Dict[str, Any]]:
        """
        Loads the supervisor notes JSON.
        Expected structure: List of dicts with: employee_id, date, note
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Supervisor notes JSON not found at {json_path}")
            
        with open(json_path, "r") as f:
            notes = json.load(f)
            
        # Standardize formats
        for note in notes:
            note["employee_id"] = str(note["employee_id"])
            note["date"] = pd.to_datetime(note["date"]).date()
            
        return notes
