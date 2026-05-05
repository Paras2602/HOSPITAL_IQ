import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.user import User

async def verify_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f"Found {len(users)} users.")
        for u in users:
            print(f"Email: {u.email} | Role: {u.role} | Access Code: {u.access_code}")

if __name__ == "__main__":
    asyncio.run(verify_users())
