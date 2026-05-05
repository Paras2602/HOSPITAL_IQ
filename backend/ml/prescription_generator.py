from typing import Dict, Any, List
from datetime import datetime

class PrescriptionGenerator:
    def __init__(self):
        pass

    def generate_prescription(self, 
                              prescription_id: str,
                              patient_data: Dict[str, Any], 
                              diagnosis_data: Dict[str, Any],
                              medicines: List[Dict[str, Any]],
                              doctor_data: Dict[str, Any]) -> str:
        
        date_str = datetime.now().strftime("%d %B %Y")
        
        # Patient Info
        p_name = patient_data.get("name", "Unknown")
        p_age = patient_data.get("age", "N/A")
        p_sex = patient_data.get("sex", "N/A")
        p_weight = patient_data.get("weight", "N/A")
        p_blood_group = patient_data.get("blood_group", "N/A")
        p_id = patient_data.get("id", "N/A")
        
        # Diagnosis
        d_disease = diagnosis_data.get("disease", "Unknown")
        d_confidence = diagnosis_data.get("confidence", 0.0)
        d_severity = diagnosis_data.get("severity", "Unknown")
        symptoms = diagnosis_data.get("symptoms", [])
        
        # Medicines Table
        med_rows = ""
        for i, med in enumerate(medicines, 1):
            name = str(med.get("name", "")).ljust(14)[:14]
            dosage = str(med.get("dosage", "")).ljust(8)[:8]
            freq = str(med.get("frequency", "")).ljust(10)[:10]
            dur = str(med.get("duration", "")).ljust(10)[:10]
            med_rows += f"   │ {str(i).ljust(2)} │ {name} │ {dosage} │ {freq} │ {dur} │\n"

        instructions = ""
        for i, med in enumerate(medicines, 1):
            if med.get("instructions"):
                instructions += f"   {i}. Take {med['name']} - {med['instructions']}\n"
            else:
                instructions += f"   {i}. Take {med['name']} as directed\n"

        precautions_text = diagnosis_data.get("precautions", "- Take adequate rest\n- Stay hydrated")
        if isinstance(precautions_text, list):
            precautions_text = "\n".join([f"- {p}" for p in precautions_text])
            
        dietary_advice = diagnosis_data.get("dietary_advice", "- Maintain a balanced diet")
        if isinstance(dietary_advice, list):
            dietary_advice = "\n".join([f"- {d}" for d in dietary_advice])
            
        follow_up = diagnosis_data.get("follow_up_days", "15")

        dr_name = doctor_data.get("name", "Dr. Unknown")
        dr_qual = doctor_data.get("qualification", "MBBS")
        
        symptoms_str = "\n   - ".join(symptoms) if symptoms else "None reported"
        if symptoms_str and not symptoms_str.startswith("\n"):
            symptoms_str = "   - " + symptoms_str

        template = f"""╔══════════════════════════════════════════════╗
║          HOSPITALIQ PRESCRIPTION             ║
╠══════════════════════════════════════════════╣

Prescription ID: {prescription_id}
Date: {date_str}

PATIENT INFORMATION:
Name: {p_name}
Age: {p_age} years | Sex: {p_sex} | Weight: {p_weight} kg
Blood Group: {p_blood_group} | Patient ID: {p_id}

DIAGNOSIS:
Primary Diagnosis: {d_disease}
Confidence: {d_confidence:.0f}% (AI-Assisted)
Severity: {d_severity}

Presenting Symptoms:{symptoms_str}

PRESCRIBED MEDICATIONS:
   ┌────┬──────────────┬────────┬──────────┬──────────┐
   │ #  │ Medicine     │ Dosage │ Frequency│ Duration │
   ├────┼──────────────┼────────┼──────────┼──────────┤
{med_rows.rstrip()}
   └────┴──────────────┴────────┴──────────┴──────────┘

INSTRUCTIONS:
{instructions.rstrip()}

PRECAUTIONS:
{precautions_text}

DIETARY ADVICE:
{dietary_advice}

FOLLOW-UP: After {follow_up} days

DISCLAIMER: This prescription includes AI-assisted 
diagnosis. Final clinical judgment has been made by 
the treating physician.

Prescribed by: {dr_name}
Qualification: {dr_qual}
Hospital: HospitalIQ

Digital Signature: [Verified]
╚══════════════════════════════════════════════╝"""
        return template

    def format_medicine_instructions(self, medicines: List[Dict[str, Any]]) -> str:
        """Create clear medicine instructions with timing, food relation, and warnings."""
        if not medicines:
            return "No medicines prescribed."
        
        lines = []
        for i, med in enumerate(medicines, 1):
            name = med.get("name", "Unknown")
            dosage = med.get("dosage", "")
            frequency = med.get("frequency", "As directed")
            duration = med.get("duration", "")
            instructions = med.get("instructions", "")
            side_effects = med.get("common_side_effects", "")
            
            line = f"{i}. {name} ({dosage})"
            line += f"\n   Schedule: {frequency}"
            if duration:
                line += f" for {duration}"
            if instructions:
                line += f"\n   Instructions: {instructions}"
            else:
                line += "\n   Instructions: Take as directed by your physician"
            if side_effects:
                line += f"\n   ⚠ Possible side effects: {side_effects}"
            lines.append(line)
        
        return "\n\n".join(lines)

    def generate_precautions(self, disease: str, patient_data: Dict[str, Any]) -> List[str]:
        """Generate context-aware precautions based on disease AND patient profile."""
        precautions = []
        
        # Universal precautions
        precautions.append("Take adequate rest and avoid strenuous physical activity")
        precautions.append("Stay well hydrated — drink at least 8 glasses of water daily")
        precautions.append("Take all medications exactly as prescribed")
        
        # Disease-specific precautions
        disease_lower = disease.lower()
        if "diabetes" in disease_lower:
            precautions.extend([
                "Monitor blood sugar levels at least twice daily",
                "Avoid sugary foods and refined carbohydrates",
                "Do not skip meals — eat at regular intervals",
                "Report any signs of hypoglycemia (dizziness, sweating, confusion) immediately",
                "Inspect feet daily for cuts, blisters, or swelling",
            ])
        elif "heart" in disease_lower or "cardiac" in disease_lower or "hypertension" in disease_lower:
            precautions.extend([
                "Monitor blood pressure daily and maintain a log",
                "Reduce salt intake to less than 5g per day",
                "Avoid heavy lifting and sudden exertion",
                "Seek emergency care if you experience chest pain, shortness of breath, or arm numbness",
                "Quit smoking and limit alcohol consumption",
            ])
        elif "liver" in disease_lower or "hepat" in disease_lower:
            precautions.extend([
                "Completely avoid alcohol and recreational drugs",
                "Reduce fatty and fried food intake",
                "Avoid self-medication, especially paracetamol/acetaminophen",
                "Report any yellowing of eyes or skin immediately",
            ])
        elif "kidney" in disease_lower or "renal" in disease_lower or "ckd" in disease_lower:
            precautions.extend([
                "Limit protein, sodium, and potassium intake as advised",
                "Monitor urine output and report any significant changes",
                "Avoid NSAIDs (ibuprofen, aspirin) without doctor approval",
                "Keep blood pressure under control",
            ])
        elif "flu" in disease_lower or "influenza" in disease_lower or "cold" in disease_lower:
            precautions.extend([
                "Isolate for at least 5 days to prevent transmission",
                "Wear a mask when around others",
                "Cover mouth and nose when coughing or sneezing",
                "Seek emergency care if difficulty breathing develops",
            ])
        elif "pneumonia" in disease_lower:
            precautions.extend([
                "Complete the full course of antibiotics even if feeling better",
                "Use a humidifier to ease breathing",
                "Seek emergency care if breathing becomes difficult",
                "Avoid smoking and exposure to pollutants",
            ])
        else:
            precautions.extend([
                "Follow up with your doctor if symptoms persist beyond 48 hours",
                "Maintain a symptom diary to track changes",
            ])
        
        # Age-specific precautions
        age = patient_data.get("age")
        if age:
            if age >= 65:
                precautions.append("Take extra caution with mobility to prevent falls")
                precautions.append("Ensure someone is available to assist with daily activities if needed")
            elif age <= 12:
                precautions.append("Guardian must supervise medication administration")
                precautions.append("Ensure adequate nutrition and fluid intake for recovery")
        
        # Allergy-aware precautions
        allergies = patient_data.get("allergies", "")
        if allergies and allergies.lower() != "none":
            precautions.append(f"Known Allergies ({allergies}) — ensure all medications are cross-checked")
        
        # Existing conditions
        conditions = patient_data.get("existing_conditions") or patient_data.get("chronic_conditions", "")
        if conditions and conditions.lower() != "none":
            precautions.append(f"Existing conditions ({conditions}) — inform treating physician of all medications")
        
        return precautions

    def generate_patient_summary(self, symptoms: List[str], prediction: Dict[str, Any]) -> str:
        disease = prediction.get("disease", "an unknown condition")
        confidence = prediction.get("confidence", 0.0)
        severity = prediction.get("severity", "moderate")
        
        symptoms_str = ", ".join(symptoms) if symptoms else "your symptoms"
        
        advice = "Please rest, stay hydrated, and consult a doctor."
        if severity and severity.lower() in ["severe", "critical"]:
            advice = "This may be a serious condition. Please seek medical attention immediately."
            
        summary = (
            f"Based on your symptoms ({symptoms_str}), our AI suggests you may have "
            f"{disease} with {confidence:.0f}% confidence. This is typically considered a "
            f"{severity.lower()} condition. {advice}"
        )
        return summary
