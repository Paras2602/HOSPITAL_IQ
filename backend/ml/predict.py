"""
Prediction engine with SHAP + LIME explainability.
"""
import os, json, pickle
import numpy as np
import pandas as pd
import shap
import lime.lime_tabular
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")

_model_cache: dict = {}
_meta_cache: dict = {}


def _load_model(disease: str):
    if disease not in _model_cache:
        model_path = os.path.join(MODEL_DIR, f"{disease}_model.pkl")
        meta_path = os.path.join(MODEL_DIR, f"{disease}_meta.json")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model for {disease} not found. Run: python -m backend.ml.train_models"
            )
        with open(model_path, "rb") as f:
            _model_cache[disease] = pickle.load(f)
        with open(meta_path) as f:
            _meta_cache[disease] = json.load(f)
    return _model_cache[disease], _meta_cache[disease]


def _risk_label(prob: float) -> str:
    if prob < 0.35:
        return "low"
    elif prob < 0.65:
        return "moderate"
    return "high"


def _recommendations(disease: str, label: str) -> str:
    recs = {
        "diabetes": {
            "low": "Maintain healthy diet. Exercise 30 min/day. Annual glucose check.",
            "moderate": "Monitor blood sugar regularly. Reduce refined carbs. Consult endocrinologist.",
            "high": "Immediate endocrinology consult. HbA1c test required. Strict diet control.",
        },
        "heart": {
            "low": "Regular cardiac screening. Low-fat diet. Aerobic exercise.",
            "moderate": "Cardiology consult recommended. Monitor BP and cholesterol. Lifestyle changes.",
            "high": "Urgent cardiology evaluation. ECG and stress test required. Medication review.",
        },
        "ckd": {
            "low": "Monitor kidney function annually. Stay hydrated. Limit NSAIDs.",
            "moderate": "Nephrology consult. Limit protein/salt. Monitor creatinine and eGFR.",
            "high": "Immediate nephrology evaluation. Assess for dialysis need. Strict diet.",
        },
        "liver": {
            "low": "Annual liver function tests. Avoid hepatotoxic drugs. Limit alcohol.",
            "moderate": "Hepatology consult. Ultrasound abdomen. Avoid alcohol completely.",
            "high": "Urgent hepatology evaluation. Liver biopsy may be indicated. Hospital admission.",
        },
    }
    return recs.get(disease, {}).get(label, "Consult your physician.")


def _plot_to_base64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return encoded


def predict(disease: str, input_data: dict) -> dict:
    model, meta = _load_model(disease)
    features = meta["features"]

    # Build input DataFrame
    row = {f: input_data.get(f, 0) for f in features}
    X = pd.DataFrame([row], columns=features)

    # Prediction
    prob = float(model.predict_proba(X)[0][1])
    label = _risk_label(prob)

    # SHAP
    clf = model.named_steps["clf"]
    scaler = model.named_steps["scaler"]
    X_scaled = scaler.transform(X)

    explainer = shap.TreeExplainer(clf)
    shap_vals = explainer.shap_values(X_scaled)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]
    shap_dict = {features[i]: round(float(shap_vals[0][i]), 4) for i in range(len(features))}

    # SHAP bar plot
    fig, ax = plt.subplots(figsize=(8, 4))
    sorted_items = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
    names = [k for k, _ in sorted_items]
    vals = [v for _, v in sorted_items]
    colors = ["#ef4444" if v > 0 else "#22c55e" for v in vals]
    ax.barh(names[::-1], vals[::-1], color=colors[::-1])
    ax.axvline(0, color="white", linewidth=0.8, linestyle="--")
    ax.set_xlabel("SHAP Value (Impact on Prediction)", color="#94a3b8")
    ax.set_title(f"SHAP Feature Contributions — {disease.title()} Risk", color="white", pad=10)
    ax.set_facecolor("#1e293b")
    fig.patch.set_facecolor("#0f172a")
    ax.tick_params(colors="#94a3b8")
    ax.spines[:].set_color("#334155")
    shap_plot = _plot_to_base64(fig)

    # LIME
    lime_dict = {}
    try:
        # Use saved background sample if available, else fallback to random (scaled)
        background = np.array(meta.get("background_sample", np.random.randn(100, len(features))))
        
        lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=background,
            feature_names=features,
            class_names=["No Disease", "Disease"],
            mode="classification",
        )
        # Pass the classifier (not the full pipeline) to avoid double scaling
        # and pass the already scaled X_scaled[0]
        lime_exp = lime_explainer.explain_instance(
            X_scaled[0],
            clf.predict_proba,
            num_features=min(6, len(features)),
        )
        lime_dict = {k: round(v, 4) for k, v in lime_exp.as_list()}
    except Exception as e:
        lime_dict = {"error": str(e)}

    return {
        "risk_probability": round(prob, 4),
        "risk_percent": round(prob * 100, 1),
        "risk_label": label,
        "shap_values": shap_dict,
        "shap_plot_base64": shap_plot,
        "lime_explanation": lime_dict,
        "recommendations": _recommendations(disease, label),
        "model_version": "v1.0",
        "features_used": features,
    }
