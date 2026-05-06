"""
HospitalIQ Model Registry - Version tracking for ML models.
Tracks training history, accuracy metrics, and provides model info API data.
"""
import os
import json
from datetime import datetime

REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "ml_models")
REGISTRY_PATH = os.path.join(REGISTRY_DIR, "model_registry.json")
os.makedirs(REGISTRY_DIR, exist_ok=True)


def _load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {"current_version": None, "models": []}


def _save_registry(registry: dict):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, default=str)


def register_model(
    accuracy: float = 0.0,
    f1_score: float = 0.0,
    auc_score: float = 0.0,
    training_samples: int = 0,
    diseases_covered: int = 0,
    symptoms_used: int = 0,
    model_file: str = "symptom_disease_model_rf.pkl",
    triggered_by: str = "system",
    parameters: dict = None,
) -> dict:
    """Register a new model version after training."""
    registry = _load_registry()
    models = registry.get("models", [])

    # Determine next version
    if models:
        last = models[-1]["version"]
        parts = last.lstrip("v").split(".")
        major, minor = int(parts[0]), int(parts[1])
        # Bump minor; bump major if accuracy improved significantly
        if accuracy > 0.95:
            new_version = f"v{major + 1}.0"
        else:
            new_version = f"v{major}.{minor + 1}"
    else:
        new_version = "v2.0"

    entry = {
        "version": new_version,
        "trained_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "accuracy": round(accuracy, 4),
        "f1_score": round(f1_score, 4),
        "auc_score": round(auc_score, 4),
        "training_samples": training_samples,
        "diseases_covered": diseases_covered,
        "symptoms_used": symptoms_used,
        "model_file": model_file,
        "triggered_by": triggered_by,
        "parameters": parameters or {
            "n_estimators": 200,
            "max_depth": 20,
            "model_type": "RandomForestClassifier"
        },
    }

    models.append(entry)
    registry["current_version"] = new_version
    registry["models"] = models
    _save_registry(registry)
    print(f"[ModelRegistry] Registered {new_version} (acc={accuracy:.4f}, f1={f1_score:.4f})")
    return entry


def get_current_version() -> str:
    registry = _load_registry()
    return registry.get("current_version", "v1.0")


def get_current_model_info() -> dict:
    """Return info for the current active model version."""
    registry = _load_registry()
    version = registry.get("current_version")
    if not version or not registry.get("models"):
        return {
            "version": "v1.0",
            "trained_at": "Unknown",
            "accuracy": 0.0,
            "f1_score": 0.0,
            "auc_score": 0.0,
            "diseases_covered": 0,
            "symptoms_used": 0,
        }
    current = registry["models"][-1]
    return current


def get_all_versions() -> list:
    registry = _load_registry()
    return registry.get("models", [])


if __name__ == "__main__":
    # Seed initial registry from latest validation report
    reports_dir = os.path.join(os.path.dirname(__file__), "../../uploads/reports")
    report_path = os.path.join(reports_dir, "model_accuracy_report.json")

    if os.path.exists(report_path):
        with open(report_path) as f:
            report = json.load(f)
        entry = register_model(
            accuracy=report.get("overall_accuracy", 0),
            f1_score=report.get("overall_f1_weighted", 0),
            auc_score=report.get("macro_avg_auc", 0),
            training_samples=report.get("test_samples", 0),
            diseases_covered=report.get("training_data_stats", {}).get("total_diseases", 0),
            symptoms_used=report.get("training_data_stats", {}).get("total_symptoms", 0),
            triggered_by="model_validator",
        )
        print(f"Registry seeded: {json.dumps(entry, indent=2)}")
    else:
        print("No validation report found. Run model_validator.py first.")
