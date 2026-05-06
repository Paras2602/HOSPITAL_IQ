from typing import Dict

def format_disease_name(name: str) -> str:
    if not name:
        return name
    
    # Common clinical mappings
    mapping = {
        "heart_failure": "Heart Failure",
        "diabetes_type_2": "Type 2 Diabetes",
        "chronic_kidney_disease": "Chronic Kidney Disease",
        "pneumonia": "Pneumonia",
        "malaria": "Malaria",
        "dengue": "Dengue",
        "typhoid": "Typhoid",
        "covid_19": "COVID-19",
        "bronchitis": "Bronchitis",
        "asthma": "Asthma",
        "hypertension": "Hypertension",
        "tuberculosis": "Tuberculosis",
        "migraine": "Migraine",
        "anemia": "Anemia",
    }
    
    name_lower = name.lower()
    if name_lower in mapping:
        return mapping[name_lower]
    
    # Fallback: snake_case to Title Case
    return name.replace("_", " ").title()

def get_symptom_weights() -> Dict[str, float]:
    return {
        "shortness_of_breath": 3.0,
        "chest_pain": 3.0,
        "swelling_in_legs": 2.5,
        "wet_cough": 1.5,
        "fever": 1.0,
        "weight_gain": 2.0,
        "fatigue": 1.2,
        "dizziness": 1.5,
        "nausea": 1.0,
        "blurred_vision": 2.0,
        "frequent_urination": 2.5,
        "excessive_thirst": 2.5,
    }
