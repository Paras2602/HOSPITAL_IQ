import unittest
import asyncio
from sqlalchemy import select, func
from backend.database import get_db, AsyncSessionLocal as SessionLocal
from backend.models.symptom_models import Symptom, Disease, Medicine, DiseaseSymptomMapping

class TestSeedData(unittest.IsolatedAsyncioTestCase):
    async def test_counts(self):
        async with SessionLocal() as db:
            # Check Symptoms
            s_count = (await db.execute(select(func.count(Symptom.id)))).scalar()
            print(f"Symptoms count: {s_count}")
            self.assertGreaterEqual(s_count, 50, "Symptoms count should be at least 50")

            # Check Diseases
            d_count = (await db.execute(select(func.count(Disease.id)))).scalar()
            print(f"Diseases count: {d_count}")
            self.assertGreaterEqual(d_count, 30, "Diseases count should be at least 30")

            # Check Medicines
            m_count = (await db.execute(select(func.count(Medicine.id)))).scalar()
            print(f"Medicines count: {m_count}")
            self.assertGreaterEqual(m_count, 40, "Medicines count should be at least 40")

    async def test_mappings(self):
        async with SessionLocal() as db:
            # Check if diseases have symptoms mapped
            mapping_count = (await db.execute(select(func.count(DiseaseSymptomMapping.id)))).scalar()
            print(f"Mappings count: {mapping_count}")
            self.assertGreater(mapping_count, 0, "There should be some disease-symptom mappings")

if __name__ == "__main__":
    unittest.main()
