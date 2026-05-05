import asyncio
import os
import sys

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from backend.database import AsyncSessionLocal
from backend.models.symptom_models import Symptom

async def verify():
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(Symptom))
            symptoms = result.scalars().all()
            print(f"Symptoms found: {len(symptoms)}")
            if symptoms:
                print(f"First symptom: {symptoms[0].display_name} ({symptoms[0].category})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
