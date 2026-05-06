"""
HospitalIQ ML Model Validator
Comprehensive validation: confusion matrix, precision/recall/F1, ROC-AUC,
calibration, threshold tuning, imbalance detection, full accuracy report.
"""
import os, sys, json, random, asyncio
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

from sklearn.metrics import (
    confusion_matrix, classification_report, precision_recall_fscore_support,
    roc_curve, auc, accuracy_score, f1_score
)
from sklearn.calibration import calibration_curve
from sklearn.model_selection import StratifiedKFold

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), "ml_models")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "../../uploads/reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class SymptomModelValidator:
    """Validates the symptom-disease multi-class predictor."""

    def __init__(self):
        from backend.ml.symptom_disease_predictor import (
            MODEL_RF_PATH, MODEL_XGB_PATH, SYMPTOM_LIST_PATH, DISEASE_LIST_PATH
        )
        self.rf_model = joblib.load(MODEL_RF_PATH) if os.path.exists(MODEL_RF_PATH) else None
        self.xgb_model = joblib.load(MODEL_XGB_PATH) if os.path.exists(MODEL_XGB_PATH) else None
        self.symptoms = joblib.load(SYMPTOM_LIST_PATH) if os.path.exists(SYMPTOM_LIST_PATH) else []
        self.diseases = joblib.load(DISEASE_LIST_PATH) if os.path.exists(DISEASE_LIST_PATH) else []
        self.results = {}

    async def _generate_test_data(self):
        """Generate held-out test data from DB mappings."""
        from backend.database import AsyncSessionLocal
        from backend.models.symptom_models import Symptom, Disease, DiseaseSymptomMapping
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            symp_res = await session.execute(select(Symptom))
            symptoms_data = sorted(symp_res.scalars().all(), key=lambda s: s.id)
            dis_res = await session.execute(select(Disease))
            diseases_data = sorted(dis_res.scalars().all(), key=lambda d: d.id)
            map_res = await session.execute(select(DiseaseSymptomMapping))
            mappings = map_res.scalars().all()

        symptom_names = [s.name for s in symptoms_data]
        disease_names = [d.name for d in diseases_data]
        symptom_id_to_idx = {s.id: i for i, s in enumerate(symptoms_data)}
        disease_id_to_name = {d.id: d.name for d in diseases_data}

        disease_to_symp_idx = {d.id: [] for d in diseases_data}
        for m in mappings:
            if m.symptom_id in symptom_id_to_idx:
                disease_to_symp_idx[m.disease_id].append(symptom_id_to_idx[m.symptom_id])

        X, y = [], []
        random.seed(99)  # Different seed from training (42) for true holdout
        for d_id, symp_indices in disease_to_symp_idx.items():
            if not symp_indices:
                continue
            d_name = disease_id_to_name[d_id]
            for _ in range(30):
                num = random.randint(max(1, len(symp_indices) // 2), len(symp_indices))
                subset = random.sample(symp_indices, num)
                vec = np.zeros(len(symptom_names))
                for idx in subset:
                    vec[idx] = 1
                X.append(vec)
                y.append(d_name)

        disease_to_idx = {name: i for i, name in enumerate(disease_names)}
        X = np.array(X)
        y_encoded = np.array([disease_to_idx[label] for label in y])
        return X, y_encoded, y, disease_names

    def _confusion_matrix(self, y_true, y_pred, labels):
        """Generate and save confusion matrix heatmap."""
        cm = confusion_matrix(y_true, y_pred, labels=range(len(labels)))
        fig, ax = plt.subplots(figsize=(max(12, len(labels)), max(10, len(labels) * 0.8)))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=labels, yticklabels=labels, ax=ax,
                    linewidths=0.5, linecolor='#334155')
        ax.set_xlabel("Predicted", fontsize=12, color="#94a3b8")
        ax.set_ylabel("Actual", fontsize=12, color="#94a3b8")
        ax.set_title("Symptom-Disease Model - Confusion Matrix", fontsize=14, color="white", pad=15)
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#1e293b")
        ax.tick_params(colors="#94a3b8", labelsize=7)
        plt.tight_layout()
        path = os.path.join(REPORTS_DIR, "confusion_matrix.png")
        fig.savefig(path, dpi=150, facecolor="#0f172a")
        plt.close(fig)
        print(f"  [OK] Confusion matrix saved: {path}")

        # Extract TP/FP/TN/FN per class
        per_class = {}
        for i, label in enumerate(labels):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            tn = cm.sum() - tp - fp - fn
            per_class[label] = {"TP": int(tp), "FP": int(fp), "TN": int(tn), "FN": int(fn)}
        return per_class

    def _precision_recall_f1(self, y_true, y_pred, labels):
        """Calculate per-disease precision, recall, F1."""
        # Only use label indices that actually appear in data
        present = sorted(set(np.concatenate([np.unique(y_true), np.unique(y_pred)])))
        present_names = [labels[i] for i in present if i < len(labels)]

        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=present, zero_division=0
        )
        report = classification_report(
            y_true, y_pred, labels=present, target_names=present_names,
            zero_division=0, output_dict=True
        )
        print("\n  Classification Report:")
        print(classification_report(
            y_true, y_pred, labels=present, target_names=present_names, zero_division=0
        ))

        metrics = {}
        for idx, i in enumerate(present):
            if i < len(labels):
                metrics[labels[i]] = {
                    "precision": round(float(precision[idx]), 4),
                    "recall": round(float(recall[idx]), 4),
                    "f1_score": round(float(f1[idx]), 4),
                    "support": int(support[idx])
                }
        metrics["macro_avg"] = {
            "precision": round(float(report["macro avg"]["precision"]), 4),
            "recall": round(float(report["macro avg"]["recall"]), 4),
            "f1_score": round(float(report["macro avg"]["f1-score"]), 4),
        }
        metrics["weighted_avg"] = {
            "precision": round(float(report["weighted avg"]["precision"]), 4),
            "recall": round(float(report["weighted avg"]["recall"]), 4),
            "f1_score": round(float(report["weighted avg"]["f1-score"]), 4),
        }

        path = os.path.join(REPORTS_DIR, "precision_recall_f1.json")
        with open(path, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"  [OK] Precision/Recall/F1 saved: {path}")
        return metrics

    def _roc_auc(self, X, y_true, labels):
        """Generate ROC curves and calculate AUC per disease."""
        probs = self.rf_model.predict_proba(X)
        n_classes = len(labels)
        auc_scores = {}

        fig, ax = plt.subplots(figsize=(10, 8))
        colors = plt.cm.tab20(np.linspace(0, 1, n_classes))

        for i in range(n_classes):
            y_bin = (y_true == i).astype(int)
            if y_bin.sum() == 0 or i >= probs.shape[1]:
                continue
            fpr, tpr, _ = roc_curve(y_bin, probs[:, i])
            roc_auc = auc(fpr, tpr)
            auc_scores[labels[i]] = round(float(roc_auc), 4)
            ax.plot(fpr, tpr, color=colors[i], lw=1.5, alpha=0.7,
                    label=f"{labels[i][:15]} (AUC={roc_auc:.2f})")

        ax.plot([0, 1], [0, 1], 'w--', lw=1, alpha=0.3)
        ax.set_xlabel("False Positive Rate", color="#94a3b8")
        ax.set_ylabel("True Positive Rate", color="#94a3b8")
        ax.set_title("ROC Curves - Per Disease", color="white", pad=10)
        ax.legend(loc="lower right", fontsize=6, facecolor="#1e293b",
                  edgecolor="#334155", labelcolor="#94a3b8")
        ax.set_facecolor("#1e293b")
        fig.patch.set_facecolor("#0f172a")
        ax.tick_params(colors="#94a3b8")
        plt.tight_layout()
        path = os.path.join(REPORTS_DIR, "roc_curves.png")
        fig.savefig(path, dpi=150, facecolor="#0f172a")
        plt.close(fig)

        macro_auc = round(float(np.mean(list(auc_scores.values()))), 4) if auc_scores else 0.0
        auc_scores["macro_average"] = macro_auc
        print(f"  [OK] ROC curves saved: {path}")
        print(f"  [OK] Macro-average AUC: {macro_auc}")
        return auc_scores

    def _calibration(self, X, y_true, labels):
        """Check prediction calibration and generate calibration curve."""
        probs = self.rf_model.predict_proba(X)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot([0, 1], [0, 1], 'w--', lw=1, alpha=0.3, label="Perfectly Calibrated")

        calibration_data = {}
        for i in range(min(6, len(labels))):  # Top 6 diseases
            y_bin = (y_true == i).astype(int)
            if y_bin.sum() < 5 or i >= probs.shape[1]:
                continue
            try:
                prob_true, prob_pred = calibration_curve(y_bin, probs[:, i], n_bins=8, strategy="uniform")
                ax.plot(prob_pred, prob_true, marker='o', lw=1.5, markersize=4,
                        label=f"{labels[i][:15]}")
                # Calculate calibration error
                ece = float(np.mean(np.abs(prob_true - prob_pred)))
                calibration_data[labels[i]] = {
                    "expected_calibration_error": round(ece, 4),
                    "well_calibrated": ece < 0.1
                }
            except Exception:
                continue

        ax.set_xlabel("Mean Predicted Probability", color="#94a3b8")
        ax.set_ylabel("Fraction of Positives", color="#94a3b8")
        ax.set_title("Calibration Curves", color="white", pad=10)
        ax.legend(fontsize=7, facecolor="#1e293b", edgecolor="#334155", labelcolor="#94a3b8")
        ax.set_facecolor("#1e293b")
        fig.patch.set_facecolor("#0f172a")
        ax.tick_params(colors="#94a3b8")
        plt.tight_layout()
        path = os.path.join(REPORTS_DIR, "calibration_curves.png")
        fig.savefig(path, dpi=150, facecolor="#0f172a")
        plt.close(fig)
        print(f"  [OK] Calibration curves saved: {path}")

        poorly_calibrated = [k for k, v in calibration_data.items() if not v["well_calibrated"]]
        if poorly_calibrated:
            print(f"  [!] Poorly calibrated diseases: {poorly_calibrated}")
            print("    -> Recommendation: Apply Platt scaling or isotonic regression")
        else:
            print("  [OK] All analyzed diseases are well-calibrated (ECE < 0.1)")
        return calibration_data

    def _threshold_tuning(self, X, y_true, labels):
        """Find optimal confidence thresholds using Youden's J."""
        probs = self.rf_model.predict_proba(X)
        thresholds = {}

        for i in range(len(labels)):
            y_bin = (y_true == i).astype(int)
            if y_bin.sum() < 5 or i >= probs.shape[1]:
                continue
            fpr, tpr, thresh = roc_curve(y_bin, probs[:, i])
            j_scores = tpr - fpr
            best_idx = np.argmax(j_scores)
            optimal_thresh = float(thresh[best_idx]) * 100
            thresholds[labels[i]] = round(optimal_thresh, 1)

        avg_threshold = round(float(np.mean(list(thresholds.values()))), 1) if thresholds else 50.0

        recommendations = {
            "inconclusive_below": max(20, min(45, round(avg_threshold * 0.5, 0))),
            "low_confidence_below": max(50, min(75, round(avg_threshold * 0.85, 0))),
            "high_confidence_above": max(75, min(90, round(avg_threshold * 1.1, 0))),
            "per_disease_optimal": thresholds,
            "average_optimal_threshold": avg_threshold,
        }
        print(f"  [OK] Average optimal threshold (Youden's J): {avg_threshold}%")
        print(f"    Recommended gates: inconclusive<{recommendations['inconclusive_below']}%, "
              f"low<{recommendations['low_confidence_below']}%, "
              f"high>{recommendations['high_confidence_above']}%")
        return recommendations

    def _misclassification_analysis(self, y_true, y_pred, labels):
        """Find most over/under predicted diseases and top misclassification pairs."""
        cm = confusion_matrix(y_true, y_pred, labels=range(len(labels)))

        # Over-predicted: high FP rate
        fp_rates = {}
        fn_rates = {}
        for i, label in enumerate(labels):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            total_pred = cm[:, i].sum()
            total_actual = cm[i, :].sum()
            fp_rates[label] = round(fp / max(total_pred, 1), 4)
            fn_rates[label] = round(fn / max(total_actual, 1), 4)

        over_predicted = sorted(fp_rates.items(), key=lambda x: x[1], reverse=True)[:5]
        under_predicted = sorted(fn_rates.items(), key=lambda x: x[1], reverse=True)[:5]

        # Top misclassification pairs
        pairs = []
        for i in range(len(labels)):
            for j in range(len(labels)):
                if i != j and cm[i, j] > 0:
                    pairs.append({
                        "actual": labels[i],
                        "predicted_as": labels[j],
                        "count": int(cm[i, j])
                    })
        pairs.sort(key=lambda x: x["count"], reverse=True)

        result = {
            "most_over_predicted": [{"disease": d, "fp_rate": r} for d, r in over_predicted],
            "most_under_predicted": [{"disease": d, "fn_rate": r} for d, r in under_predicted],
            "top_misclassification_pairs": pairs[:5]
        }
        print(f"  [OK] Top over-predicted: {over_predicted[0][0] if over_predicted else 'N/A'}")
        print(f"  [OK] Top under-predicted: {under_predicted[0][0] if under_predicted else 'N/A'}")
        if pairs:
            print(f"  [OK] Top misclass pair: {pairs[0]['actual']} -> {pairs[0]['predicted_as']} ({pairs[0]['count']}x)")
        return result

    def _imbalance_check(self, y_true, labels):
        """Check training data balance across diseases."""
        counts = np.bincount(y_true, minlength=len(labels))
        disease_counts = {labels[i]: int(counts[i]) for i in range(len(labels)) if counts[i] > 0}
        total = sum(disease_counts.values())
        mean_count = total / max(len(disease_counts), 1)

        imbalance_ratio = max(disease_counts.values()) / max(min(disease_counts.values()), 1) if disease_counts else 1

        result = {
            "per_disease_samples": disease_counts,
            "total_samples": total,
            "mean_per_disease": round(mean_count, 1),
            "imbalance_ratio": round(imbalance_ratio, 2),
            "is_balanced": imbalance_ratio < 3.0,
            "recommendation": "Data is balanced" if imbalance_ratio < 3.0
                else "Consider SMOTE oversampling for minority classes"
        }
        print(f"  [OK] Imbalance ratio: {imbalance_ratio:.2f} ({'Balanced' if result['is_balanced'] else 'IMBALANCED'})")
        return result

    async def run_full_validation(self):
        """Execute all validation steps and generate complete report."""
        if not self.rf_model:
            print("ERROR: No trained model found. Train first.")
            return

        print("=" * 60)
        print("  HospitalIQ ML Model Validator")
        print("=" * 60)

        # Generate test data
        print("\n[1/8] Generating test data...")
        X, y_encoded, y_labels, disease_names = await self._generate_test_data()
        y_pred = self.rf_model.predict(X)
        overall_acc = accuracy_score(y_encoded, y_pred)
        overall_f1 = f1_score(y_encoded, y_pred, average="weighted", zero_division=0)
        print(f"  Test samples: {len(X)}, Diseases: {len(disease_names)}")
        print(f"  Overall Accuracy: {overall_acc:.4f}")
        print(f"  Overall F1 (weighted): {overall_f1:.4f}")

        # 1. Confusion Matrix
        print("\n[2/8] Generating confusion matrix...")
        cm_data = self._confusion_matrix(y_encoded, y_pred, disease_names)

        # 2. Precision / Recall / F1
        print("\n[3/8] Calculating precision/recall/F1...")
        prf_metrics = self._precision_recall_f1(y_encoded, y_pred, disease_names)

        # 3. ROC-AUC
        print("\n[4/8] Generating ROC-AUC curves...")
        auc_scores = self._roc_auc(X, y_encoded, disease_names)

        # 4. Calibration
        print("\n[5/8] Checking prediction calibration...")
        cal_data = self._calibration(X, y_encoded, disease_names)

        # 5. Threshold Tuning
        print("\n[6/8] Tuning confidence thresholds (Youden's J)...")
        threshold_recs = self._threshold_tuning(X, y_encoded, disease_names)

        # 6. Misclassification Analysis
        print("\n[7/8] Analyzing misclassifications...")
        misclass = self._misclassification_analysis(y_encoded, y_pred, disease_names)

        # 7. Imbalance Check
        print("\n[8/8] Checking symptom frequency imbalance...")
        imbalance = self._imbalance_check(y_encoded, disease_names)

        # 8. Complete Accuracy Report
        report = {
            "report_generated_at": datetime.utcnow().isoformat(),
            "model_version": "v2.0",
            "model_type": "RandomForestClassifier",
            "overall_accuracy": round(float(overall_acc), 4),
            "overall_f1_weighted": round(float(overall_f1), 4),
            "macro_avg_auc": auc_scores.get("macro_average", 0),
            "test_samples": len(X),
            "diseases_covered": len([d for d in disease_names if np.sum(y_encoded == disease_names.index(d)) > 0]) if disease_names else 0,
            "symptoms_used": len(self.symptoms),
            "per_disease_metrics": prf_metrics,
            "auc_scores": auc_scores,
            "calibration": cal_data,
            "confidence_threshold_recommendations": threshold_recs,
            "misclassification_analysis": misclass,
            "data_imbalance": imbalance,
            "confusion_matrix_per_class": cm_data,
            "training_data_stats": {
                "total_diseases": len(disease_names),
                "total_symptoms": len(self.symptoms),
            }
        }

        report_path = os.path.join(REPORTS_DIR, "model_accuracy_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print("\n" + "=" * 60)
        print("  VALIDATION COMPLETE")
        print("=" * 60)
        print(f"  Overall Accuracy:    {overall_acc:.2%}")
        print(f"  Overall F1 (wt):     {overall_f1:.4f}")
        print(f"  Macro AUC:           {auc_scores.get('macro_average', 'N/A')}")
        print(f"  Data Balanced:       {'Yes' if imbalance['is_balanced'] else 'No'}")
        print(f"  Report saved:        {report_path}")
        print("=" * 60)

        self.results = report
        return report


if __name__ == "__main__":
    validator = SymptomModelValidator()
    asyncio.run(validator.run_full_validation())
