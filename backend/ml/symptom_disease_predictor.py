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

    def predict(self, symptoms_list: List[str]) -> Dict[str, Any]:
        if not self.rf_model:
            raise ValueError("Model not trained")
            
        vec = np.zeros(len(self.symptoms))
        for s in symptoms_list:
            if s in self.symptoms:
                vec[self.symptoms.index(s)] = 1
                
        probs = self.rf_model.predict_proba([vec])[0]
        
        results = []
        for i, prob in enumerate(probs):
            if prob > 0.05: # At least 5%
                results.append({
                    "disease": self.diseases[i],
                    "confidence": float(prob * 100),
                })
                
        results.sort(key=lambda x: x["confidence"], reverse=True)
        top_results = results[:5]
        
        for rank, res in enumerate(top_results, 1):
            res["rank"] = rank
            
        return {
            "predictions": top_results,
            "symptoms_analyzed": [s for s in symptoms_list if s in self.symptoms],
            "total_symptoms": int(sum(vec)),
            "model_used": "random_forest",
            "disclaimer": "This is an AI prediction and NOT a medical diagnosis. Please consult a qualified doctor."
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
