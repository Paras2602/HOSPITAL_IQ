import asyncio
from sqlalchemy import text
from backend.database import AsyncSessionLocal, engine

async def migrate():
    async with engine.begin() as conn:
        try:
            # Check if column exists
            result = await conn.execute(text("PRAGMA table_info(diagnosis_sessions)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "follow_up_appointment_id" not in columns:
                print("Adding column 'follow_up_appointment_id' to 'diagnosis_sessions'...")
                await conn.execute(text("ALTER TABLE diagnosis_sessions ADD COLUMN follow_up_appointment_id VARCHAR"))
                print("Migration successful.")
            else:
                print("Column 'follow_up_appointment_id' already exists.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
