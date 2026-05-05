"""
ML Training Script — generates synthetic data and trains 4 XGBoost classifiers.
Run once: python -m backend.ml.train_models
"""
import os, json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
import pickle

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(MODEL_DIR, exist_ok=True)

np.random.seed(42)
N = 3000


def train_diabetes():
    df = pd.DataFrame({
        "Pregnancies": np.random.randint(0, 17, N),
        "Glucose": np.random.normal(120, 30, N).clip(50, 250),
        "BloodPressure": np.random.normal(72, 12, N).clip(40, 130),
        "SkinThickness": np.random.normal(28, 10, N).clip(0, 80),
        "Insulin": np.random.normal(80, 60, N).clip(0, 400),
        "BMI": np.random.normal(32, 6, N).clip(15, 60),
        "DiabetesPedigreeFunction": np.random.uniform(0.08, 2.4, N),
        "Age": np.random.randint(18, 80, N),
    })
    risk = (
        (df["Glucose"] > 140).astype(int) * 3
        + (df["BMI"] > 30).astype(int) * 2
        + (df["Age"] > 45).astype(int)
        + (df["Insulin"] > 150).astype(int)
        + np.random.randint(0, 2, N)
    )
    df["Outcome"] = (risk >= 4).astype(int)

    X, y = df.drop("Outcome", axis=1), df["Outcome"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                              use_label_encoder=False, eval_metric="logloss", random_state=42))
    ])
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"[Diabetes] Accuracy: {score:.3f}")
    
    # Save a small sample of training data for LIME background (scaled)
    X_sample = model.named_steps["scaler"].transform(X_train[:100]).tolist()
    
    meta = {
        "features": list(X.columns), 
        "label": "Diabetic (1) / No (0)", 
        "accuracy": round(score, 3),
        "background_sample": X_sample
    }
    _save(model, meta, "diabetes")


def train_heart():
    df = pd.DataFrame({
        "age": np.random.randint(30, 80, N),
        "sex": np.random.randint(0, 2, N),
        "cp": np.random.randint(0, 4, N),
        "trestbps": np.random.normal(130, 18, N).clip(90, 200),
        "chol": np.random.normal(246, 50, N).clip(150, 450),
        "fbs": np.random.randint(0, 2, N),
        "restecg": np.random.randint(0, 3, N),
        "thalach": np.random.normal(150, 23, N).clip(70, 210),
        "exang": np.random.randint(0, 2, N),
        "oldpeak": np.random.uniform(0, 5, N),
        "slope": np.random.randint(0, 3, N),
        "ca": np.random.randint(0, 4, N),
        "thal": np.random.randint(1, 4, N),
    })
    risk = (
        (df["age"] > 55).astype(int) * 2
        + (df["cp"] >= 2).astype(int) * 2
        + (df["chol"] > 240).astype(int)
        + (df["thalach"] < 130).astype(int)
        + (df["ca"] > 1).astype(int)
        + np.random.randint(0, 2, N)
    )
    df["target"] = (risk >= 4).astype(int)

    X, y = df.drop("target", axis=1), df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                              use_label_encoder=False, eval_metric="logloss", random_state=42))
    ])
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"[Heart] Accuracy: {score:.3f}")

    # Save a small sample of training data for LIME background (scaled)
    X_sample = model.named_steps["scaler"].transform(X_train[:100]).tolist()

    meta = {
        "features": list(X.columns), 
        "label": "Heart Disease (1) / No (0)", 
        "accuracy": round(score, 3),
        "background_sample": X_sample
    }
    _save(model, meta, "heart")


def train_ckd():
    df = pd.DataFrame({
        "age": np.random.randint(20, 90, N),
        "bp": np.random.normal(76, 12, N).clip(50, 130),
        "sg": np.random.choice([1.005, 1.010, 1.015, 1.020, 1.025], N),
        "al": np.random.randint(0, 5, N),
        "su": np.random.randint(0, 5, N),
        "bgr": np.random.normal(130, 50, N).clip(50, 500),
        "bu": np.random.normal(50, 30, N).clip(10, 300),
        "sc": np.random.normal(1.7, 1.0, N).clip(0.4, 15),
        "sod": np.random.normal(137, 5, N).clip(110, 160),
        "pot": np.random.normal(4.5, 1.0, N).clip(2.0, 8.0),
        "hemo": np.random.normal(12.5, 2.5, N).clip(4, 18),
        "pcv": np.random.normal(38, 8, N).clip(15, 54),
        "wbcc": np.random.normal(8000, 2500, N).clip(3000, 30000),
        "rbcc": np.random.normal(4.5, 0.8, N).clip(2, 7),
    })
    risk = (
        (df["sc"] > 2.5).astype(int) * 3
        + (df["al"] >= 3).astype(int) * 2
        + (df["hemo"] < 10).astype(int) * 2
        + (df["bu"] > 100).astype(int)
        + (df["bgr"] > 200).astype(int)
        + np.random.randint(0, 2, N)
    )
    df["class"] = (risk >= 5).astype(int)

    X, y = df.drop("class", axis=1), df["class"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                              use_label_encoder=False, eval_metric="logloss", random_state=42))
    ])
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"[CKD] Accuracy: {score:.3f}")

    # Save a small sample of training data for LIME background (scaled)
    X_sample = model.named_steps["scaler"].transform(X_train[:100]).tolist()

    meta = {
        "features": list(X.columns), 
        "label": "CKD (1) / No (0)", 
        "accuracy": round(score, 3),
        "background_sample": X_sample
    }
    _save(model, meta, "ckd")


def train_liver():
    df = pd.DataFrame({
        "Age": np.random.randint(18, 80, N),
        "Gender": np.random.randint(0, 2, N),
        "Total_Bilirubin": np.random.exponential(1.5, N).clip(0.2, 20),
        "Direct_Bilirubin": np.random.exponential(0.5, N).clip(0.1, 10),
        "Alkaline_Phosphotase": np.random.normal(250, 100, N).clip(100, 1200),
        "Alamine_Aminotransferase": np.random.exponential(35, N).clip(5, 400),
        "Aspartate_Aminotransferase": np.random.exponential(40, N).clip(5, 500),
        "Total_Proteins": np.random.normal(6.5, 0.8, N).clip(3, 9),
        "Albumin": np.random.normal(3.5, 0.6, N).clip(1.5, 5.5),
        "Albumin_and_Globulin_Ratio": np.random.normal(1.0, 0.3, N).clip(0.3, 2.5),
    })
    risk = (
        (df["Total_Bilirubin"] > 3).astype(int) * 2
        + (df["Alamine_Aminotransferase"] > 50).astype(int) * 2
        + (df["Alkaline_Phosphotase"] > 300).astype(int)
        + (df["Albumin"] < 3.0).astype(int)
        + np.random.randint(0, 2, N)
    )
    df["Dataset"] = (risk >= 4).astype(int)

    X, y = df.drop("Dataset", axis=1), df["Dataset"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                              use_label_encoder=False, eval_metric="logloss", random_state=42))
    ])
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"[Liver] Accuracy: {score:.3f}")

    # Save a small sample of training data for LIME background (scaled)
    X_sample = model.named_steps["scaler"].transform(X_train[:100]).tolist()

    meta = {
        "features": list(X.columns), 
        "label": "Liver Disease (1) / No (0)", 
        "accuracy": round(score, 3),
        "background_sample": X_sample
    }
    _save(model, meta, "liver")


def _save(model, meta: dict, name: str):
    with open(os.path.join(MODEL_DIR, f"{name}_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(MODEL_DIR, f"{name}_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  -> Saved {name} model")


if __name__ == "__main__":
    print("Training HospitalIQ ML models...")
    train_diabetes()
    train_heart()
    train_ckd()
    train_liver()
    print("All models trained and saved!")
