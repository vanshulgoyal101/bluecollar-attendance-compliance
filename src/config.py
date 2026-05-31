import os
import yaml
from typing import Dict, Any

class PolicyConfig:
    def __init__(self, config_path: str = "config.yaml"):
        if not os.path.exists(config_path):
            # Try loading from parent directory just in case run from main vs test
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            
        policy = data.get("policy", {})
        self.start_points: float = float(policy.get("start_points", 7.0))
        self.roll_off_months: int = int(policy.get("roll_off_months", 12))
        
        freeze = policy.get("freeze", {})
        self.freeze_trigger: float = float(freeze.get("trigger_points", 1.0))
        self.freeze_duration_months: int = int(freeze.get("duration_months", 4))
        
        warnings = policy.get("warnings", {})
        self.warning_written: float = float(warnings.get("written", 2.0))
        self.warning_termination_warning: float = float(warnings.get("termination_warning", 1.0))
        self.warning_termination: float = float(warnings.get("termination", 0.0))
        
        self.infractions: Dict[str, float] = {
            k: float(v) for k, v in policy.get("infractions", {}).items()
        }
        self.lo_freebies: int = int(policy.get("lo_freebies", 3))

    def get_deduction(self, actual_code: str) -> float:
        return self.infractions.get(actual_code, 0.0)
