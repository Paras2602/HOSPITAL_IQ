import os
import sys

def verify_audit_completeness():
    required_actions = [
        "symptoms_submitted",
        "prediction_generated",
        "shared_with_doctor",
        "doctor_reviewed",
        "doctor_confirmed",
        "doctor_overridden",
        "prescription_created",
        "prescription_approved",
        "prescription_downloaded",
        "high_risk_alert_triggered",
        "model_version_used"
    ]
    
    # We will search the backend/routers directory for these string literals
    routers_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "routers")
    found_actions = set()
    
    for root, dirs, files in os.walk(routers_dir):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    for action in required_actions:
                        if action in content:
                            found_actions.add(action)
                            
    print("Audit Trail Verification Results:")
    print("-" * 40)
    for action in required_actions:
        status = "PASS" if action in found_actions else "FAIL"
        print(f"[{status}] {action}")
        
    missing = [a for a in required_actions if a not in found_actions]
    if missing:
        print("\nMissing Audit Logs:")
        for m in missing:
            print(f"- {m}")
        sys.exit(1)
    else:
        print("\nAll required audit actions are implemented!")
        sys.exit(0)

if __name__ == "__main__":
    verify_audit_completeness()
