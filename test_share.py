import asyncio
import json
from sqlalchemy import select
from backend.database import AsyncSessionLocal
from backend.models.user import User
from backend.models.symptom_models import DiagnosisSession

async def main():
    async with AsyncSessionLocal() as db:
        # Find a user and a diagnosis session
        user_res = await db.execute(select(User).where(User.role == "patient").limit(1))
        user = user_res.scalar_one_or_none()
        if not user:
            print("No patient found")
            return
            
        session_res = await db.execute(select(DiagnosisSession).order_by(DiagnosisSession.created_at.desc()).limit(1))
        session = session_res.scalar_one_or_none()
        if not session:
            print("No session found")
            return
            
        doc_res = await db.execute(select(User).where(User.role == "doctor").limit(1))
        doc = doc_res.scalar_one_or_none()
        if not doc:
            print("No doctor found")
            return

        print(f"Patient: {user.email}, Session: {session.session_id}, Doctor: {doc.id}")

        # Try to simulate the share-with-doctor logic
        sess_lookup = await db.execute(select(DiagnosisSession).where(DiagnosisSession.session_id == session.session_id))
        sess = sess_lookup.scalar_one_or_none()
        if not sess:
            print("Session not found by session_id")
        else:
            print("Session found by session_id successfully!")
            print(f"Status before: {sess.status}")

if __name__ == "__main__":
    asyncio.run(main())
