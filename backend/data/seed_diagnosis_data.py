import asyncio
import sys
import os

# Add the root project directory to the python path so imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.symptom_models import Symptom, Disease, Medicine, DiseaseSymptomMapping, DiseaseMedicineMapping

SYMPTOMS = [
    # General
    {"name": "fever", "display_name": "Fever", "category": "General", "severity_weight": 2.0},
    {"name": "fatigue", "display_name": "Fatigue", "category": "General", "severity_weight": 1.0},
    {"name": "weight_loss", "display_name": "Weight Loss", "category": "General", "severity_weight": 2.0},
    {"name": "weight_gain", "display_name": "Weight Gain", "category": "General", "severity_weight": 1.0},
    {"name": "chills", "display_name": "Chills", "category": "General", "severity_weight": 2.0},
    {"name": "night_sweats", "display_name": "Night Sweats", "category": "General", "severity_weight": 2.0},
    {"name": "body_ache", "display_name": "Body Ache", "category": "General", "severity_weight": 1.5},
    {"name": "loss_of_appetite", "display_name": "Loss of Appetite", "category": "General", "severity_weight": 1.5},
    {"name": "dehydration", "display_name": "Dehydration", "category": "General", "severity_weight": 2.0},
    {"name": "weakness", "display_name": "Weakness", "category": "General", "severity_weight": 1.5},
    {"name": "excessive_thirst", "display_name": "Excessive Thirst", "category": "General", "severity_weight": 1.0},
    # Respiratory
    {"name": "cough", "display_name": "Cough", "category": "Respiratory", "severity_weight": 1.5},
    {"name": "dry_cough", "display_name": "Dry Cough", "category": "Respiratory", "severity_weight": 1.5},
    {"name": "wet_cough", "display_name": "Wet Cough", "category": "Respiratory", "severity_weight": 2.0},
    {"name": "shortness_of_breath", "display_name": "Shortness of Breath", "category": "Respiratory", "severity_weight": 3.0},
    {"name": "wheezing", "display_name": "Wheezing", "category": "Respiratory", "severity_weight": 2.5},
    {"name": "sore_throat", "display_name": "Sore Throat", "category": "Respiratory", "severity_weight": 1.0},
    {"name": "runny_nose", "display_name": "Runny Nose", "category": "Respiratory", "severity_weight": 1.0},
    {"name": "nasal_congestion", "display_name": "Nasal Congestion", "category": "Respiratory", "severity_weight": 1.0},
    {"name": "sneezing", "display_name": "Sneezing", "category": "Respiratory", "severity_weight": 1.0},
    {"name": "chest_tightness", "display_name": "Chest Tightness", "category": "Respiratory", "severity_weight": 2.5},
    {"name": "rapid_breathing", "display_name": "Rapid Breathing", "category": "Respiratory", "severity_weight": 3.0},
    # Cardiac
    {"name": "chest_pain", "display_name": "Chest Pain", "category": "Cardiac", "severity_weight": 3.0},
    {"name": "palpitations", "display_name": "Palpitations", "category": "Cardiac", "severity_weight": 2.0},
    {"name": "irregular_heartbeat", "display_name": "Irregular Heartbeat", "category": "Cardiac", "severity_weight": 2.5},
    {"name": "swelling_in_legs", "display_name": "Swelling in Legs", "category": "Cardiac", "severity_weight": 2.0},
    {"name": "high_blood_pressure", "display_name": "High Blood Pressure", "category": "Cardiac", "severity_weight": 2.0},
    {"name": "low_blood_pressure", "display_name": "Low Blood Pressure", "category": "Cardiac", "severity_weight": 2.0},
    # Digestive
    {"name": "nausea", "display_name": "Nausea", "category": "Digestive", "severity_weight": 1.5},
    {"name": "vomiting", "display_name": "Vomiting", "category": "Digestive", "severity_weight": 2.0},
    {"name": "diarrhea", "display_name": "Diarrhea", "category": "Digestive", "severity_weight": 2.0},
    {"name": "constipation", "display_name": "Constipation", "category": "Digestive", "severity_weight": 1.5},
    {"name": "abdominal_pain", "display_name": "Abdominal Pain", "category": "Digestive", "severity_weight": 2.0},
    {"name": "bloating", "display_name": "Bloating", "category": "Digestive", "severity_weight": 1.0},
    {"name": "acid_reflux", "display_name": "Acid Reflux", "category": "Digestive", "severity_weight": 1.5},
    {"name": "blood_in_stool", "display_name": "Blood in Stool", "category": "Digestive", "severity_weight": 3.0},
    # Neurological
    {"name": "headache", "display_name": "Headache", "category": "Neurological", "severity_weight": 1.5},
    {"name": "migraine", "display_name": "Migraine", "category": "Neurological", "severity_weight": 2.0},
    {"name": "dizziness", "display_name": "Dizziness", "category": "Neurological", "severity_weight": 1.5},
    {"name": "confusion", "display_name": "Confusion", "category": "Neurological", "severity_weight": 3.0},
    {"name": "numbness", "display_name": "Numbness", "category": "Neurological", "severity_weight": 2.0},
    {"name": "tingling", "display_name": "Tingling", "category": "Neurological", "severity_weight": 1.5},
    {"name": "blurred_vision", "display_name": "Blurred Vision", "category": "Neurological", "severity_weight": 2.0},
    {"name": "seizures", "display_name": "Seizures", "category": "Neurological", "severity_weight": 3.0},
    {"name": "memory_loss", "display_name": "Memory Loss", "category": "Neurological", "severity_weight": 2.5},
    # Musculoskeletal
    {"name": "joint_pain", "display_name": "Joint Pain", "category": "Musculoskeletal", "severity_weight": 1.5},
    {"name": "muscle_pain", "display_name": "Muscle Pain", "category": "Musculoskeletal", "severity_weight": 1.5},
    {"name": "back_pain", "display_name": "Back Pain", "category": "Musculoskeletal", "severity_weight": 2.0},
    {"name": "stiffness", "display_name": "Stiffness", "category": "Musculoskeletal", "severity_weight": 1.5},
    {"name": "swelling_in_joints", "display_name": "Swelling in Joints", "category": "Musculoskeletal", "severity_weight": 2.0},
    {"name": "limited_movement", "display_name": "Limited Movement", "category": "Musculoskeletal", "severity_weight": 2.5},
    # Skin
    {"name": "rash", "display_name": "Rash", "category": "Skin", "severity_weight": 1.5},
    {"name": "itching", "display_name": "Itching", "category": "Skin", "severity_weight": 1.0},
    {"name": "skin_discoloration", "display_name": "Skin Discoloration", "category": "Skin", "severity_weight": 1.5},
    {"name": "swelling", "display_name": "Swelling", "category": "Skin", "severity_weight": 1.5},
    {"name": "dry_skin", "display_name": "Dry Skin", "category": "Skin", "severity_weight": 1.0},
    {"name": "excessive_sweating", "display_name": "Excessive Sweating", "category": "Skin", "severity_weight": 1.5},
    # Urinary
    {"name": "frequent_urination", "display_name": "Frequent Urination", "category": "Urinary", "severity_weight": 1.5},
    {"name": "painful_urination", "display_name": "Painful Urination", "category": "Urinary", "severity_weight": 2.0},
    {"name": "blood_in_urine", "display_name": "Blood in Urine", "category": "Urinary", "severity_weight": 3.0},
    {"name": "dark_urine", "display_name": "Dark Urine", "category": "Urinary", "severity_weight": 2.0},
    {"name": "foamy_urine", "display_name": "Foamy Urine", "category": "Urinary", "severity_weight": 2.0},
    # Endocrine
    {"name": "excessive_hunger", "display_name": "Excessive Hunger", "category": "Endocrine", "severity_weight": 1.5},
    {"name": "unexplained_weight_loss", "display_name": "Unexplained Weight Loss", "category": "Endocrine", "severity_weight": 2.5},
]

DISEASES = [
    {"name": "common_cold", "display_name": "Common Cold", "category": "Infectious", "severity": "Mild"},
    {"name": "influenza", "display_name": "Influenza (Flu)", "category": "Infectious", "severity": "Moderate"},
    {"name": "covid_19", "display_name": "COVID-19", "category": "Infectious", "severity": "Severe"},
    {"name": "pneumonia", "display_name": "Pneumonia", "category": "Respiratory", "severity": "Severe"},
    {"name": "bronchitis", "display_name": "Bronchitis", "category": "Respiratory", "severity": "Moderate"},
    {"name": "asthma", "display_name": "Asthma", "category": "Respiratory", "severity": "Moderate"},
    {"name": "tuberculosis", "display_name": "Tuberculosis", "category": "Infectious", "severity": "Severe"},
    {"name": "diabetes_type_1", "display_name": "Diabetes Type 1", "category": "Endocrine", "severity": "Severe"},
    {"name": "diabetes_type_2", "display_name": "Diabetes Type 2", "category": "Endocrine", "severity": "Moderate"},
    {"name": "hypertension", "display_name": "Hypertension", "category": "Cardiac", "severity": "Moderate"},
    {"name": "heart_disease", "display_name": "Heart Disease", "category": "Cardiac", "severity": "Severe"},
    {"name": "coronary_artery_disease", "display_name": "Coronary Artery Disease", "category": "Cardiac", "severity": "Severe"},
    {"name": "heart_failure", "display_name": "Heart Failure", "category": "Cardiac", "severity": "Critical"},
    {"name": "chronic_kidney_disease", "display_name": "Chronic Kidney Disease", "category": "Renal", "severity": "Severe"},
    {"name": "kidney_stones", "display_name": "Kidney Stones", "category": "Renal", "severity": "Moderate"},
    {"name": "uti", "display_name": "Urinary Tract Infection", "category": "Renal", "severity": "Moderate"},
    {"name": "liver_disease", "display_name": "Liver Disease", "category": "Digestive", "severity": "Severe"},
    {"name": "hepatitis", "display_name": "Hepatitis", "category": "Infectious", "severity": "Moderate"},
    {"name": "cirrhosis", "display_name": "Cirrhosis", "category": "Digestive", "severity": "Severe"},
    {"name": "gastritis", "display_name": "Gastritis", "category": "Digestive", "severity": "Mild"},
    {"name": "gerd", "display_name": "GERD", "category": "Digestive", "severity": "Moderate"},
    {"name": "peptic_ulcer", "display_name": "Peptic Ulcer", "category": "Digestive", "severity": "Moderate"},
    {"name": "ibs", "display_name": "Irritable Bowel Syndrome", "category": "Digestive", "severity": "Mild"},
    {"name": "migraine", "display_name": "Migraine", "category": "Neurological", "severity": "Moderate"},
    {"name": "stroke", "display_name": "Stroke", "category": "Neurological", "severity": "Critical"},
    {"name": "epilepsy", "display_name": "Epilepsy", "category": "Neurological", "severity": "Severe"},
    {"name": "alzheimer", "display_name": "Alzheimer's Disease", "category": "Neurological", "severity": "Severe"},
    {"name": "anemia", "display_name": "Anemia", "category": "Blood", "severity": "Moderate"},
    {"name": "dengue", "display_name": "Dengue", "category": "Infectious", "severity": "Moderate"},
    {"name": "malaria", "display_name": "Malaria", "category": "Infectious", "severity": "Moderate"},
    {"name": "typhoid", "display_name": "Typhoid", "category": "Infectious", "severity": "Moderate"},
    {"name": "arthritis", "display_name": "Arthritis", "category": "Musculoskeletal", "severity": "Moderate"},
    {"name": "osteoporosis", "display_name": "Osteoporosis", "category": "Musculoskeletal", "severity": "Moderate"},
    {"name": "psoriasis", "display_name": "Psoriasis", "category": "Skin", "severity": "Mild"},
    {"name": "eczema", "display_name": "Eczema", "category": "Skin", "severity": "Mild"},
]

MEDICINES = [
    {"name": "Paracetamol", "medicine_type": "Tablet", "default_dosage": "500mg", "frequency": "When required"},
    {"name": "Ibuprofen", "medicine_type": "Tablet", "default_dosage": "400mg", "frequency": "When required"},
    {"name": "Amoxicillin", "medicine_type": "Capsule", "default_dosage": "500mg", "frequency": "Three times a day"},
    {"name": "Azithromycin", "medicine_type": "Tablet", "default_dosage": "500mg", "frequency": "Once daily"},
    {"name": "Metformin", "medicine_type": "Tablet", "default_dosage": "500mg", "frequency": "Twice daily"},
    {"name": "Glimepiride", "medicine_type": "Tablet", "default_dosage": "2mg", "frequency": "Once daily"},
    {"name": "Amlodipine", "medicine_type": "Tablet", "default_dosage": "5mg", "frequency": "Once daily"},
    {"name": "Losartan", "medicine_type": "Tablet", "default_dosage": "50mg", "frequency": "Once daily"},
    {"name": "Atorvastatin", "medicine_type": "Tablet", "default_dosage": "10mg", "frequency": "Once daily at night"},
    {"name": "Omeprazole", "medicine_type": "Capsule", "default_dosage": "20mg", "frequency": "Once daily before breakfast"},
    {"name": "Pantoprazole", "medicine_type": "Tablet", "default_dosage": "40mg", "frequency": "Once daily before breakfast"},
    {"name": "Cetirizine", "medicine_type": "Tablet", "default_dosage": "10mg", "frequency": "Once daily"},
    {"name": "Montelukast", "medicine_type": "Tablet", "default_dosage": "10mg", "frequency": "Once daily at night"},
    {"name": "Salbutamol", "medicine_type": "Inhaler", "default_dosage": "100mcg", "frequency": "2 puffs as needed"},
    {"name": "Domperidone", "medicine_type": "Tablet", "default_dosage": "10mg", "frequency": "When required"},
    {"name": "Ondansetron", "medicine_type": "Tablet", "default_dosage": "4mg", "frequency": "When required"},
    {"name": "Loperamide", "medicine_type": "Capsule", "default_dosage": "2mg", "frequency": "After loose stool"},
    {"name": "Diclofenac", "medicine_type": "Tablet", "default_dosage": "50mg", "frequency": "Twice daily"},
    {"name": "Tramadol", "medicine_type": "Tablet", "default_dosage": "50mg", "frequency": "When severe pain"},
    {"name": "Metoprolol", "medicine_type": "Tablet", "default_dosage": "50mg", "frequency": "Twice daily"},
    {"name": "Furosemide", "medicine_type": "Tablet", "default_dosage": "40mg", "frequency": "Once daily morning"},
    {"name": "Clopidogrel", "medicine_type": "Tablet", "default_dosage": "75mg", "frequency": "Once daily"},
    {"name": "Aspirin", "medicine_type": "Tablet", "default_dosage": "75mg", "frequency": "Once daily"},
    {"name": "Ranitidine", "medicine_type": "Tablet", "default_dosage": "150mg", "frequency": "Twice daily"},
    {"name": "Doxycycline", "medicine_type": "Capsule", "default_dosage": "100mg", "frequency": "Twice daily"},
    {"name": "Ciprofloxacin", "medicine_type": "Tablet", "default_dosage": "500mg", "frequency": "Twice daily"},
    {"name": "Hydroxychloroquine", "medicine_type": "Tablet", "default_dosage": "200mg", "frequency": "Once daily"},
    {"name": "Artemether", "medicine_type": "Tablet", "default_dosage": "80mg", "frequency": "Twice daily"},
    {"name": "Iron supplement", "medicine_type": "Tablet", "default_dosage": "325mg", "frequency": "Once daily"},
    {"name": "Folic acid", "medicine_type": "Tablet", "default_dosage": "5mg", "frequency": "Once daily"},
    {"name": "Vitamin D3", "medicine_type": "Capsule", "default_dosage": "60000IU", "frequency": "Once a week"},
    {"name": "Calcium", "medicine_type": "Tablet", "default_dosage": "500mg", "frequency": "Once daily"},
    {"name": "Levothyroxine", "medicine_type": "Tablet", "default_dosage": "50mcg", "frequency": "Once daily morning"},
    {"name": "Insulin", "medicine_type": "Injection", "default_dosage": "As prescribed", "frequency": "Before meals"},
    {"name": "ORS Sachets", "medicine_type": "Powder", "default_dosage": "1 sachet", "frequency": "In 1L water"},
    {"name": "Cough syrup", "medicine_type": "Syrup", "default_dosage": "5ml", "frequency": "Three times a day"},
    {"name": "Nasal spray", "medicine_type": "Spray", "default_dosage": "2 puffs", "frequency": "Twice daily"},
    {"name": "Antacid suspension", "medicine_type": "Syrup", "default_dosage": "10ml", "frequency": "After meals"},
    {"name": "Calamine lotion", "medicine_type": "Lotion", "default_dosage": "Apply locally", "frequency": "Twice daily"},
    {"name": "Betamethasone", "medicine_type": "Ointment", "default_dosage": "Apply locally", "frequency": "Twice daily"},
]

DISEASE_SYMPTOMS_MAP = {
    "common_cold": ["runny_nose", "sneezing", "sore_throat", "cough", "fatigue", "fever", "nasal_congestion"],
    "influenza": ["fever", "chills", "muscle_pain", "fatigue", "cough", "headache", "sore_throat", "runny_nose"],
    "covid_19": ["fever", "dry_cough", "fatigue", "loss_of_appetite", "body_ache", "shortness_of_breath", "sore_throat", "headache", "chest_pain"],
    "pneumonia": ["fever", "chills", "wet_cough", "shortness_of_breath", "chest_pain", "fatigue", "nausea"],
    "bronchitis": ["wet_cough", "fatigue", "shortness_of_breath", "chest_tightness", "fever", "chills"],
    "asthma": ["shortness_of_breath", "wheezing", "chest_tightness", "cough"],
    "tuberculosis": ["cough", "chest_pain", "fatigue", "fever", "night_sweats", "weight_loss", "loss_of_appetite"],
    "diabetes_type_1": ["excessive_thirst", "frequent_urination", "excessive_hunger", "weight_loss", "fatigue", "blurred_vision"],
    "diabetes_type_2": ["excessive_thirst", "frequent_urination", "fatigue", "blurred_vision", "weight_gain"],
    "hypertension": ["headache", "shortness_of_breath", "dizziness", "chest_pain", "palpitations"],
    "heart_disease": ["chest_pain", "shortness_of_breath", "palpitations", "weakness", "dizziness"],
    "coronary_artery_disease": ["chest_pain", "shortness_of_breath", "fatigue", "dizziness"],
    "heart_failure": ["shortness_of_breath", "fatigue", "swelling_in_legs", "rapid_breathing", "irregular_heartbeat", "weight_gain"],
    "chronic_kidney_disease": ["fatigue", "swelling_in_legs", "nausea", "loss_of_appetite", "frequent_urination", "muscle_pain", "dry_skin"],
    "kidney_stones": ["back_pain", "painful_urination", "blood_in_urine", "nausea", "vomiting", "frequent_urination"],
    "uti": ["painful_urination", "frequent_urination", "blood_in_urine", "dark_urine", "pelvic_pain", "fever"],
    "liver_disease": ["fatigue", "nausea", "loss_of_appetite", "swelling_in_legs", "skin_discoloration", "dark_urine", "itching"],
    "hepatitis": ["fatigue", "nausea", "vomiting", "loss_of_appetite", "fever", "dark_urine", "joint_pain", "skin_discoloration"],
    "cirrhosis": ["fatigue", "weakness", "loss_of_appetite", "nausea", "weight_loss", "itching", "swelling_in_legs"],
    "gastritis": ["abdominal_pain", "nausea", "vomiting", "loss_of_appetite", "bloating"],
    "gerd": ["acid_reflux", "chest_pain", "nausea", "sore_throat"],
    "peptic_ulcer": ["abdominal_pain", "bloating", "acid_reflux", "nausea", "vomiting"],
    "ibs": ["abdominal_pain", "bloating", "diarrhea", "constipation"],
    "migraine": ["headache", "nausea", "vomiting", "blurred_vision", "dizziness"],
    "stroke": ["numbness", "weakness", "confusion", "dizziness", "blurred_vision", "headache", "loss_of_balance"],
    "epilepsy": ["seizures", "confusion", "staring_spell", "loss_of_consciousness"],
    "alzheimer": ["memory_loss", "confusion", "difficulty_thinking_and_understanding", "disorientation", "inability_to_create_new_memories"],
    "anemia": ["fatigue", "weakness", "dizziness", "shortness_of_breath", "chest_pain", "cold_hands_and_feet", "headache"],
    "dengue": ["fever", "headache", "muscle_pain", "joint_pain", "nausea", "vomiting", "rash", "pain_behind_eyes"],
    "malaria": ["fever", "chills", "headache", "nausea", "vomiting", "muscle_pain", "fatigue", "sweating"],
    "typhoid": ["fever", "headache", "weakness", "fatigue", "muscle_pain", "sweating", "dry_cough", "loss_of_appetite", "weight_loss", "abdominal_pain", "diarrhea", "rash"],
    "arthritis": ["joint_pain", "stiffness", "swelling_in_joints", "limited_movement"],
    "osteoporosis": ["back_pain", "loss_of_height", "bone_fracture", "stooped_posture"],
    "psoriasis": ["rash", "dry_skin", "itching", "skin_discoloration", "joint_pain"],
    "eczema": ["itching", "dry_skin", "rash", "skin_discoloration"],
}

DISEASE_MEDICINES_MAP = {
    "common_cold": ["Paracetamol", "Cetirizine", "Cough syrup"],
    "influenza": ["Paracetamol", "Ibuprofen", "Oseltamivir"],
    "covid_19": ["Paracetamol", "Azithromycin", "Vitamin D3", "Cough syrup"],
    "pneumonia": ["Amoxicillin", "Azithromycin", "Paracetamol", "Cough syrup"],
    "bronchitis": ["Amoxicillin", "Salbutamol", "Cough syrup"],
    "asthma": ["Salbutamol", "Montelukast"],
    "tuberculosis": ["Isoniazid", "Rifampin", "Ethambutol"],
    "diabetes_type_1": ["Insulin"],
    "diabetes_type_2": ["Metformin", "Glimepiride"],
    "hypertension": ["Amlodipine", "Losartan"],
    "heart_disease": ["Aspirin", "Atorvastatin", "Metoprolol"],
    "coronary_artery_disease": ["Aspirin", "Atorvastatin", "Clopidogrel"],
    "heart_failure": ["Furosemide", "Metoprolol", "Lisinopril"],
    "chronic_kidney_disease": ["Furosemide", "Calcium", "Vitamin D3"],
    "kidney_stones": ["Diclofenac", "Tamsulosin", "Paracetamol"],
    "uti": ["Ciprofloxacin", "Paracetamol"],
    "liver_disease": ["Ursodiol", "Spironolactone"],
    "hepatitis": ["Tenofovir", "Entecavir"],
    "cirrhosis": ["Spironolactone", "Furosemide"],
    "gastritis": ["Pantoprazole", "Antacid suspension"],
    "gerd": ["Omeprazole", "Antacid suspension"],
    "peptic_ulcer": ["Pantoprazole", "Amoxicillin", "Clarithromycin"],
    "ibs": ["Loperamide", "Mebeverine", "Dietary fiber"],
    "migraine": ["Ibuprofen", "Sumatriptan", "Paracetamol"],
    "stroke": ["Aspirin", "Clopidogrel", "Atorvastatin"],
    "epilepsy": ["Levetiracetam", "Valproic acid"],
    "alzheimer": ["Donepezil", "Memantine"],
    "anemia": ["Iron supplement", "Folic acid", "Vitamin C"],
    "dengue": ["Paracetamol", "ORS Sachets"],
    "malaria": ["Artemether", "Hydroxychloroquine", "Paracetamol"],
    "typhoid": ["Ciprofloxacin", "Azithromycin", "Paracetamol"],
    "arthritis": ["Ibuprofen", "Diclofenac", "Methotrexate"],
    "osteoporosis": ["Calcium", "Vitamin D3", "Alendronate"],
    "psoriasis": ["Betamethasone", "Methotrexate", "Salicylic acid"],
    "eczema": ["Calamine lotion", "Betamethasone", "Moisturizer"],
}

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("Seeding symptoms...")
        symptom_ids = {}
        for symp in SYMPTOMS:
            result = await session.execute(select(Symptom).filter_by(name=symp["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                new_symp = Symptom(**symp)
                session.add(new_symp)
                await session.flush()
                symptom_ids[symp["name"]] = new_symp.id
            else:
                symptom_ids[symp["name"]] = existing.id
        await session.commit()
        print(f"Added {len(SYMPTOMS)} symptoms.")

        print("Seeding diseases...")
        disease_ids = {}
        for dis in DISEASES:
            result = await session.execute(select(Disease).filter_by(name=dis["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                new_dis = Disease(**dis)
                session.add(new_dis)
                await session.flush()
                disease_ids[dis["name"]] = new_dis.id
            else:
                disease_ids[dis["name"]] = existing.id
        await session.commit()
        print(f"Added {len(DISEASES)} diseases.")

        print("Seeding medicines...")
        medicine_ids = {}
        for med in MEDICINES:
            result = await session.execute(select(Medicine).filter_by(name=med["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                new_med = Medicine(**med)
                session.add(new_med)
                await session.flush()
                medicine_ids[med["name"]] = new_med.id
            else:
                medicine_ids[med["name"]] = existing.id
        await session.commit()
        print(f"Added {len(MEDICINES)} medicines.")

        print("Seeding disease-symptom mappings...")
        for disease_name, symptom_names in DISEASE_SYMPTOMS_MAP.items():
            if disease_name not in disease_ids:
                continue
            dis_id = disease_ids[disease_name]
            for symp_name in symptom_names:
                if symp_name not in symptom_ids:
                    continue
                symp_id = symptom_ids[symp_name]
                result = await session.execute(select(DiseaseSymptomMapping).filter_by(disease_id=dis_id, symptom_id=symp_id))
                existing = result.scalar_one_or_none()
                if not existing:
                    session.add(DiseaseSymptomMapping(disease_id=dis_id, symptom_id=symp_id, is_primary=(symptom_names.index(symp_name) < 3)))
        await session.commit()
        print("Added disease-symptom mappings.")

        print("Seeding disease-medicine mappings...")
        for disease_name, med_names in DISEASE_MEDICINES_MAP.items():
            if disease_name not in disease_ids:
                continue
            dis_id = disease_ids[disease_name]
            for med_name in med_names:
                # Add medicine if it doesn't exist in MEDICINES but is in MAP
                if med_name not in medicine_ids:
                    new_med = Medicine(name=med_name, medicine_type="Tablet")
                    session.add(new_med)
                    await session.flush()
                    medicine_ids[med_name] = new_med.id
                
                med_id = medicine_ids[med_name]
                result = await session.execute(select(DiseaseMedicineMapping).filter_by(disease_id=dis_id, medicine_id=med_id))
                existing = result.scalar_one_or_none()
                if not existing:
                    session.add(DiseaseMedicineMapping(disease_id=dis_id, medicine_id=med_id, priority_order=med_names.index(med_name)+1))
        await session.commit()
        print("Added disease-medicine mappings.")

if __name__ == "__main__":
    asyncio.run(seed_data())
