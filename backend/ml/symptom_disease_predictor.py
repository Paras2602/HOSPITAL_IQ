import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import random
from sqlalchemy import select
from typing import List, Dict, Any
import asyncio

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.database import AsyncSessionLocal
from backend.models.symptom_models import Symptom, Disease, DiseaseSymptomMapping

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), "ml_models")
os.makedirs(ML_MODELS_DIR, exist_ok=True)

MODEL_RF_PATH = os.path.join(ML_MODELS_DIR, "symptom_disease_model_rf.pkl")
MODEL_XGB_PATH = os.path.join(ML_MODELS_DIR, "symptom_disease_model_xgb.pkl")
SYMPTOM_LIST_PATH = os.path.join(ML_MODELS_DIR, "symptom_list.pkl")
DISEASE_LIST_PATH = os.path.join(ML_MODELS_DIR, "disease_list.pkl")

class SymptomDiseasePredictor:
    def __init__(self):
        self.rf_model = None
        self.xgb_model = None
        self.symptoms = []
        self.diseases = []
        
        if os.path.exists(MODEL_RF_PATH):
            self.rf_model = joblib.load(MODEL_RF_PATH)
        if os.path.exists(MODEL_XGB_PATH):
            self.xgb_model = joblib.load(MODEL_XGB_PATH)
        if os.path.exists(SYMPTOM_LIST_PATH):
            self.symptoms = joblib.load(SYMPTOM_LIST_PATH)
        if os.path.exists(DISEASE_LIST_PATH):
            self.diseases = joblib.load(DISEASE_LIST_PATH)
            
    async def get_all_symptoms_from_db(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Symptom))
            symps = result.scalars().all()
            return [{"id": s.id, "name": s.name, "display_name": s.display_name, "category": s.category, "severity_weight": s.severity_weight} for s in symps]

    async def get_all_diseases_from_db(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Disease))
            dis = result.scalars().all()
            return [{"id": d.id, "name": d.name, "display_name": d.display_name, "severity": d.severity, "description": d.description} for d in dis]

    async def get_mappings_from_db(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DiseaseSymptomMapping))
            mappings = result.scalars().all()
            return [{"disease_id": m.disease_id, "symptom_id": m.symptom_id, "weight": m.weight, "is_primary": m.is_primary} for m in mappings]

    async def train_model(self):
        symptoms_data = await self.get_all_symptoms_from_db()
        diseases_data = await self.get_all_diseases_from_db()
        mappings = await self.get_mappings_from_db()
        
        self.symptoms = [s["name"] for s in sorted(symptoms_data, key=lambda x: x["id"])]
        self.diseases = [d["name"] for d in sorted(diseases_data, key=lambda x: x["id"])]
        
        symptom_id_to_idx = {s["id"]: i for i, s in enumerate(sorted(symptoms_data, key=lambda x: x["id"]))}
        disease_id_to_name = {d["id"]: d["name"] for d in diseases_data}
        
        disease_to_symp_idx = {}
        for d in diseases_data:
            disease_to_symp_idx[d["id"]] = []
            
        for m in mappings:
            if m["symptom_id"] in symptom_id_to_idx:
                disease_to_symp_idx[m["disease_id"]].append(symptom_id_to_idx[m["symptom_id"]])
            
        # Generate training data
        X = []
        y = []
        
        random.seed(42)
        
        for d_id, symp_indices in disease_to_symp_idx.items():
            if not symp_indices:
                continue
            
            d_name = disease_id_to_name[d_id]
            
            # Base case: All symptoms present
            base_vec = np.zeros(len(self.symptoms))
            for idx in symp_indices:
                base_vec[idx] = 1
            X.append(base_vec)
            y.append(d_name)
            
            # Augment data with random subsets (simulate different patients)
            for _ in range(50): # 50 synthetic samples per disease
                num_symps = random.randint(max(1, len(symp_indices) // 2), len(symp_indices))
                subset = random.sample(symp_indices, num_symps)
                vec = np.zeros(len(self.symptoms))
                for idx in subset:
                    vec[idx] = 1
                X.append(vec)
                y.append(d_name)
                
        X = np.array(X)
        
        # Convert labels to integer indices for XGBoost
        disease_to_idx = {name: i for i, name in enumerate(self.diseases)}
        y_encoded = np.array([disease_to_idx[label] for label in y])

        # Random Forest
        rf = RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42)
        rf.fit(X, y_encoded)
        self.rf_model = rf
        
        # XGBoost
        xgb_model = xgb.XGBClassifier(n_estimators=200, learning_rate=0.1, max_depth=6, use_label_encoder=False, eval_metric='mlogloss')
        xgb_model.fit(X, y_encoded)
        self.xgb_model = xgb_model
        
        # Save
        joblib.dump(self.rf_model, MODEL_RF_PATH)
        joblib.dump(self.xgb_model, MODEL_XGB_PATH)
        joblib.dump(self.symptoms, SYMPTOM_LIST_PATH)
        joblib.dump(self.diseases, DISEASE_LIST_PATH)
        
        print("Models trained and saved.")

    async def predict(self, symptoms_list: List[str]) -> Dict[str, Any]:
        if not self.rf_model:
            raise ValueError("Model not trained")
            
        from backend.utils.clinical import format_disease_name, get_symptom_weights
        
        # 1. Symptom Weighting
        weights = get_symptom_weights()
        vec = np.zeros(len(self.symptoms))
        for s in symptoms_list:
            if s in self.symptoms:
                weight = weights.get(s, 1.0)
                vec[self.symptoms.index(s)] = weight
                
        # 2. Base Prediction
        probs = self.rf_model.predict_proba([vec])[0]
        
        # 3. Get Disease Info for Severity
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Disease))
            diseases_info = {d.name: d for d in res.scalars().all()}
            
        results = []
        for i, prob in enumerate(probs):
            confidence = float(prob * 100)
            if confidence > 5.0:
                disease_name = self.diseases[i]
                disease_obj = diseases_info.get(disease_name)
                severity = disease_obj.severity if disease_obj else "Moderate"
                
                # Apply Contradiction Penalties
                warning = self.check_symptom_contradictions(symptoms_list, disease_name)
                if warning:
                    confidence *= 0.6  # 40% reduction
                
                results.append({
                    "disease": disease_name,
                    "display_name": format_disease_name(disease_name),
                    "confidence": confidence,
                    "severity": severity,
                    "warning": warning
                })
                
        results.sort(key=lambda x: x["confidence"], reverse=True)
        top_results = results[:5]
        
        # 4. Confidence Gating & Clinical Status
        top_confidence = top_results[0]["confidence"] if top_results else 0
        status = "high_confidence"
        message = "High Confidence Prediction"
        
        if top_confidence < 40:
            status = "inconclusive"
            message = "Symptoms do not strongly match a single condition."
        elif top_confidence < 70:
            status = "low_confidence"
            message = "Possible condition detected. Doctor review recommended."
        elif top_confidence < 85:
            status = "moderate_confidence"
            message = "Likely Condition"
            
        # 5. Risk Label Logic
        for res in top_results:
            conf = res["confidence"]
            sev = res["severity"]
            
            if conf > 85 and sev == "Critical":
                res["risk_label"] = "Critical Risk"
            elif conf > 70 and sev == "Severe":
                res["risk_label"] = "High Risk"
            elif conf > 50:
                res["risk_label"] = "Moderate Risk"
            else:
                res["risk_label"] = "Low Confidence"
                
        # 6. Emergency Warning
        emergency_warning = None
        if top_results and top_results[0]["confidence"] > 85 and top_results[0]["severity"] == "Critical":
            emergency_warning = "⚠ SEEK IMMEDIATE MEDICAL ATTENTION"
            
        # 7. Feature Importance (Why this prediction?)
        importances = self.get_symptom_importance(symptoms_list, top_results[0]["disease"] if top_results else "")
        top_symptoms = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:3]
        why_this = [format_disease_name(s[0]) for s in top_symptoms if s[1] > 0]

        return {
            "predictions": top_results if status != "inconclusive" else [],
            "differential_diagnosis": top_results if status in ["inconclusive", "low_confidence"] else top_results[1:4],
            "status": status,
            "message": message,
            "emergency_warning": emergency_warning,
            "why_this_prediction": why_this,
            "symptoms_analyzed": [s for s in symptoms_list if s in self.symptoms],
            "total_symptoms": int(sum(1 for v in vec if v > 0)),
            "model_used": "random_forest",
            "disclaimer": "HospitalIQ provides AI-assisted clinical support and is NOT a replacement for professional medical diagnosis. Predictions are probabilistic and should always be reviewed by a licensed physician."
        }
        
    def check_symptom_contradictions(self, symptoms_list: List[str], disease_name: str) -> str | None:
        """Identify atypical symptom combinations for a given disease."""
        # IF disease == "heart_failure" AND symptom includes "fever": reduce confidence by 40%
        if disease_name == "heart_failure" and "fever" in symptoms_list:
            return "Symptoms are atypical for this condition (e.g., Fever is uncommon in pure Heart Failure)."
            
        # IF disease == "diabetes" AND symptom includes "wet_cough"
        if "diabetes" in disease_name and "wet_cough" in symptoms_list:
            return "Symptoms are atypical for this condition."
            
        # IF disease == "pneumonia" AND NO respiratory symptoms
        respiratory = ["wet_cough", "dry_cough", "shortness_of_breath", "chest_pain"]
        if disease_name == "pneumonia" and not any(s in symptoms_list for s in respiratory):
            return "Symptoms are atypical for this condition (Missing respiratory symptoms)."
            
        return None

    async def check_symptom_compatibility(self, symptoms_list: List[str], disease_name: str) -> Dict[str, Any]:
        """Verify if input symptoms match the typical profile of the predicted disease."""
        async with AsyncSessionLocal() as session:
            # 1. Get disease ID
            res = await session.execute(select(Disease.id).where(Disease.name == disease_name))
            disease_id = res.scalar()
            if not disease_id:
                return {"is_compatible": True, "matched_primary": 0} # Fallback
            
            # 2. Get primary symptoms for this disease
            res = await session.execute(
                select(Symptom.name)
                .join(DiseaseSymptomMapping, Symptom.id == DiseaseSymptomMapping.symptom_id)
                .where(DiseaseSymptomMapping.disease_id == disease_id, DiseaseSymptomMapping.is_primary == True)
            )
            primary_symptoms = [s[0] for s in res.all()]
            
            # 3. Check match count
            matched_primary = [s for s in symptoms_list if s in primary_symptoms]
            
            return {
                "is_compatible": len(matched_primary) >= 2,
                "matched_primary_count": len(matched_primary),
                "matched_symptoms": matched_primary,
                "total_primary_required": 2
            }

    def get_symptom_importance(self, symptoms_list: List[str], predicted_disease: str) -> Dict[str, float]:
        if not self.rf_model:
            return {}
            
        importances = self.rf_model.feature_importances_
        res = {}
        for s in symptoms_list:
            if s in self.symptoms:
                idx = self.symptoms.index(s)
                res[s] = float(importances[idx])
        return res

if __name__ == "__main__":
    predictor = SymptomDiseasePredictor()
    asyncio.run(predictor.train_model())
