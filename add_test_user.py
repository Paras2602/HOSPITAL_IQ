import sqlite3
import uuid

def create_test_user():
    conn = sqlite3.connect('hospitaliq.db')
    cursor = conn.cursor()
    code = "HIQ-" + str(uuid.uuid4().hex[:6]).upper()
    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (id, email, hashed_password, role, access_code, is_active, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (user_id, f"pending_{code}@hospitaliq.local", "hash", "doctor", code, 1)
    )
    conn.commit()
    print(f"Created user with Access Code: {code}")
    conn.close()

if __name__ == "__main__":
    create_test_user()
