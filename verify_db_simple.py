import sqlite3

def verify():
    conn = sqlite3.connect('hospitaliq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email, role, access_code FROM users")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} users.")
    for row in rows:
        print(f"Email: {row[0]} | Role: {row[1]} | Access Code: {row[2]}")
    conn.close()

if __name__ == "__main__":
    verify()
